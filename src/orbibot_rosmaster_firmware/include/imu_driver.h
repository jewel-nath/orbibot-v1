/**
 * @file imu_driver.h
 * @brief ICM-20948 9-axis IMU Driver (SPI2) — OrbiBot public surface
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Supported operations:
 *   - init + gyro/accel/mag startup calibration (Welford variance)
 *   - single-shot raw + calibrated read (used by task_imu once per 20 ms)
 *   - magnetometer hard/soft-iron calibration round-trip
 *   - startup sensor-noise variance (future: transmit to ROS 2 EKF)
 *   - attitude forwarder (delegates to task_imu's complementary-filter cache)
 *
 * Everything else previously exported (per-axis float readers, self-test,
 * config accessors, is-alive probe) was removed on 2026-04-19 as dead
 * public API — it was GC'd by the linker anyway.
 */

#ifndef IMU_DRIVER_H
#define IMU_DRIVER_H

#include <stdint.h>
#include "robot_error.h"

/** Raw int16 sensor values (one SPI block read). */
typedef struct {
    int16_t accel_x, accel_y, accel_z;
    int16_t gyro_x, gyro_y, gyro_z;
    int16_t mag_x, mag_y, mag_z;
    int16_t temperature;
} imu_raw_data_t;

/** Calibrated SI-unit values (m/s², rad/s, µT, °C). */
typedef struct {
    float accel_x, accel_y, accel_z;   // m/s²
    float gyro_x, gyro_y, gyro_z;      // rad/s
    float mag_x, mag_y, mag_z;         // µT
    float temperature;                 // °C
} imu_data_t;

/** Mag hard/soft-iron calibration. Stored in flash, round-trips over 0x16. */
typedef struct {
    float hard_iron_offset[3];  // µT
    float soft_iron_matrix[9];  // 3×3 row-major; identity when uncalibrated
    uint8_t calibrated;
} mag_calibration_t;

/**
 * @brief Initialize ICM-20948 + AK09916 magnetometer. Also runs the 1000-sample
 *        gyro/accel calibration via imu_calibrate(). Blocks for ~1 s.
 * @return ROBOT_OK on success. Boot message identifies the exact WHO_AM_I
 *         value on failure (MPU-9250/6500 alternate chips, MISO stuck, etc.).
 */
robot_err_t imu_driver_init(void);

/** One-shot single-read filling raw int16 fields. */
robot_err_t imu_read_raw(imu_raw_data_t *data);

/** Single SPI transaction — fills raw AND calibrated values. */
robot_err_t imu_read_both(imu_raw_data_t *raw, imu_data_t *cal);

/**
 * @brief Startup-time gyro+accel zero-rate calibration using 1000 stationary
 *        samples. Also accumulates sample variance in a Welford pass.
 * @return 0 on success, -1 if too few valid samples (<500).
 */
int imu_calibrate(void);

/* Magnetometer calibration round-trip (used by flash_storage + protocol 0x16) */
void imu_set_mag_calibration(const mag_calibration_t *cal);
void imu_get_mag_calibration(mag_calibration_t *cal);

/**
 * @brief Return per-axis noise variance computed during imu_calibrate().
 *        Units: (m/s²)² for accel, (rad/s)² for gyro. Diagonal only.
 *        Either output pointer may be NULL.
 *
 * Currently the values live inside the firmware only — a future protocol
 * extension (see firmware-issue.md) will ship them to ROS 2 for the EKF.
 */
void imu_get_noise_variance(float accel_var[3], float gyro_var[3]);

/**
 * @brief Get latest attitude angles (rad). Thread-safe — reads the
 *        complementary-filter cache in task_imu.
 */
void imu_get_attitude(float *roll, float *pitch, float *yaw);

#endif // IMU_DRIVER_H
