/**
 * @file protocol.c
 * @brief Serial Communication Protocol Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * ROSMaster compatible serial protocol for ROS 2 integration
 */

#include "protocol.h"
#include "hal_usart.h"
#include "task_control.h"
#include "imu_driver.h"
#include "task_imu.h"
#include "encoder_driver.h"
#include "battery_monitor.h"
#include "flash_storage.h"
#include "orbibot_config.h"
#include "firmware_version.h"
#include "FreeRTOS.h"
#include "task.h"
#include <string.h>

/* ========================================================================
 * GLOBAL VARIABLES
 * ======================================================================== */

// Reception buffers and state (double-buffered to prevent ISR/task race)
uint8_t g_rx_buffer[PTO_MAX_BUF_LEN] = {0};
uint8_t g_rx_buffer2[PTO_MAX_BUF_LEN] = {0};  // Secondary buffer
uint8_t g_rx_index = 0;
rx_state_t g_rx_state = RX_STATE_WAIT_HEADER;
uint8_t g_rx_active_buffer = 0;  // Which buffer is being written: 0=primary, 1=secondary, 2=drop
uint8_t g_cmd_flag = 0;
uint8_t g_cmd_flag2 = 0;  // Flag for secondary buffer
uint8_t g_cmd_length = 0;
uint8_t g_cmd_length2 = 0;  // Length for secondary buffer
static uint8_t g_cmd_length_drop = 0;   // Length for dropped packet (correct drain)
volatile uint32_t g_rx_drop_count = 0;  // Dropped packets (both buffers full)
volatile uint32_t g_unknown_cmd_count = 0;  // Unhandled function codes received

// Auto-report state
volatile uint8_t g_auto_report_enabled = 0;

// Buzzer state
static volatile uint16_t g_buzzer_on_time = 0;  // 0=off, 1=on, >=10 timed (ms)
static volatile uint32_t g_buzzer_start_tick = 0;  // Start time for timed beep

// Current robot velocities (updated by task_control)
static int16_t g_current_vx = 0;  // mm/s
static int16_t g_current_vy = 0;  // mm/s
static int16_t g_current_vz = 0;  // deg/s or rad/s × 1000

/* ========================================================================
 * PROTOCOL INITIALIZATION
 * ======================================================================== */

void protocol_init(void)
{
    // Clear reception state (both buffers)
    memset(g_rx_buffer, 0, sizeof(g_rx_buffer));
    memset(g_rx_buffer2, 0, sizeof(g_rx_buffer2));
    g_rx_index = 0;
    g_rx_state = RX_STATE_WAIT_HEADER;
    g_rx_active_buffer = 0;
    g_cmd_flag = 0;
    g_cmd_flag2 = 0;
    g_cmd_length = 0;
    g_cmd_length2 = 0;
    g_rx_drop_count = 0;

    // Disable auto-report by default (ROS will enable it)
    g_auto_report_enabled = 0;
}

/* ========================================================================
 * BYTE RECEPTION (Call from USART ISR)
 * ======================================================================== */

// Debug counter - increments for every byte received
volatile uint32_t g_rx_byte_count = 0;

/* Staging area for header bytes — avoids writing to g_rx_buffer
 * while the primary buffer might still be processed by the task. */
static uint8_t g_rx_staged_header = 0;
static uint8_t g_rx_staged_device = 0;

