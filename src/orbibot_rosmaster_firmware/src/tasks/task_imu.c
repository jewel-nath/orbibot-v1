/**
 * @file task_imu.c
 * @brief IMU Task Implementation (CRITICAL - user emphasized)
 *
 * Handles IMU data acquisition and attitude estimation:
 * - Reads calibrated IMU data at 50Hz
 * - Integrates gyroscope Z-axis for yaw estimation
 * - Provides thread-safe access to attitude angles
 *
 * @author Jewel Nath
 * @date 2025-11-30
 */

#include "task_imu.h"
#include "FreeRTOS.h"
#include "task.h"
#include "imu_driver.h"
#include "task_monitoring.h"
#include "orbibot_config.h"
#include <math.h>

/* IMU update period in seconds */
#define IMU_DT              (1.0f / IMU_UPDATE_RATE_HZ)

/* Complementary filter weight for gyro vs magnetometer yaw correction.
 * At 50Hz: 0.98 gyro / 0.02 mag — gyro leads transient response,
 * mag slowly corrects long-term drift. */
#define YAW_CF_ALPHA        0.98f

/* Attitude state (protected by FreeRTOS task isolation) */
static volatile float g_roll = 0.0f;
static volatile float g_pitch = 0.0f;
static volatile float g_yaw = 0.0f;

/* Latest calibrated IMU data */
static volatile imu_data_t g_imu_data;

/**
 * @brief Get current attitude angles (thread-safe)
 * @param roll Pointer to roll angle (rad)
 * @param pitch Pointer to pitch angle (rad)
 * @param yaw Pointer to yaw angle (rad)
 *
 * Uses a critical section to guarantee a consistent snapshot of all three
 * angles. Without this, task_control (priority 10) preempting task_imu
 * (priority 8) between the roll and yaw reads would produce torn data.
 */
void imu_task_get_attitude(float *roll, float *pitch, float *yaw)
{
    taskENTER_CRITICAL();
    float r = g_roll;
    float p = g_pitch;
    float y = g_yaw;
    taskEXIT_CRITICAL();

    if (roll)  *roll  = r;
    if (pitch) *pitch = p;
    if (yaw)   *yaw   = y;
}

/**
 * @brief Reset yaw angle to zero
 *
 * Call this when robot position is known (e.g., at startup or after reset).
 */
void imu_task_reset_yaw(void)
{
    g_yaw = 0.0f;
}

/**
 * @brief IMU Task Entry Point
 *
 * Runs at 50Hz (20ms period):
 * 1. Reads calibrated IMU data (accel, gyro)
 * 2. Calculates roll/pitch from accelerometer
 * 3. Integrates gyro Z for yaw estimation
 */
void task_imu(void *params)
{
    (void)params;

    imu_data_t imu_data;
    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(1000 / IMU_UPDATE_RATE_HZ);

    /* Initialize attitude to zero */
    g_roll = 0.0f;
    g_pitch = 0.0f;
    g_yaw = 0.0f;

    for (;;)
    {
        /* Read calibrated IMU data */
        if (imu_read_calibrated(&imu_data) == 0)
        {
            /* Store latest data */
            g_imu_data = imu_data;

            /* Compute roll and pitch from accelerometer (no shared state) */
            float new_roll = -atan2f(imu_data.accel_x, imu_data.accel_z);
            float new_pitch = atan2f(-imu_data.accel_y,
                            sqrtf(imu_data.accel_x * imu_data.accel_x +
                                  imu_data.accel_z * imu_data.accel_z));

            /* Gyro integration step (read g_yaw inside critical section) */
            float prev_yaw;
            taskENTER_CRITICAL();
            prev_yaw = g_yaw;
            taskEXIT_CRITICAL();

            float gyro_yaw = prev_yaw + imu_data.gyro_z * IMU_DT;
            while (gyro_yaw > PI_F)  gyro_yaw -= 2.0f * PI_F;
            while (gyro_yaw < -PI_F) gyro_yaw += 2.0f * PI_F;

            /* Complementary filter: blend gyro with magnetometer heading */
            float new_yaw;
            if (imu_data.mag_x != 0.0f || imu_data.mag_y != 0.0f)
            {
                float mag_yaw = atan2f(-imu_data.mag_y, imu_data.mag_x);

                float diff = mag_yaw - gyro_yaw;
                while (diff > PI_F)  diff -= 2.0f * PI_F;
                while (diff < -PI_F) diff += 2.0f * PI_F;

                new_yaw = gyro_yaw + (1.0f - YAW_CF_ALPHA) * diff;
            }
            else
            {
                new_yaw = gyro_yaw;
            }

            /* Normalize final yaw to -PI to +PI */
            while (new_yaw > PI_F)  new_yaw -= 2.0f * PI_F;
            while (new_yaw < -PI_F) new_yaw += 2.0f * PI_F;

            /* Atomically update all three attitude values */
            taskENTER_CRITICAL();
            g_roll = new_roll;
            g_pitch = new_pitch;
            g_yaw = new_yaw;
            taskEXIT_CRITICAL();
        }

        task_alive_kick(ALIVE_TASK_IMU);

        vTaskDelayUntil(&last_wake_time, period);
    }
}
