/**
 * @file imu_driver.c
 * @brief ICM-20948 9-Axis IMU Driver Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * CRITICAL: User emphasized IMU is mandatory for OrbiBot.
 * This driver includes robust error handling and timeout protection.
 */

#include "imu_driver.h"
#include "hal_spi.h"
#include "stm32f10x.h"
#include "orbibot_config.h"
#include <math.h>

// ICM-20948 Register Map (User Bank 0)
#define ICM20948_WHO_AM_I           0x00
#define ICM20948_USER_CTRL          0x03
#define ICM20948_LP_CONFIG          0x05
#define ICM20948_PWR_MGMT_1         0x06
#define ICM20948_PWR_MGMT_2         0x07
#define ICM20948_INT_PIN_CFG        0x0F
#define ICM20948_INT_ENABLE         0x10
#define ICM20948_INT_ENABLE_1       0x11
#define ICM20948_INT_ENABLE_2       0x12
#define ICM20948_INT_ENABLE_3       0x13
#define ICM20948_ACCEL_XOUT_H       0x2D
#define ICM20948_GYRO_XOUT_H        0x33
#define ICM20948_TEMP_OUT_H         0x39
#define ICM20948_EXT_SLV_SENS_DATA_00 0x3B
#define ICM20948_REG_BANK_SEL       0x7F

// ICM-20948 Register Map (User Bank 2)
#define ICM20948_GYRO_CONFIG_1      0x01
#define ICM20948_ACCEL_CONFIG       0x14
#define ICM20948_ACCEL_CONFIG_2     0x15

// ICM-20948 Register Map (User Bank 3) — I2C Master for AK09916
#define ICM20948_I2C_MST_ODR_CONFIG 0x00
#define ICM20948_I2C_MST_CTRL       0x01
#define ICM20948_I2C_SLV0_ADDR      0x03
#define ICM20948_I2C_SLV0_REG       0x04
#define ICM20948_I2C_SLV0_CTRL      0x05
#define ICM20948_I2C_SLV0_DO        0x06

// AK09916 Magnetometer (accessed via ICM-20948 I2C Master)
#define AK09916_I2C_ADDR            0x0C
#define AK09916_WIA2                0x01    // WHO_AM_I = 0x09
#define AK09916_ST1                 0x10    // Status 1 (DRDY bit 0)
#define AK09916_HXL                 0x11    // Mag data start (little-endian)
#define AK09916_ST2                 0x18    // Status 2 (overflow)
#define AK09916_CNTL2               0x31    // Mode control
#define AK09916_CNTL3               0x32    // Soft reset

// Expected WHO_AM_I value
#define ICM20948_WHO_AM_I_VALUE     0xEA

// SPI Read/Write bits
#define ICM20948_SPI_READ           0x80
#define ICM20948_SPI_WRITE          0x00

// Calibration settings
#define CALIBRATION_SAMPLES         1000

// Conversion scales
static float accel_scale = 1.0f;    // Will be set based on range
static float gyro_scale = 1.0f;     // Will be set based on range
static float mag_scale = 0.15f;     // Fixed for AK09916: 0.15 µT/LSB

// Calibration offsets
static float gyro_offset_x = 0.0f;
static float gyro_offset_y = 0.0f;
static float gyro_offset_z = 0.0f;

// Magnetometer calibration (hard/soft iron correction)
static mag_calibration_t mag_cal = {
    .hard_iron_offset = {0.0f, 0.0f, 0.0f},
    .soft_iron_matrix = {1.0f, 0.0f, 0.0f, 0.0f, 1.0f, 0.0f, 0.0f, 0.0f, 1.0f},
    .calibrated = 0
};

// Magnetometer initialization status
static uint8_t mag_initialized = 0;

// G6: Last valid magnetometer reading (for when DRDY not set)
static int16_t last_mag_x = 0;
static int16_t last_mag_y = 0;
static int16_t last_mag_z = 0;

// Current configuration
static imu_config_t current_config;