void protocol_receive_byte(uint8_t byte)
{
    g_rx_byte_count++;

    switch (g_rx_state)
    {
        case RX_STATE_WAIT_HEADER:
            if (byte == PTO_HEAD)
            {
                g_rx_staged_header = byte;
                g_rx_index = 1;
                g_rx_state = RX_STATE_WAIT_DEVICE;
            }
            break;

        case RX_STATE_WAIT_DEVICE:
            if (byte == PTO_DEVICE_ID)
            {
                g_rx_staged_device = byte;
                g_rx_index = 2;
                g_rx_state = RX_STATE_WAIT_LENGTH;
            }
            else
            {
                g_rx_state = RX_STATE_WAIT_HEADER;
                g_rx_index = 0;
            }
            break;

        case RX_STATE_WAIT_LENGTH:
            {
                uint8_t packet_length = byte + 2;

                if (packet_length > PTO_MAX_BUF_LEN || packet_length < 5)
                {
                    g_rx_state = RX_STATE_WAIT_HEADER;
                    g_rx_index = 0;
                }
                else
                {
                    if (!g_cmd_flag)
                    {
                        g_rx_active_buffer = 0;
                        g_rx_buffer[0] = g_rx_staged_header;
                        g_rx_buffer[1] = g_rx_staged_device;
                        g_rx_buffer[2] = byte;
                        g_cmd_length = packet_length;
                    }
                    else if (!g_cmd_flag2)
                    {
                        g_rx_active_buffer = 1;
                        g_rx_buffer2[0] = g_rx_staged_header;
                        g_rx_buffer2[1] = g_rx_staged_device;
                        g_rx_buffer2[2] = byte;
                        g_cmd_length2 = packet_length;
                    }
                    else
                    {
                        g_rx_active_buffer = 2;
                        g_cmd_length_drop = packet_length;
                        g_rx_drop_count++;
                    }

                    g_rx_index = 3;
                    g_rx_state = RX_STATE_READ_DATA;
                }
            }
            break;

        case RX_STATE_READ_DATA:
            {
                // Write to selected buffer based on g_rx_active_buffer
                if (g_rx_active_buffer == 0)
                {
                    g_rx_buffer[g_rx_index] = byte;
                }
                else if (g_rx_active_buffer == 1)
                {
                    g_rx_buffer2[g_rx_index] = byte;
                }
                // else g_rx_active_buffer == 2: drop mode, discard byte

                g_rx_index++;

                // Check if packet complete
                uint8_t target_length;
                if (g_rx_active_buffer == 0)
                    target_length = g_cmd_length;
                else if (g_rx_active_buffer == 1)
                    target_length = g_cmd_length2;
                else
                    target_length = g_cmd_length_drop;
                if (g_rx_index >= target_length)
                {
                    // Packet complete - set flag for processing
                    if (g_rx_active_buffer == 0)
                    {
                        g_cmd_flag = 1;
                    }
                    else if (g_rx_active_buffer == 1)
                    {
                        g_cmd_flag2 = 1;
                    }
                    // else: dropped, no flag set

                    // Reset state machine
                    g_rx_state = RX_STATE_WAIT_HEADER;
                    g_rx_index = 0;
                }
            }
            break;
    }
}

// Get RX byte count for debugging
uint32_t protocol_get_rx_count(void)
{
    return g_rx_byte_count;
}

/* ========================================================================
 * CHECKSUM FUNCTIONS
 * ======================================================================== */

uint8_t protocol_calculate_checksum(const uint8_t *data, uint8_t length)
{
    uint16_t sum = 0;

    // Sum bytes from index 2 to length-1
    for (uint8_t i = 2; i < length - 1; i++)
    {
        sum += data[i];
    }

    return (uint8_t)(sum & 0xFF);
}

uint8_t protocol_validate_checksum(const uint8_t *data, uint8_t length)
{
#if ENABLE_CHECKSUM
    uint8_t calculated = protocol_calculate_checksum(data, length);
    uint8_t received = data[length - 1];
    return (calculated == received) ? 1 : 0;
#else
    return 1;  // Always valid if checksums disabled
#endif
}

/* ========================================================================
 * PACKET TRANSMISSION
 * ======================================================================== */

void protocol_send_packet(uint8_t func_code, const uint8_t *data, uint8_t data_len)
{
    uint8_t packet[PTO_MAX_BUF_LEN];
    uint8_t packet_len = data_len + 5;  // Header + ID + Len + Func + Checksum

    // Build packet
    packet[0] = PTO_HEAD;
    packet[1] = PTO_DEVICE_ID_SEND;
    packet[2] = packet_len - 2;  // Length field
    packet[3] = func_code;

    // Copy payload
    if (data != NULL && data_len > 0)
    {
        memcpy(&packet[4], data, data_len);
    }

    // Calculate checksum
    packet[packet_len - 1] = protocol_calculate_checksum(packet, packet_len);

    // Send via USART
    hal_usart_send_bytes(packet, packet_len);
}

/* ========================================================================
 * COMMAND PARSER
 * ======================================================================== */

