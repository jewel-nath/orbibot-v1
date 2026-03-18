/**
 * @file task_communication.c
 * @brief Communication Task Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * This task handles serial communication with ROS 2 hardware node:
 * - Parses incoming commands (FUNC_MOTION, FUNC_AUTO_REPORT)
 * - Transmits auto-report data (motion, IMU, encoders)
 *
 * Uses ROSMaster compatible protocol for ROS 2 integration.
 * Reports 5 data types at 20Hz each (100 packets/sec total).
 */

#include "task_communication.h"
#include "FreeRTOS.h"
#include "task.h"
#include "hal_usart.h"
#include "protocol.h"
#include "task_monitoring.h"

/**
 * @brief Communication Task Entry Point
 * @param params Task parameters (unused)
 *
 * Auto-report timing configuration:
 * - 50ms cycle = 20Hz per data type
 * - 5 data types: Speed, IMU Raw, IMU Attitude, Encoders, Odometry
 * - Reports spread 10ms apart within cycle
 */
void task_communication(void *params)
{
    (void)params;

    uint16_t report_count = 0;

    // Cycle configuration for auto-report:
    // - 50 counts × 1ms = 50ms cycle = 20Hz per data type
    // - Reports at counts 1, 11, 21, 31, 41 (spread 10ms apart)
    // - 5 data types = 100 packets/sec total
    static const uint16_t AUTO_SEND_CYCLE = 50;

    // Initial delay
    vTaskDelay(pdMS_TO_TICKS(AUTO_SEND_CYCLE));

    for (;;)
    {
        // 1. Check for and process incoming commands
        if (protocol_is_command_ready())
        {
            protocol_parse_command();
        }

        // 2. Auto-report data if enabled (20Hz per type = 50ms cycle)
        // Timing slots for interleaved reporting:
        // - count 1:  Motion/Speed (Vx, Vy, Vz, Battery)
        // - count 11: IMU Raw (gyro, accel, mag)
        // - count 21: IMU Attitude (roll, pitch, yaw)
        // - count 31: Encoders (4 motor counts)
        // - count 41: Firmware Odometry (x, y, theta, vx, vy, omega)
        if (protocol_is_auto_report_enabled())
        {
            if (report_count == 1)
            {
                protocol_send_motion_data();
            }
            else if (report_count == 11)
            {
                protocol_send_imu_raw_data();
            }
            else if (report_count == 21)
            {
                protocol_send_imu_attitude_data();
            }
            else if (report_count == 31)
            {
                protocol_send_encoder_data();
            }
            else if (report_count == 41)
            {
                protocol_send_odometry_data();
            }
        }

        // Update counter (G10: Fixed off-by-one, reset at 50 not 51)
        report_count++;
        if (report_count >= AUTO_SEND_CYCLE)
        {
            report_count = 0;
        }

        // Drive buzzer timing state machine at 1ms cadence (handles timed and double-beep)
        protocol_update_buzzer();

        task_alive_kick(ALIVE_TASK_COMM);

        vTaskDelay(pdMS_TO_TICKS(1));
    }
}