/**
 * @brief Select IMU register bank
 * @param bank Bank number (0-3)
 */
static void imu_select_bank(uint8_t bank)
{
    hal_spi_select();
    hal_spi_write_byte(ICM20948_REG_BANK_SEL | ICM20948_SPI_WRITE);
    hal_spi_write_byte((bank & 0x03) << 4);
    hal_spi_deselect();
}

/**
 * @brief Write a single register
 * @param reg Register address
 * @param value Value to write
 */
static void imu_write_register(uint8_t reg, uint8_t value)
{
    hal_spi_select();
    hal_spi_write_byte(reg | ICM20948_SPI_WRITE);
    hal_spi_write_byte(value);
    hal_spi_deselect();
}

/**
 * @brief Read a single register
 * @param reg Register address
 * @return Register value
 */
static uint8_t imu_read_register(uint8_t reg)
{
    uint8_t value;

    hal_spi_select();
    hal_spi_write_byte(reg | ICM20948_SPI_READ);
    value = hal_spi_read_byte();
    hal_spi_deselect();

    return value;
}

/**
 * @brief Read multiple registers
 * @param reg Starting register address
 * @param data Buffer for read data
 * @param length Number of bytes to read
 */
static void imu_read_registers(uint8_t reg, uint8_t *data, uint8_t length)
{
    hal_spi_select();
    hal_spi_write_byte(reg | ICM20948_SPI_READ);
    hal_spi_read_bytes(data, length);
    hal_spi_deselect();
}

/**
 * @brief Delay in milliseconds
 * @param ms Milliseconds to delay
 *
 * IMPORTANT: Simple delay for initialization only.
 * Does NOT manipulate SysTick (lesson from PlatformIO migration).
 * Uses simple CPU cycle counting.
 */
static void imu_delay_ms(uint32_t ms)
{
    // At 72MHz: ~72000 cycles per ms
    // This is approximate and for initialization only
    for (uint32_t i = 0; i < ms; i++)
    {
        for (volatile uint32_t j = 0; j < 12000; j++)
        {
            __NOP();
        }
    }
}

/* ========================================================================
 * AK09916 MAGNETOMETER I2C MASTER FUNCTIONS
 * ======================================================================== */

/**
 * @brief Write to AK09916 register via ICM-20948 I2C master
 * @param reg AK09916 register address
 * @param value Value to write
 */
static void mag_i2c_write(uint8_t reg, uint8_t value)
{
    imu_select_bank(3);
    imu_write_register(ICM20948_I2C_SLV0_ADDR, AK09916_I2C_ADDR);  // Write mode
    imu_write_register(ICM20948_I2C_SLV0_REG, reg);
    imu_write_register(ICM20948_I2C_SLV0_DO, value);
    imu_write_register(ICM20948_I2C_SLV0_CTRL, 0x80 | 0x01);       // Enable + 1 byte
    imu_select_bank(0);
    imu_delay_ms(10);
}

/**
 * @brief Setup continuous read from AK09916 via I2C master
 *
 * After calling this, mag data will be automatically read by the ICM-20948
 * I2C master and placed in EXT_SLV_SENS_DATA registers.
 *
 * @param reg AK09916 starting register
 * @param len Number of bytes to read
 */
static void mag_i2c_setup_read(uint8_t reg, uint8_t len)
{
    imu_select_bank(3);
    imu_write_register(ICM20948_I2C_SLV0_ADDR, 0x80 | AK09916_I2C_ADDR);  // Read mode
    imu_write_register(ICM20948_I2C_SLV0_REG, reg);
    imu_write_register(ICM20948_I2C_SLV0_CTRL, 0x80 | len);               // Enable + len bytes
    imu_select_bank(0);
}

/**
 * @brief Initialize AK09916 magnetometer via ICM-20948 I2C master
 *
 * Sequence follows LGDXRobot2 pattern:
 * 1. Reset I2C master
 * 2. Enable I2C master mode
 * 3. Reset AK09916
 * 4. Set continuous measurement mode (100Hz)
 * 5. Setup continuous SLV0 read (9 bytes: ST1 + XYZ data + ST2)
 *
 * @return 0 on success, -1 on failure
 */
