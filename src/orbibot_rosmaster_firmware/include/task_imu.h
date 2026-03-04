/**
 * @file task_imu.h
 * @brief IMU Task Interface
 *
 * Provides IMU data acquisition and attitude estimation.
 *
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef TASK_IMU_H
#define TASK_IMU_H

/**
 * @brief IMU Task Entry Point
 * @param params Task parameters (unused)
 */
void task_imu(void *params);

/**
 * @brief Get current attitude angles from IMU task
 * @param roll Pointer to roll angle (rad)
 * @param pitch Pointer to pitch angle (rad)
 * @param yaw Pointer to yaw angle (rad, integrated from gyro)
 */
void imu_task_get_attitude(float *roll, float *pitch, float *yaw);

/**
 * @brief Reset yaw angle to zero
 */
void imu_task_reset_yaw(void);

/**
 * @brief Get cached raw IMU data (thread-safe, no SPI access)
 *
 * Returns the raw int16 values from the most recent task_imu read.
 * This eliminates the SPI race condition (BUG-1) by ensuring only
 * task_imu performs SPI reads; all other tasks read from this cache.
 */
void imu_task_get_raw_data(int16_t gyro[3], int16_t accel[3], int16_t mag[3]);

#endif /* TASK_IMU_H */