int8_t protocol_parse_command(void)
{
    // Double-buffer: check which buffer has a command ready
    uint8_t *rx_buf;
    uint8_t rx_len;
    uint8_t buffer_id;  // 0=primary, 1=secondary

    if (g_cmd_flag)
    {
        // Primary buffer has command
        rx_buf = g_rx_buffer;
        rx_len = g_cmd_length;
        buffer_id = 0;
    }
    else if (g_cmd_flag2)
    {
        // Secondary buffer has command
        rx_buf = g_rx_buffer2;
        rx_len = g_cmd_length2;
        buffer_id = 1;
    }
    else
    {
        // No command ready in either buffer
        return -1;
    }

    // Validate checksum
    if (!protocol_validate_checksum(rx_buf, rx_len))
    {
        DEBUG_ERROR("Checksum failed, len=%d buf=%d\n", rx_len, buffer_id);
        // Clear the appropriate flag
        if (buffer_id == 0)
            g_cmd_flag = 0;
        else
            g_cmd_flag2 = 0;
        return -1;  // Checksum failed
    }

    // Extract function code
    uint8_t func_code = rx_buf[3];

    // Debug: print received command
    DEBUG_VERBOSE("CMD: func=0x%02X len=%d buf=%d\n", func_code, rx_len, buffer_id);

    // Dispatch to handler (using selected buffer)
    switch (func_code)
    {
        case FUNC_AUTO_REPORT:
            protocol_handle_auto_report(&rx_buf[4]);
            break;

        case FUNC_MOTION:
            protocol_handle_motion(&rx_buf[4]);
            break;

        case FUNC_RESET_ODOM:
            protocol_handle_reset_odom();
            break;

        case FUNC_RESET_STATE:
            protocol_handle_reset_state();
            break;

        case FUNC_REQUEST_DATA:
            // Handle data request (e.g., version query)
            {
                uint8_t request_type = rx_buf[4];
                if (request_type == FUNC_VERSION)
                {
                    // Send firmware version using actual version from firmware_version.h
                    uint8_t version_data[2] = {FIRMWARE_VERSION_MAJOR, FIRMWARE_VERSION_MINOR};
                    protocol_send_packet(FUNC_VERSION, version_data, 2);
                }
            }
            break;

        case FUNC_BEEP:
            // Beep command - no response needed (fire-and-forget)
            // Protocol specification: no response for beep commands
            // Data: 2-byte on_time (0=off, 1=always on, >=10=on for xx ms)
            // Minimum valid packet: header(1)+device(1)+len_field(1)+func(1)+data[0](1)+data[1](1)+csum(1)
            // packet_length = len_field + 2, so packet_length >= 6 guarantees 2 data bytes
            if (rx_len >= 6)
            {
                uint16_t on_time = (uint16_t)((rx_buf[5] << 8) | rx_buf[4]);
                g_buzzer_on_time = on_time;

                if (on_time == 0)
                {
                    // Turn off buzzer
                    BUZZER_OFF();
                }
                else if (on_time == 1)
                {
                    // Turn on buzzer continuously
                    BUZZER_ON();
                }
                else
                {
                    // Turn on buzzer for timed duration (will be handled in monitoring task)
                    BUZZER_ON();
                    g_buzzer_start_tick = xTaskGetTickCount();
                }
            }
            break;

        case FUNC_SET_MOTOR_PID:
            protocol_handle_set_motor_pid(&rx_buf[4]);
            break;

        case FUNC_SET_YAW_PID:
            protocol_handle_set_yaw_pid(&rx_buf[4]);
            break;

        // FUNC_SET_MOTOR_PID_MULTILEVEL removed - using single PID only

        case FUNC_SET_MAG_CAL:
            protocol_handle_set_mag_cal(&rx_buf[4]);
            break;

        default:
            g_unknown_cmd_count++;
            break;
    }

    // Clear the appropriate command flag
    if (buffer_id == 0)
        g_cmd_flag = 0;
    else
        g_cmd_flag2 = 0;

    return 0;
}

/* ========================================================================
 * COMMAND HANDLERS
 * ======================================================================== */

void protocol_handle_auto_report(const uint8_t *data)
{
    uint8_t enable = data[0];

    if (enable == 0x00)
    {
        g_auto_report_enabled = 0;
    }
    else
    {
        g_auto_report_enabled = 1;
    }
}