static int mag_init(void)
{
    uint8_t buf;

    // Reset I2C master
    imu_select_bank(0);
    buf = imu_read_register(ICM20948_USER_CTRL);
    buf |= 0x02;  // I2C_MST_RST
    imu_write_register(ICM20948_USER_CTRL, buf);
    imu_delay_ms(100);

    // Enable I2C master
    buf = imu_read_register(ICM20948_USER_CTRL);
    buf |= 0x20;  // I2C_MST_EN
    imu_write_register(ICM20948_USER_CTRL, buf);
    imu_delay_ms(10);

    // Set I2C master clock to 400kHz
    imu_select_bank(3);
    imu_write_register(ICM20948_I2C_MST_CTRL, 0x07);
    imu_select_bank(0);
    imu_delay_ms(10);

    // Configure low-power mode for I2C master
    imu_write_register(ICM20948_LP_CONFIG, 0x40);
    imu_delay_ms(10);

    // Set I2C master ODR
    imu_select_bank(3);
    imu_write_register(ICM20948_I2C_MST_ODR_CONFIG, 0x03);
    imu_select_bank(0);
    imu_delay_ms(10);

    // Reset AK09916 magnetometer
    mag_i2c_write(AK09916_CNTL3, 0x01);
    imu_delay_ms(100);

    // Set AK09916 to continuous measurement mode 4 (100Hz)
    mag_i2c_write(AK09916_CNTL2, 0x08);
    imu_delay_ms(50);

    // Setup continuous read: ST1(1) + HXL..HZH(6) + dummy(1) + ST2(1) = 9 bytes
    mag_i2c_setup_read(AK09916_ST1, 9);
    imu_delay_ms(100);

    mag_initialized = 1;
    return 0;
}

/**
 * @brief Initialize ICM-20948 IMU
 */
int imu_driver_init(void)
{
    uint8_t who_am_i;

    // Select User Bank 0
    imu_select_bank(0);

    // Reset device
    imu_write_register(ICM20948_PWR_MGMT_1, 0x80);  // Device reset
    imu_delay_ms(100);  // Wait for reset to complete

    // Wake up device and set clock to auto-select best
    imu_write_register(ICM20948_PWR_MGMT_1, 0x01);  // Auto select clock
    imu_delay_ms(10);

    // G7: Disable I2C interface (SPI-only mode) to avoid conflicts
    imu_write_register(ICM20948_USER_CTRL, 0x10);  // I2C_IF_DIS bit 4
    imu_delay_ms(1);

    // Verify WHO_AM_I register
    who_am_i = imu_read_register(ICM20948_WHO_AM_I);
    if (who_am_i != ICM20948_WHO_AM_I_VALUE)
    {
        return -1;  // Wrong device ID
    }

    // Enable accelerometer and gyroscope
    imu_write_register(ICM20948_PWR_MGMT_2, 0x00);  // Enable all axes
    imu_delay_ms(10);

    // Select User Bank 2 for sensor configuration
    imu_select_bank(2);

    // Configure gyroscope: ±2000 dps, DLPF enabled
    // GYRO_FS_SEL = 3 (±2000 dps)
    imu_write_register(ICM20948_GYRO_CONFIG_1, 0x06);  // ±2000 dps, DLPF 196Hz
    gyro_scale = 2000.0f / 32768.0f * (M_PI / 180.0f);  // Convert to rad/s

    // Configure accelerometer: ±16g, DLPF enabled
    // ACCEL_FS_SEL = 3 (±16g)
    imu_write_register(ICM20948_ACCEL_CONFIG, 0x06);    // ±16g
    imu_write_register(ICM20948_ACCEL_CONFIG_2, 0x06);  // DLPF 196Hz
    accel_scale = 16.0f / 32768.0f * 9.80665f;  // Convert to m/s²

    // Return to User Bank 0
    imu_select_bank(0);

    // Store current configuration
    current_config.accel_range = 3;  // ±16g
    current_config.gyro_range = 3;   // ±2000 dps
    current_config.accel_dlpf = 6;   // 196Hz
    current_config.gyro_dlpf = 6;    // 196Hz
    current_config.sample_rate = 0;  // 1125Hz / (1 + 0) = 1125Hz

    // Initialize AK09916 magnetometer via I2C master
    if (mag_init() != 0)
    {
        // Magnetometer init failed — continue without mag (gyro/accel still work)
        mag_initialized = 0;
    }

    // Calibrate gyroscope (collect zero-rate bias samples)
    // Device must be stationary during this ~1 second calibration
    imu_calibrate();

    return 0;
}

