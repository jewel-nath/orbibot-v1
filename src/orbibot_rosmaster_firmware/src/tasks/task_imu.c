/**
 * @file task_imu.c
 * @brief IMU Task Implementation (CRITICAL - user emphasized)
 *
 * Handles IMU data acquisition and attitude estimation:
 * - Reads calibrated IMU data at 50Hz
 * - Roll/pitch from accelerometer (gravity vector)
 * - Yaw from pure gyro Z integration (no mag — heading correction
 *   provided by EKF + slam_toolbox at the ROS 2 layer; magnetometer
 *   was removed 2026-04-28 due to indoor SS-frame contamination making
 *   mag readings unreliable)
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

/* Attitude state (protected by FreeRTOS task isolation) */
static volatile float g_roll = 0.0f;
static volatile float g_pitch = 0.0f;
static volatile float g_yaw = 0.0f;

/* Latest calibrated IMU data */
static volatile imu_data_t g_imu_data;

/* Cached raw int16 IMU data for protocol reporting (eliminates SPI race) */
static volatile int16_t g_raw_gyro[3]  = {0};
static volatile int16_t g_raw_accel[3] = {0};

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

void imu_task_get_raw_data(int16_t gyro[3], int16_t accel[3])
{
    taskENTER_CRITICAL();
    for (int i = 0; i < 3; i++)
    {
        gyro[i]  = g_raw_gyro[i];
        accel[i] = g_raw_accel[i];
    }
    taskEXIT_CRITICAL();
}

/**
 * @brief Get IMU data pre-scaled to milli-units for protocol transport (thread-safe)
 *
 * Reads from the calibrated g_imu_data cache (already in SI: m/s², rad/s) and
 * multiplies by 1000 so the ROS 2 driver can apply ×(1/1000) to recover SI units.
 *
 * Sensor ranges are sized to prevent int16 overflow:
 *   Gyro  ±500 dps  → max ±8 727 milli-rad/s  (< 32 767) ✅
 *   Accel ±2 g      → max ±19 613 milli-m/s²  (< 32 767) ✅
 *
 * @param gyro_mrad_s  [out] Angular velocity in milli-rad/s (×1000 rad/s)
 * @param accel_mm_s2  [out] Linear acceleration in milli-m/s² (×1000 m/s²)
 */
void imu_task_get_milli_data(int16_t gyro_mrad_s[3], int16_t accel_mm_s2[3])
{
    taskENTER_CRITICAL();
    gyro_mrad_s[0]  = (int16_t)(g_imu_data.gyro_x  * 1000.0f);
    gyro_mrad_s[1]  = (int16_t)(g_imu_data.gyro_y  * 1000.0f);
    gyro_mrad_s[2]  = (int16_t)(g_imu_data.gyro_z  * 1000.0f);
    accel_mm_s2[0]  = (int16_t)(g_imu_data.accel_x * 1000.0f);
    accel_mm_s2[1]  = (int16_t)(g_imu_data.accel_y * 1000.0f);
    accel_mm_s2[2]  = (int16_t)(g_imu_data.accel_z * 1000.0f);
    taskEXIT_CRITICAL();
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
        /* Single SPI read: get both raw (for protocol cache) and calibrated data */
        imu_raw_data_t raw;
        if (imu_read_both(&raw, &imu_data) == 0)
        {
            /* Cache raw int16 values for protocol reporting (no SPI from comm task) */
            taskENTER_CRITICAL();
            g_raw_gyro[0]  = raw.gyro_x;
            g_raw_gyro[1]  = raw.gyro_y;
            g_raw_gyro[2]  = raw.gyro_z;
            g_raw_accel[0] = raw.accel_x;
            g_raw_accel[1] = raw.accel_y;
            g_raw_accel[2] = raw.accel_z;
            taskEXIT_CRITICAL();

            g_imu_data = imu_data;

            /* Compute roll and pitch from accelerometer (no shared state) */
            float new_roll = -atan2f(imu_data.accel_x, imu_data.accel_z);
            float new_pitch = atan2f(-imu_data.accel_y,
                            sqrtf(imu_data.accel_x * imu_data.accel_x +
                                  imu_data.accel_z * imu_data.accel_z));

            /* Gyro-only yaw integration. Heading correction is handled at the
             * ROS 2 layer (Madgwick + EKF + slam_toolbox/AMCL), so this task
             * just integrates and lets long-term drift be corrected upstream. */
            float prev_yaw;
            taskENTER_CRITICAL();
            prev_yaw = g_yaw;
            taskEXIT_CRITICAL();

            float new_yaw = prev_yaw + imu_data.gyro_z * IMU_DT;
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
