/**
 * @file imu_driver.h
 * @brief ICM-20948 9-Axis IMU Driver
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Driver for TDK InvenSense ICM-20948 9-axis motion tracking sensor.
 *
 * Features:
 * - 3-axis gyroscope (±250, ±500, ±1000, ±2000 dps)
 * - 3-axis accelerometer (±2g, ±4g, ±8g, ±16g)
 * - 3-axis magnetometer (AK09916)
 * - Digital Motion Processor (DMP)
 * - SPI interface @ 8MHz
 *
 * CRITICAL: User emphasized IMU is mandatory for OrbiBot.
 * This driver includes robust error handling and timeout protection.
 */

#ifndef IMU_DRIVER_H
#define IMU_DRIVER_H

#include <stdint.h>

/**
 * @brief IMU data structure for raw sensor readings
 */
typedef struct
{
    int16_t accel_x;    // Accelerometer X-axis (raw ADC counts)
    int16_t accel_y;    // Accelerometer Y-axis
    int16_t accel_z;    // Accelerometer Z-axis

    int16_t gyro_x;     // Gyroscope X-axis (raw ADC counts)
    int16_t gyro_y;     // Gyroscope Y-axis
    int16_t gyro_z;     // Gyroscope Z-axis

    int16_t mag_x;      // Magnetometer X-axis (raw ADC counts)
    int16_t mag_y;      // Magnetometer Y-axis
    int16_t mag_z;      // Magnetometer Z-axis

    int16_t temperature;  // Die temperature (raw ADC counts)
} imu_raw_data_t;

/**
 * @brief IMU data structure for calibrated sensor readings
 */
typedef struct
{
    float accel_x;      // Accelerometer X-axis (m/s²)
    float accel_y;      // Accelerometer Y-axis (m/s²)
    float accel_z;      // Accelerometer Z-axis (m/s²)

    float gyro_x;       // Gyroscope X-axis (rad/s)
    float gyro_y;       // Gyroscope Y-axis (rad/s)
    float gyro_z;       // Gyroscope Z-axis (rad/s)

    float mag_x;        // Magnetometer X-axis (µT)
    float mag_y;        // Magnetometer Y-axis (µT)
    float mag_z;        // Magnetometer Z-axis (µT)

    float temperature;  // Die temperature (°C)
} imu_data_t;

/**
 * @brief IMU configuration structure
 */
typedef struct
{
    uint8_t accel_range;    // 0=2g, 1=4g, 2=8g, 3=16g
    uint8_t gyro_range;     // 0=250dps, 1=500dps, 2=1000dps, 3=2000dps
    uint8_t accel_dlpf;     // Digital low-pass filter (0-7)
    uint8_t gyro_dlpf;      // Digital low-pass filter (0-7)
    uint16_t sample_rate;   // Sample rate divider
} imu_config_t;

/**
 * @brief Magnetometer calibration data (hard/soft iron correction)
 */
typedef struct
{
    float hard_iron_offset[3];  // Bias offset [x, y, z] in µT
    float soft_iron_matrix[9];  // 3x3 correction matrix (row-major)
    uint8_t calibrated;         // 0 = uncalibrated, 1 = calibrated
} mag_calibration_t;

/**
 * @brief Initialize ICM-20948 IMU
 *
 * Initialization sequence:
 * 1. Reset device
 * 2. Verify WHO_AM_I register (0xEA)
 * 3. Configure gyroscope and accelerometer ranges
 * 4. Configure DLPF (digital low-pass filter)
 * 5. Configure sample rate
 * 6. Enable magnetometer (AK09916)
 *
 * @return 0 on success, -1 on failure
 */
int imu_driver_init(void);

/**
 * @brief Read raw sensor data from IMU
 * @param data Pointer to structure for raw data
 * @return 0 on success, -1 on failure
 */
int imu_read_raw(imu_raw_data_t *data);

/**
 * @brief Read calibrated sensor data from IMU
 * @param data Pointer to structure for calibrated data
 * @return 0 on success, -1 on failure
 */
int imu_read_calibrated(imu_data_t *data);