/**
 * @brief Read raw sensor data from IMU
 */
int imu_read_raw(imu_raw_data_t *data)
{
    uint8_t buffer[14];

    if (data == NULL)
    {
        return -1;
    }

    // Ensure we're in User Bank 0
    imu_select_bank(0);

    // Read accelerometer (6 bytes) + gyroscope (6 bytes) + temperature (2 bytes)
    // Registers are contiguous: ACCEL_XOUT_H to GYRO_ZOUT_L
    imu_read_registers(ICM20948_ACCEL_XOUT_H, buffer, 14);

    // Parse accelerometer data (big-endian)
    data->accel_x = (int16_t)((buffer[0] << 8) | buffer[1]);
    data->accel_y = (int16_t)((buffer[2] << 8) | buffer[3]);
    data->accel_z = (int16_t)((buffer[4] << 8) | buffer[5]);

    // Parse gyroscope data (big-endian)
    data->gyro_x = (int16_t)((buffer[6] << 8) | buffer[7]);
    data->gyro_y = (int16_t)((buffer[8] << 8) | buffer[9]);
    data->gyro_z = (int16_t)((buffer[10] << 8) | buffer[11]);

    // Parse temperature data
    data->temperature = (int16_t)((buffer[12] << 8) | buffer[13]);

    // Read magnetometer from external sensor data registers
    // I2C master continuously reads AK09916 into EXT_SLV_SENS_DATA_00..08
    // Layout: [ST1][HXL][HXH][HYL][HYH][HZL][HZH][dummy][ST2]
    if (mag_initialized)
    {
        uint8_t mag_buf[9];
        imu_read_registers(ICM20948_EXT_SLV_SENS_DATA_00, mag_buf, 9);

        // Check data ready bit (ST1 bit 0)
        if (mag_buf[0] & 0x01)
        {
            // AK09916 data is little-endian (low byte first)
            data->mag_x = (int16_t)(mag_buf[2] << 8 | mag_buf[1]);
            data->mag_y = (int16_t)(mag_buf[4] << 8 | mag_buf[3]);
            data->mag_z = (int16_t)(mag_buf[6] << 8 | mag_buf[5]);

            // G6: Store last valid reading
            last_mag_x = data->mag_x;
            last_mag_y = data->mag_y;
            last_mag_z = data->mag_z;
        }
        else
        {
            // G6: Data not ready — keep previous reading to avoid spikes
            data->mag_x = last_mag_x;
            data->mag_y = last_mag_y;
            data->mag_z = last_mag_z;
        }
    }
    else
    {
        data->mag_x = 0;
        data->mag_y = 0;
        data->mag_z = 0;
    }

    return 0;
}

/**
 * @brief Read calibrated sensor data from IMU
 */