void protocol_handle_motion(const uint8_t *data)
{
    // Update command timestamp for timeout safety (CRIT-3)
    control_update_command_time();

    // Parse motion command
    // Format: [Param][Vx_Lo][Vx_Hi][Vy_Lo][Vy_Hi][Vz_Lo][Vz_Hi]
    // Velocities are in mm/s (int16_t, little-endian)

    int16_t vx_mm = (int16_t)((data[2] << 8) | data[1]);  // mm/s
    int16_t vy_mm = (int16_t)((data[4] << 8) | data[3]);  // mm/s
    int16_t vz_raw = (int16_t)((data[6] << 8) | data[5]); // mrad/s (rad/s × 1000)

    // Speed clamping from config constants
    static const int16_t MAX_LINEAR_SPEED_MM = (int16_t)(MAX_LINEAR_VELOCITY_MPS * 1000.0f);
    static const int16_t MAX_ANGULAR_SPEED_MRAD = (int16_t)(MAX_ANGULAR_VELOCITY_RPS * 1000.0f);

    if (vx_mm > MAX_LINEAR_SPEED_MM) vx_mm = MAX_LINEAR_SPEED_MM;
    if (vx_mm < -MAX_LINEAR_SPEED_MM) vx_mm = -MAX_LINEAR_SPEED_MM;
    if (vy_mm > MAX_LINEAR_SPEED_MM) vy_mm = MAX_LINEAR_SPEED_MM;
    if (vy_mm < -MAX_LINEAR_SPEED_MM) vy_mm = -MAX_LINEAR_SPEED_MM;
    if (vz_raw > MAX_ANGULAR_SPEED_MRAD) vz_raw = MAX_ANGULAR_SPEED_MRAD;
    if (vz_raw < -MAX_ANGULAR_SPEED_MRAD) vz_raw = -MAX_ANGULAR_SPEED_MRAD;

    // Convert mm/s to m/s for control task
    float vx_m = (float)vx_mm / 1000.0f;
    float vy_m = (float)vy_mm / 1000.0f;

    // CRITICAL: Invert Vy to match ROSMaster protocol convention
    // Protocol uses negative Y for lateral velocity
    // This ensures strafing direction matches ROS2 expectations
    vy_m = -vy_m;

    // Convert angular velocity (mrad/s to rad/s)
    float vz_rad = (float)vz_raw / 1000.0f;

    // Check for zero command (stop)
    if (vx_mm == 0 && vy_mm == 0 && vz_raw == 0)
    {
        control_set_velocity(0.0f, 0.0f, 0.0f);
    }
    else
    {
        control_set_velocity(vx_m, vy_m, vz_rad);
    }

    // Store for internal tracking (not used for auto-report anymore)
    g_current_vx = vx_mm;
    g_current_vy = vy_mm;
    g_current_vz = vz_raw;
}

void protocol_handle_reset_state(void)
{
    // Stop motors
    control_set_velocity(0.0f, 0.0f, 0.0f);

    DEBUG_INFO("State reset: motors stopped\n");
}

void protocol_handle_reset_odom(void)
{
    // Reset firmware odometry to zero
    control_reset_odometry();

    DEBUG_INFO("Firmware odometry reset to zero\n");
}

/* ========================================================================
 * DATA REPORTING FUNCTIONS
 * ======================================================================== */

void protocol_send_motion_data(void)
{
    // Packet: [Vx_Lo][Vx_Hi][Vy_Lo][Vy_Hi][Vz_Lo][Vz_Hi][Battery]
    // CRITICAL: Send MEASURED velocities, not commanded velocities!
    // This provides actual velocity feedback from encoder readings.
    uint8_t data[7];

    // Get ACTUAL measured velocity from encoder feedback
    int16_t meas_vx, meas_vy, meas_vz;
    control_get_measured_velocity(&meas_vx, &meas_vy, &meas_vz);

    // Pack velocities (16-bit little-endian)
    data[0] = meas_vx & 0xFF;
    data[1] = (meas_vx >> 8) & 0xFF;
    data[2] = meas_vy & 0xFF;
    data[3] = (meas_vy >> 8) & 0xFF;
    data[4] = meas_vz & 0xFF;
    data[5] = (meas_vz >> 8) & 0xFF;

    // Battery voltage (0-255, multiply by 0.1 for volts on ROS 2 side)
    float voltage = battery_get_voltage();
    if (voltage < 0.0f) voltage = 0.0f;
    if (voltage > 25.5f) voltage = 25.5f;
    data[6] = (uint8_t)(voltage * 10.0f);

    protocol_send_packet(FUNC_REPORT_SPEED, data, sizeof(data));
}