/**
 * @brief Read accelerometer only
 * @param accel_x Pointer for X-axis (m/s²)
 * @param accel_y Pointer for Y-axis (m/s²)
 * @param accel_z Pointer for Z-axis (m/s²)
 * @return 0 on success, -1 on failure
 */
int imu_read_accel(float *accel_x, float *accel_y, float *accel_z);

/**
 * @brief Read gyroscope only
 * @param gyro_x Pointer for X-axis (rad/s)
 * @param gyro_y Pointer for Y-axis (rad/s)
 * @param gyro_z Pointer for Z-axis (rad/s)
 * @return 0 on success, -1 on failure
 */
int imu_read_gyro(float *gyro_x, float *gyro_y, float *gyro_z);

/**
 * @brief Read magnetometer only
 * @param mag_x Pointer for X-axis (µT)
 * @param mag_y Pointer for Y-axis (µT)
 * @param mag_z Pointer for Z-axis (µT)
 * @return 0 on success, -1 on failure
 */
int imu_read_mag(float *mag_x, float *mag_y, float *mag_z);

/**
 * @brief Read die temperature
 * @return Temperature in degrees Celsius
 */
float imu_read_temperature(void);

/**
 * @brief Calibrate IMU (gyroscope zero-rate offset)
 *
 * Device must be stationary during calibration.
 * Takes 1000 samples and calculates average offsets.
 *
 * @return 0 on success, -1 on failure
 */
int imu_calibrate(void);

/**
 * @brief Set IMU configuration
 * @param config Pointer to configuration structure
 * @return 0 on success, -1 on failure
 */
int imu_set_config(const imu_config_t *config);

/**
 * @brief Get current IMU configuration
 * @param config Pointer to structure for configuration
 * @return 0 on success, -1 on failure
 */
int imu_get_config(imu_config_t *config);

/**
 * @brief Reset IMU to default configuration
 * @return 0 on success, -1 on failure
 */
int imu_reset(void);

/**
 * @brief Check if IMU is responding
 * @return 1 if IMU is alive, 0 if not responding
 */
int imu_is_alive(void);

/**
 * @brief Perform IMU self-test
 * @return 0 on success, -1 on failure
 */
int imu_self_test(void);

/* ========================================================================
 * MAGNETOMETER CALIBRATION FUNCTIONS
 * ======================================================================== */

/**
 * @brief Set magnetometer calibration data
 * @param cal Pointer to calibration data
 */
void imu_set_mag_calibration(const mag_calibration_t *cal);

/**
 * @brief Get current magnetometer calibration data
 * @param cal Pointer to store calibration data
 */
void imu_get_mag_calibration(mag_calibration_t *cal);

/* ========================================================================
 * PROTOCOL-COMPATIBLE WRAPPER FUNCTIONS
 * ======================================================================== */

/**
 * @brief Get raw gyroscope data as int16 array
 * @param gyro Array of 3 int16_t values [X, Y, Z]
 */
void imu_get_gyro_raw(int16_t gyro[3]);

/**
 * @brief Get raw accelerometer data as int16 array
 * @param accel Array of 3 int16_t values [X, Y, Z]
 */
void imu_get_accel_raw(int16_t accel[3]);

/**
 * @brief Get raw magnetometer data as int16 array
 * @param mag Array of 3 int16_t values [X, Y, Z]
 */
void imu_get_mag_raw(int16_t mag[3]);

/**
 * @brief Get all raw IMU data in single SPI read (efficient)
 * @param gyro Array of 3 int16_t values [X, Y, Z]
 * @param accel Array of 3 int16_t values [X, Y, Z]
 * @param mag Array of 3 int16_t values [X, Y, Z]
 */
void imu_get_all_raw(int16_t gyro[3], int16_t accel[3], int16_t mag[3]);

/**
 * @brief Get attitude angles (roll, pitch, yaw)
 * @param roll Pointer to roll angle (radians)
 * @param pitch Pointer to pitch angle (radians)
 * @param yaw Pointer to yaw angle (radians)
 */
void imu_get_attitude(float *roll, float *pitch, float *yaw);

#endif // IMU_DRIVER_H