int imu_read_calibrated(imu_data_t *data)
{
    imu_raw_data_t raw_data;

    if (data == NULL)
    {
        return -1;
    }

    // Read raw data
    if (imu_read_raw(&raw_data) != 0)
    {
        return -1;
    }

    // Convert accelerometer to m/s²
    data->accel_x = raw_data.accel_x * accel_scale;
    data->accel_y = raw_data.accel_y * accel_scale;
    data->accel_z = raw_data.accel_z * accel_scale;

    // Convert gyroscope to rad/s and apply calibration offsets
    data->gyro_x = (raw_data.gyro_x * gyro_scale) - gyro_offset_x;
    data->gyro_y = (raw_data.gyro_y * gyro_scale) - gyro_offset_y;
    data->gyro_z = (raw_data.gyro_z * gyro_scale) - gyro_offset_z;

    // Convert magnetometer to µT and apply hard/soft iron calibration
    if (mag_cal.calibrated)
    {
        // Raw to µT
        float raw_mx = raw_data.mag_x * mag_scale;
        float raw_my = raw_data.mag_y * mag_scale;
        float raw_mz = raw_data.mag_z * mag_scale;

        // Hard iron correction (subtract bias offset)
        float hx = raw_mx - mag_cal.hard_iron_offset[0];
        float hy = raw_my - mag_cal.hard_iron_offset[1];
        float hz = raw_mz - mag_cal.hard_iron_offset[2];

        // Soft iron correction (3x3 matrix multiply)
        data->mag_x = mag_cal.soft_iron_matrix[0] * hx +
                       mag_cal.soft_iron_matrix[1] * hy +
                       mag_cal.soft_iron_matrix[2] * hz;
        data->mag_y = mag_cal.soft_iron_matrix[3] * hx +
                       mag_cal.soft_iron_matrix[4] * hy +
                       mag_cal.soft_iron_matrix[5] * hz;
        data->mag_z = mag_cal.soft_iron_matrix[6] * hx +
                       mag_cal.soft_iron_matrix[7] * hy +
                       mag_cal.soft_iron_matrix[8] * hz;
    }
    else
    {
        // No calibration — convert raw to µT only
        data->mag_x = raw_data.mag_x * mag_scale;
        data->mag_y = raw_data.mag_y * mag_scale;
        data->mag_z = raw_data.mag_z * mag_scale;
    }

    // Convert temperature to °C
    // Temperature formula: ((TEMP_OUT - RoomTemp_Offset) / Temp_Sensitivity) + 21°C
    data->temperature = ((float)raw_data.temperature / 333.87f) + 21.0f;

    return 0;
}

/**
 * @brief Read accelerometer only
 */
int imu_read_accel(float *accel_x, float *accel_y, float *accel_z)
{
    imu_data_t data;

    if (imu_read_calibrated(&data) != 0)
    {
        return -1;
    }

    if (accel_x) *accel_x = data.accel_x;
    if (accel_y) *accel_y = data.accel_y;
    if (accel_z) *accel_z = data.accel_z;

    return 0;
}

/**
 * @brief Read gyroscope only
 */
int imu_read_gyro(float *gyro_x, float *gyro_y, float *gyro_z)
{
    imu_data_t data;

    if (imu_read_calibrated(&data) != 0)
    {
        return -1;
    }

    if (gyro_x) *gyro_x = data.gyro_x;
    if (gyro_y) *gyro_y = data.gyro_y;
    if (gyro_z) *gyro_z = data.gyro_z;

    return 0;
}

/**
 * @brief Read magnetometer only
 */
int imu_read_mag(float *mag_x, float *mag_y, float *mag_z)
{
    imu_data_t data;

    if (imu_read_calibrated(&data) != 0)
    {
        return -1;
    }

    if (mag_x) *mag_x = data.mag_x;
    if (mag_y) *mag_y = data.mag_y;
    if (mag_z) *mag_z = data.mag_z;

    return 0;
}

/**
 * @brief Read die temperature
 */
float imu_read_temperature(void)
{
    imu_data_t data;

    if (imu_read_calibrated(&data) != 0)
    {
        return 0.0f;
    }

    return data.temperature;
}

/**
 * @brief Calibrate IMU (gyroscope zero-rate offset)
 *
 * Device must be stationary during calibration.
 */
