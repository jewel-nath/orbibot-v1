/**
 * @file protocol.h
 * @brief Serial Communication Protocol (ROSMaster Compatible)
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * ROSMaster compatible serial protocol for communication with
 * ROS 2 hardware node (rosmaster_driver.py).
 *
 * Packet Format:
 * [Header][Device_ID][Length][Function][Data...][Checksum]
 *
 * See HARDWARE_DOC.md for detailed protocol specification
 */

#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>
#include "orbibot_config.h"

/* ========================================================================
 * PROTOCOL CONSTANTS
 * ======================================================================== */

/**
 * Packet Structure Constants
 */
#define PTO_HEAD                0xFF    // Packet header byte
#define PTO_DEVICE_ID           0xFC    // Device ID (receive commands with 0xFC)
#define PTO_DEVICE_ID_SEND      0xFB    // Device ID for sending (0xFC-1)
#define PTO_MAX_BUF_LEN         60      // Maximum buffer length (increased for odom/cal packets)

/**
 * Protocol Configuration
 */
#define ENABLE_CHECKSUM         1       // Enable checksum validation

/* Auto-report cycle is set by AUTO_SEND_CYCLE inside task_communication.c
 * (1ms tick × 20 counts = 20ms → 50Hz per report type). */

/* ========================================================================
 * FUNCTION CODES (ROSMaster Protocol)
 * ======================================================================== */

/**
 * System Functions (0x01-0x0F)
 */
#define FUNC_AUTO_REPORT        0x01    // Enable/disable auto-reporting
#define FUNC_BEEP               0x02    // Beep control
#define FUNC_RESET_ENCODERS     0x08    // Reset encoder counts to zero (odometry unchanged)
#define FUNC_RESET_ODOM         0x09    // Reset firmware odometry to zero
#define FUNC_RESET_STATE        0x0F    // Reset system state

/**
 * Data Reporting Functions (0x0A-0x0E)
 */
#define FUNC_REPORT_SPEED       0x0A    // Report motion speed (Vx, Vy, Vz, Battery)
#define FUNC_REPORT_IMU_ATT     0x0C    // Report IMU attitude (roll, pitch, yaw)
#define FUNC_REPORT_ENCODER     0x0D    // Report encoder counts (4 motors)
#define FUNC_REPORT_ICM_RAW     0x0E    // Report ICM-20948 raw data (outgoing only)

/**
 * Motion Control Functions (0x10-0x1F)
 * Only FUNC_MOTION (0x12) through FUNC_SET_MAG_CAL (0x16) are dispatched.
 */
#define FUNC_MOTION             0x12    // 3D velocity control (Vx, Vy, Vz)
#define FUNC_SET_MOTOR_PID      0x13    // Set motor PID parameters
#define FUNC_SET_YAW_PID        0x14    // Set yaw PID parameters
#define FUNC_REPORT_ODOM        0x15    // Report firmware odometry (x, y, theta, vx, vy, omega)
#define FUNC_SET_MAG_CAL        0x16    // Set magnetometer calibration data

/**
 * Request Functions (0x50-0x5F)
 * Both 0x50+0x51 (legacy) and direct 0x51 (Python-driver convention) work.
 */
#define FUNC_REQUEST_DATA       0x50    // Legacy request wrapper (takes sub-byte)
#define FUNC_VERSION            0x51    // Get firmware version — direct or via 0x50

/* ---------------------------------------------------------------------
 * Reserved ROSMaster protocol codes — NOT dispatched by this firmware.
 * Kept as comment-only reference so a 3rd-party host sending them just
 * falls through to the `default` case in protocol_parse_command() and
 * increments g_unknown_cmd_count without side effects.
 *
 *   0x03  PWM_SERVO          (single servo)
 *   0x04  PWM_SERVO_ALL      (all 4 servos)
 *   0x05  RGB                (RGB LED)
 *   0x06  RGB_EFFECT         (RGB effects)
 *   0x10  MOTOR              (direct motor PWM — Yahboom reference only)
 *   0x11  CAR_RUN            (directional control)
 *   0x17  CAR_TYPE           (mecanum/ackerman select)
 *   0x20  UART_SERVO         (serial bus servo)
 *   0x21  UART_SERVO_ID      (servo ID assignment)
 *   0x22  UART_SERVO_TORQUE  (servo torque)
 *   0x23  ARM_CTRL           (robotic arm)
 *   0x24  ARM_OFFSET         (arm calibration)
 *   0x30  AKM_DEF_ANGLE      (Ackerman default)
 *   0x31  AKM_STEER_ANGLE    (Ackerman steering)
 *   0x52  NOW_YAW            (query current yaw)
 *   0x60  CAN_RX_BEEP        (CAN bus)
 *   0x70  OLED_FLAG          (OLED display)
 *   0xA0  RESET_FLASH        (flash reset)
 *   0xA1  TEST_MODE          (factory test)
 *   0xA2  TEST_CLEAR_YAW     (test mode — clear yaw)
 * --------------------------------------------------------------------- */

/**
 * Verification Values
 */
#define SAVE_VERIFY             0x5F    // Verify byte for flash saves

/* ========================================================================
 * COMMUNICATION STATE
 * ======================================================================== */

/**
 * Reception State Machine States
 */
typedef enum {
    RX_STATE_WAIT_HEADER = 0,   // Waiting for 0xFF
    RX_STATE_WAIT_DEVICE,       // Waiting for 0xFC
    RX_STATE_WAIT_LENGTH,       // Reading length byte
    RX_STATE_READ_DATA          // Reading payload
} rx_state_t;