void protocol_send_imu_raw_data(void)
{
    // Packet: [Gx_Lo][Gx_Hi][Gy_Lo][Gy_Hi][Gz_Lo][Gz_Hi]
    //         [Ax_Lo][Ax_Hi][Ay_Lo][Ay_Hi][Az_Lo][Az_Hi]
    //         [Mx_Lo][Mx_Hi][My_Lo][My_Hi][Mz_Lo][Mz_Hi]
    uint8_t data[18];

    // Read from task_imu cache (no SPI access — eliminates BUG-1 race)
    int16_t gyro[3], accel[3], mag[3];
    imu_task_get_raw_data(gyro, accel, mag);

    // Pack gyroscope (16-bit little-endian)
    data[0] = gyro[0] & 0xFF;
    data[1] = (gyro[0] >> 8) & 0xFF;
    data[2] = gyro[1] & 0xFF;
    data[3] = (gyro[1] >> 8) & 0xFF;
    data[4] = gyro[2] & 0xFF;
    data[5] = (gyro[2] >> 8) & 0xFF;

    // Pack accelerometer
    data[6] = accel[0] & 0xFF;
    data[7] = (accel[0] >> 8) & 0xFF;
    data[8] = accel[1] & 0xFF;
    data[9] = (accel[1] >> 8) & 0xFF;
    data[10] = accel[2] & 0xFF;
    data[11] = (accel[2] >> 8) & 0xFF;

    // Pack magnetometer
    data[12] = mag[0] & 0xFF;
    data[13] = (mag[0] >> 8) & 0xFF;
    data[14] = mag[1] & 0xFF;
    data[15] = (mag[1] >> 8) & 0xFF;
    data[16] = mag[2] & 0xFF;
    data[17] = (mag[2] >> 8) & 0xFF;

    protocol_send_packet(FUNC_REPORT_MPU_RAW, data, sizeof(data));
}

void protocol_send_imu_attitude_data(void)
{
    // Packet: [Roll_Lo][Roll_Hi][Pitch_Lo][Pitch_Hi][Yaw_Lo][Yaw_Hi]
    // Values: radians × 10000 (16-bit signed)
    uint8_t data[6];

    // Get attitude angles
    float roll, pitch, yaw;
    imu_get_attitude(&roll, &pitch, &yaw);

    // Convert to fixed-point (radians × 10000)
    int16_t roll_int = (int16_t)(roll * 10000.0f);
    int16_t pitch_int = (int16_t)(pitch * 10000.0f);
    int16_t yaw_int = (int16_t)(yaw * 10000.0f);

    // Pack data (16-bit little-endian)
    data[0] = roll_int & 0xFF;
    data[1] = (roll_int >> 8) & 0xFF;
    data[2] = pitch_int & 0xFF;
    data[3] = (pitch_int >> 8) & 0xFF;
    data[4] = yaw_int & 0xFF;
    data[5] = (yaw_int >> 8) & 0xFF;

    protocol_send_packet(FUNC_REPORT_IMU_ATT, data, sizeof(data));
}

void protocol_send_encoder_data(void)
{
    // Packet: [M1_0][M1_1][M1_2][M1_3][M2_0][M2_1][M2_2][M2_3]
    //         [M3_0][M3_1][M3_2][M3_3][M4_0][M4_1][M4_2][M4_3]
    // Values: 32-bit unsigned integers (little-endian)
    uint8_t data[16];

    // Get encoder counts
    int32_t enc[4];
    for (uint8_t i = 0; i < 4; i++)
    {
        enc[i] = encoder_get_count(i);
    }

    // Pack encoder counts (32-bit little-endian)
    for (uint8_t i = 0; i < 4; i++)
    {
        data[i * 4 + 0] = enc[i] & 0xFF;
        data[i * 4 + 1] = (enc[i] >> 8) & 0xFF;
        data[i * 4 + 2] = (enc[i] >> 16) & 0xFF;
        data[i * 4 + 3] = (enc[i] >> 24) & 0xFF;
    }

    protocol_send_packet(FUNC_REPORT_ENCODER, data, sizeof(data));
}

/* ========================================================================
 * PID TUNING HANDLERS
 * ======================================================================== */