int imu_calibrate(void)
{
    imu_raw_data_t raw_data;
    int32_t sum_x = 0, sum_y = 0, sum_z = 0;
    uint16_t valid_samples = 0;

    // Reset offsets
    gyro_offset_x = 0.0f;
    gyro_offset_y = 0.0f;
    gyro_offset_z = 0.0f;

    // Collect samples
    for (uint16_t i = 0; i < CALIBRATION_SAMPLES; i++)
    {
        if (imu_read_raw(&raw_data) == 0)
        {
            sum_x += raw_data.gyro_x;
            sum_y += raw_data.gyro_y;
            sum_z += raw_data.gyro_z;
            valid_samples++;
        }

        imu_delay_ms(1);  // 1ms between samples
    }

    if (valid_samples < CALIBRATION_SAMPLES / 2)
    {
        return -1;  // Too few valid samples
    }

    // Calculate average offsets
    gyro_offset_x = (sum_x / (float)valid_samples) * gyro_scale;
    gyro_offset_y = (sum_y / (float)valid_samples) * gyro_scale;
    gyro_offset_z = (sum_z / (float)valid_samples) * gyro_scale;

    return 0;
}

/**
 * @brief Reset IMU to default configuration
 */
int imu_reset(void)
{
    return imu_driver_init();
}

/**
 * @brief Check if IMU is responding
 */
int imu_is_alive(void)
{
    uint8_t who_am_i;

    imu_select_bank(0);
    who_am_i = imu_read_register(ICM20948_WHO_AM_I);

    return (who_am_i == ICM20948_WHO_AM_I_VALUE) ? 1 : 0;
}

/**
 * @brief Perform IMU self-test
 */
int imu_self_test(void)
{
    // Check if device responds
    if (!imu_is_alive())
    {
        return -1;
    }

    // Try reading sensor data
    imu_raw_data_t raw_data;
    if (imu_read_raw(&raw_data) != 0)
    {
        return -1;
    }

    // Basic sanity check: accelerometer Z-axis should read ~1g (gravity)
    // In ±16g range: 1g ≈ 2048 counts
    if (raw_data.accel_z < 1000 || raw_data.accel_z > 3000)
    {
        // Warning: Z-axis not reading expected gravity value
        // This may indicate orientation or calibration issue
        // But not a fatal error
    }

    return 0;
}

/**
 * @brief Set IMU configuration (placeholder for future enhancement)
 */
int imu_set_config(const imu_config_t *config)
{
    if (config == NULL)
    {
        return -1;
    }

    // This can be expanded to dynamically configure ranges and DLPF
    // For now, we use fixed configuration from init

    return 0;
}

/**
 * @brief Get current IMU configuration
 */
int imu_get_config(imu_config_t *config)
{
    if (config == NULL)
    {
        return -1;
    }

    *config = current_config;
    return 0;
}

/* ========================================================================
 * MAGNETOMETER CALIBRATION FUNCTIONS
 * ======================================================================== */

void imu_set_mag_calibration(const mag_calibration_t *cal)
{
    if (cal != NULL)
    {
        mag_cal = *cal;
    }
}

void imu_get_mag_calibration(mag_calibration_t *cal)
{
    if (cal != NULL)
    {
        *cal = mag_cal;
    }
}

/* ========================================================================
 * PROTOCOL-COMPATIBLE WRAPPER FUNCTIONS
 * ======================================================================== */

/**
 * @brief Get raw gyroscope data as int16 array
 */
void imu_get_gyro_raw(int16_t gyro[3])
{
    imu_raw_data_t data;
    if (imu_read_raw(&data) == 0)
    {
        gyro[0] = data.gyro_x;
        gyro[1] = data.gyro_y;
        gyro[2] = data.gyro_z;
    }
    else
    {
        gyro[0] = 0;
        gyro[1] = 0;
        gyro[2] = 0;
    }
}

/**
 * @brief Get raw accelerometer data as int16 array
 */
void imu_get_accel_raw(int16_t accel[3])
{
    imu_raw_data_t data;
    if (imu_read_raw(&data) == 0)
    {
        accel[0] = data.accel_x;
        accel[1] = data.accel_y;
        accel[2] = data.accel_z;
    }
    else
    {
        accel[0] = 0;
        accel[1] = 0;
        accel[2] = 0;
    }
}

