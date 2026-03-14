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

#include <stdint.h>

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
 *
 * Gyro/accel values are raw ADC counts. Mag values are raw AK09916 counts.
 * Use imu_task_get_milli_data() for protocol-ready pre-scaled gyro/accel.
 */
void imu_task_get_raw_data(int16_t gyro[3], int16_t accel[3], int16_t mag[3]);

/**
 * @brief Get IMU data pre-scaled to milli-units for protocol transport (thread-safe)
 *
 * Reads calibrated g_imu_data (m/s², rad/s) and multiplies by 1000.
 * The ROS 2 driver applies ICM20948_ACCEL_RATIO = ICM20948_GYRO_RATIO = 1/1000
 * to recover SI units. Mag is excluded — use imu_task_get_raw_data() for mag.
 *
 * @param gyro_mrad_s  [out] Angular velocity in milli-rad/s
 * @param accel_mm_s2  [out] Linear acceleration in milli-m/s²
 */
void imu_task_get_milli_data(int16_t gyro_mrad_s[3], int16_t accel_mm_s2[3]);

#endif /* TASK_IMU_H */