void protocol_handle_set_motor_pid(const uint8_t *data)
{
    // Data format: [KP_Lo][KP_Hi][KI_Lo][KI_Hi][KD_Lo][KD_Hi][state]
    // Gains are int16_t little-endian, scaled by 1000
    int16_t kp_raw = (int16_t)((data[1] << 8) | data[0]);
    int16_t ki_raw = (int16_t)((data[3] << 8) | data[2]);
    int16_t kd_raw = (int16_t)((data[5] << 8) | data[4]);

    float kp = (float)kp_raw / 1000.0f;
    float ki = (float)ki_raw / 1000.0f;
    float kd = (float)kd_raw / 1000.0f;
    uint8_t state = data[6];

    control_set_motor_pid(kp, ki, kd);

    // Save to flash when state byte == SAVE_VERIFY (0x5F)
    if (state == SAVE_VERIFY)
    {
        flash_storage_save();
    }
}

void protocol_handle_set_yaw_pid(const uint8_t *data)
{
    int16_t kp_raw = (int16_t)((data[1] << 8) | data[0]);
    int16_t ki_raw = (int16_t)((data[3] << 8) | data[2]);
    int16_t kd_raw = (int16_t)((data[5] << 8) | data[4]);

    float kp = (float)kp_raw / 1000.0f;
    float ki = (float)ki_raw / 1000.0f;
    float kd = (float)kd_raw / 1000.0f;

    control_set_yaw_pid(kp, ki, kd);
}

/* ========================================================================
 * MAGNETOMETER CALIBRATION HANDLER
 * ======================================================================== */

void protocol_handle_set_mag_cal(const uint8_t *data)
{
    // Data format: [ox_lo][ox_hi][oy_lo][oy_hi][oz_lo][oz_hi]
    // Offsets are int16_t little-endian, scaled by 100 (µT × 100)
    int16_t ox_raw = (int16_t)((data[1] << 8) | data[0]);
    int16_t oy_raw = (int16_t)((data[3] << 8) | data[2]);
    int16_t oz_raw = (int16_t)((data[5] << 8) | data[4]);

    mag_calibration_t cal;
    imu_get_mag_calibration(&cal);

    cal.hard_iron_offset[0] = (float)ox_raw / 100.0f;
    cal.hard_iron_offset[1] = (float)oy_raw / 100.0f;
    cal.hard_iron_offset[2] = (float)oz_raw / 100.0f;
    cal.calibrated = 1;

    imu_set_mag_calibration(&cal);

    // Auto-save mag calibration to flash
    flash_storage_save();

    DEBUG_INFO("Mag cal set+saved: [%.2f, %.2f, %.2f] uT\n",
               cal.hard_iron_offset[0], cal.hard_iron_offset[1], cal.hard_iron_offset[2]);
}

/* ========================================================================
 * FIRMWARE ODOMETRY REPORTING
 * ======================================================================== */

void protocol_send_odometry_data(void)
{
    // Packet: 6× int32 LE = 24 bytes
    // [x_mm][y_mm][theta_mrad][vx_mms][vy_mms][omega_mrads]
    uint8_t data[24];

    float x, y, theta, vx, vy, omega;
    control_get_firmware_odometry(&x, &y, &theta, &vx, &vy, &omega);

    int32_t vals[6] = {
        (int32_t)(x * 1000.0f),         // m → mm
        (int32_t)(y * 1000.0f),         // m → mm
        (int32_t)(theta * 1000.0f),     // rad → mrad
        (int32_t)(vx * 1000.0f),        // m/s → mm/s
        (int32_t)(vy * 1000.0f),        // m/s → mm/s
        (int32_t)(omega * 1000.0f),     // rad/s → mrad/s
    };

    for (int i = 0; i < 6; i++)
    {
        data[i * 4 + 0] = vals[i] & 0xFF;
        data[i * 4 + 1] = (vals[i] >> 8) & 0xFF;
        data[i * 4 + 2] = (vals[i] >> 16) & 0xFF;
        data[i * 4 + 3] = (vals[i] >> 24) & 0xFF;
    }

    protocol_send_packet(FUNC_REPORT_ODOM, data, sizeof(data));
}

/* ========================================================================
 * BUZZER CONTROL
 * ======================================================================== */

void protocol_update_buzzer(void)
{
    // Handle timed buzzer (on_time >= 10)
    if (g_buzzer_on_time >= 10)
    {
        uint32_t current_tick = xTaskGetTickCount();
        uint32_t elapsed_ms = (current_tick - g_buzzer_start_tick) * portTICK_PERIOD_MS;

        if (elapsed_ms >= g_buzzer_on_time)
        {
            // Time expired, turn off buzzer
            BUZZER_OFF();
            g_buzzer_on_time = 0;
        }
    }
}