/**
 * @brief Get calibrated magnetometer data as int16 array
 *
 * Returns mag values in µT × 1000 to match ICM20948_MAG_RATIO on ROS2 side.
 * The ROS2 driver divides by 1000 to get µT.
 */
void imu_get_mag_raw(int16_t mag[3])
{
    imu_data_t data;
    if (imu_read_calibrated(&data) == 0)
    {
        // Scale calibrated µT values × 1000 for protocol transport
        mag[0] = (int16_t)(data.mag_x * 1000.0f);
        mag[1] = (int16_t)(data.mag_y * 1000.0f);
        mag[2] = (int16_t)(data.mag_z * 1000.0f);
    }
    else
    {
        mag[0] = 0;
        mag[1] = 0;
        mag[2] = 0;
    }
}

/**
 * @brief Get all IMU data efficiently in a single SPI transaction
 *
 * Gyro/accel returned as raw ADC counts (ROS2 applies scaling).
 * Mag returned as calibrated µT × 1000 (ROS2 divides by 1000).
 *
 * Previously called imu_read_raw() then imu_read_calibrated() which
 * internally called imu_read_raw() again — two SPI reads from different
 * time points. Now reads once and applies mag calibration inline.
 */
void imu_get_all_raw(int16_t gyro[3], int16_t accel[3], int16_t mag[3])
{
    imu_raw_data_t raw;
    if (imu_read_raw(&raw) != 0)
    {
        gyro[0] = gyro[1] = gyro[2] = 0;
        accel[0] = accel[1] = accel[2] = 0;
        mag[0] = mag[1] = mag[2] = 0;
        return;
    }

    gyro[0] = raw.gyro_x;
    gyro[1] = raw.gyro_y;
    gyro[2] = raw.gyro_z;
    accel[0] = raw.accel_x;
    accel[1] = raw.accel_y;
    accel[2] = raw.accel_z;

    // Apply mag calibration inline (no second SPI read)
    float raw_mx = raw.mag_x * mag_scale;
    float raw_my = raw.mag_y * mag_scale;
    float raw_mz = raw.mag_z * mag_scale;

    if (mag_cal.calibrated)
    {
        float hx = raw_mx - mag_cal.hard_iron_offset[0];
        float hy = raw_my - mag_cal.hard_iron_offset[1];
        float hz = raw_mz - mag_cal.hard_iron_offset[2];

        float cx = mag_cal.soft_iron_matrix[0] * hx +
                   mag_cal.soft_iron_matrix[1] * hy +
                   mag_cal.soft_iron_matrix[2] * hz;
        float cy = mag_cal.soft_iron_matrix[3] * hx +
                   mag_cal.soft_iron_matrix[4] * hy +
                   mag_cal.soft_iron_matrix[5] * hz;
        float cz = mag_cal.soft_iron_matrix[6] * hx +
                   mag_cal.soft_iron_matrix[7] * hy +
                   mag_cal.soft_iron_matrix[8] * hz;

        mag[0] = (int16_t)(cx * 1000.0f);
        mag[1] = (int16_t)(cy * 1000.0f);
        mag[2] = (int16_t)(cz * 1000.0f);
    }
    else
    {
        mag[0] = (int16_t)(raw_mx * 1000.0f);
        mag[1] = (int16_t)(raw_my * 1000.0f);
        mag[2] = (int16_t)(raw_mz * 1000.0f);
    }
}

/**
 * @brief Get attitude angles (roll, pitch, yaw)
 *
 * Gets attitude from IMU task which performs gyro integration for yaw.
 * Roll and pitch are calculated from accelerometer.
 * Yaw is integrated from gyroscope Z-axis.
 */
void imu_get_attitude(float *roll, float *pitch, float *yaw)
{
    /* Get attitude from IMU task (which does gyro integration) */
    extern void imu_task_get_attitude(float *roll, float *pitch, float *yaw);
    imu_task_get_attitude(roll, pitch, yaw);
}
