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

#endif /* TASK_IMU_H */