/**
 * Global Communication Buffers
 */
extern uint8_t g_rx_buffer[PTO_MAX_BUF_LEN];    // Reception buffer (primary)
extern uint8_t g_rx_index;                      // Current buffer index
extern rx_state_t g_rx_state;                   // State machine state
extern uint8_t g_cmd_flag;                      // Primary buffer command ready flag
extern uint8_t g_cmd_flag2;                     // Secondary buffer command ready flag
extern uint8_t g_cmd_length;                    // Command length

/**
 * Auto-Report State
 */
extern volatile uint8_t g_auto_report_enabled;  // Auto-report enable flag

/* ========================================================================
 * FUNCTION PROTOTYPES
 * ======================================================================== */

/**
 * @brief Initialize protocol communication
 */
void protocol_init(void);

/**
 * @brief Process received byte (call from USART ISR)
 * @param byte Received byte
 */
void protocol_receive_byte(uint8_t byte);

/**
 * @brief Parse and execute command (call from task)
 * @return 0 on success, -1 on error
 */
int8_t protocol_parse_command(void);

/**
 * @brief Calculate checksum for data buffer
 * @param data Pointer to data buffer
 * @param length Length of data (from byte 2 to end)
 * @return 8-bit checksum value
 */
uint8_t protocol_calculate_checksum(const uint8_t *data, uint8_t length);

/**
 * @brief Validate checksum of received packet
 * @param data Pointer to data buffer
 * @param length Total packet length
 * @return 1 if valid, 0 if invalid
 */
uint8_t protocol_validate_checksum(const uint8_t *data, uint8_t length);

/**
 * @brief Send data packet
 * @param func_code Function code
 * @param data Pointer to data payload
 * @param data_len Length of data payload
 */
void protocol_send_packet(uint8_t func_code, const uint8_t *data, uint8_t data_len);

/* ========================================================================
 * DATA REPORTING FUNCTIONS
 * ======================================================================== */

/**
 * @brief Send motion speed data (Vx, Vy, Vz, battery)
 */
void protocol_send_motion_data(void);

/**
 * @brief Send raw IMU data (gyro, accel, mag)
 */
void protocol_send_imu_raw_data(void);

/**
 * @brief Send IMU attitude data (roll, pitch, yaw)
 */
void protocol_send_imu_attitude_data(void);

/**
 * @brief Send encoder counts (4 motors)
 */
void protocol_send_encoder_data(void);

/* ========================================================================
 * COMMAND HANDLERS
 * ======================================================================== */

/**
 * @brief Handle FUNC_AUTO_REPORT command
 * @param data Pointer to command data
 */
void protocol_handle_auto_report(const uint8_t *data);

/**
 * @brief Handle FUNC_MOTION command
 * @param data Pointer to command data
 */
void protocol_handle_motion(const uint8_t *data);

/**
 * @brief Handle FUNC_RESET_STATE command
 */
void protocol_handle_reset_state(void);

/**
 * @brief Handle FUNC_RESET_ODOM command
 */
void protocol_handle_reset_odom(void);

/**
 * @brief Handle FUNC_RESET_ENCODERS command
 */
void protocol_handle_reset_encoders(void);

/**
 * @brief Handle FUNC_SET_MOTOR_PID command
 * @param data Pointer to command data [KP_Lo][KP_Hi][KI_Lo][KI_Hi][KD_Lo][KD_Hi][state]
 *
 * Gains are int16_t little-endian, scaled by 1000 (e.g., 0.8 → 800).
 */
void protocol_handle_set_motor_pid(const uint8_t *data);

/**
 * @brief Handle FUNC_SET_YAW_PID command
 * @param data Pointer to command data [KP_Lo][KP_Hi][KI_Lo][KI_Hi][KD_Lo][KD_Hi][state]
 *
 * Gains are int16_t little-endian, scaled by 1000 (e.g., 0.4 → 400).
 */
void protocol_handle_set_yaw_pid(const uint8_t *data);

/**
 * @brief Handle FUNC_SET_MAG_CAL command
 * @param data Pointer to command data [offset_x_lo][offset_x_hi]... (3× int16, scaled ×100)
 */
void protocol_handle_set_mag_cal(const uint8_t *data);

/**
 * @brief Send firmware odometry data (x, y, theta, vx, vy, omega)
 */
void protocol_send_odometry_data(void);

/**
 * @brief Update buzzer state for timed beeps and patterns.
 * Call from task_communication at ~1ms cadence for accurate timing.
 */
void protocol_update_buzzer(void);

/**
 * @brief Trigger a non-blocking double-beep (200ms on/off/on/off) for battery warning.
 * State machine is advanced by protocol_update_buzzer().
 */
void protocol_start_double_beep(void);

/* ========================================================================
 * INLINE HELPER FUNCTIONS
 * ======================================================================== */

/**
 * @brief Check if any command is ready to process (primary or secondary buffer)
 * @return 1 if ready, 0 if not
 *
 * Checks both double-buffer slots. protocol_parse_command() handles
 * prioritizing the primary buffer first, but we must know to call it
 * even when only the secondary buffer has data.
 */
static inline uint8_t protocol_is_command_ready(void)
{
    return g_cmd_flag || g_cmd_flag2;
}

/**
 * @brief Check if auto-reporting is enabled
 * @return 1 if enabled, 0 if disabled
 */
static inline uint8_t protocol_is_auto_report_enabled(void)
{
    return g_auto_report_enabled;
}

#endif // PROTOCOL_H
