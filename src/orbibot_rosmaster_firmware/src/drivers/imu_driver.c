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
#include "robot_error.h"
#include "task_imu.h"
#include "hal_spi.h"
#include "stm32f10x.h"
#include "orbibot_config.h"
#include <math.h>

/* DWT (Data Watchpoint and Trace) for cycle-accurate delay.
 * Not all CMSIS versions define DWT; provide minimal definitions when missing. */
#ifndef DWT
#define DWT_BASE                (0xE0001000UL)
#define DWT_CTRL_CYCCNTENA_Pos  (0U)
#define DWT_CTRL_CYCCNTENA_Msk  (1UL << DWT_CTRL_CYCCNTENA_Pos)
typedef struct {
    volatile uint32_t CTRL;
    volatile uint32_t CYCCNT;
    volatile uint32_t CPICNT;
    volatile uint32_t EXCCNT;
    volatile uint32_t SLEEPCNT;
    volatile uint32_t LSUCNT;
    volatile uint32_t FOLDCNT;
    volatile uint32_t PCSR;
} DWT_Type;
#define DWT ((DWT_Type *)DWT_BASE)
#endif

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

// Calibration offsets (computed at startup from 1000 stationary samples)
static float gyro_offset_x = 0.0f;
static float gyro_offset_y = 0.0f;
static float gyro_offset_z = 0.0f;
static float accel_offset_x = 0.0f;  // X bias (should be ~0 when level)
static float accel_offset_y = 0.0f;  // Y bias (should be ~0 when level)
// Note: Z is NOT offset-corrected — Madgwick needs gravity vector intact

// Sensor noise variance (computed once at startup from stationary samples)
// Units: accel in (m/s²)², gyro in (rad/s)² — ready for ROS2 Imu covariance
static float accel_variance[3] = {0.01f, 0.01f, 0.01f};   // X, Y, Z
static float gyro_variance[3] = {0.0025f, 0.0025f, 0.0025f}; // X, Y, Z

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
 * @return Register value, or 0xFF on SPI bus timeout.
 *
 * Note: hal_spi_read_byte() returns 0xFF on timeout. Callers that perform
 * identity checks (e.g. WHO_AM_I == 0xEA) naturally reject 0xFF. For bulk
 * sensor reads where 0xFF is a plausible data value, a persistent SPI fault
 * would be detected at the next IMU init (watchdog reset) or via imu_driver_init()
 * re-check. No additional per-call validation is added to avoid overhead at 50Hz.
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
 * Uses DWT cycle counter for hardware-accurate timing independent of
 * compiler optimization level. Falls back to SysTick if DWT is unavailable.
 */
static void imu_delay_ms(uint32_t ms)
{
    /* DWT CYCCNT is available on Cortex-M3 (STM32F103) when enabled. */
    if (!(CoreDebug->DEMCR & CoreDebug_DEMCR_TRCENA_Msk))
    {
        CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
        DWT->CYCCNT = 0;
        DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    }

    uint32_t cycles_per_ms = SystemCoreClock / 1000;
    for (uint32_t i = 0; i < ms; i++)
    {
        uint32_t start = DWT->CYCCNT;
        while ((DWT->CYCCNT - start) < cycles_per_ms)
            ;
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

/* AK09916 WHO_AM_I register value (read from WIA2 = 0x01) */
#define AK09916_WIA2_VALUE          0x09

/**
 * @brief Initialize AK09916 magnetometer via ICM-20948 I2C master
 *
 * Sequence follows LGDXRobot2 pattern:
 * 1. Reset I2C master
 * 2. Enable I2C master mode
 * 3. Verify AK09916 WHO_AM_I (WIA2 should read 0x09)
 * 4. Reset AK09916
 * 5. Set continuous measurement mode (100Hz)
 * 6. Setup continuous SLV0 read (9 bytes: ST1 + XYZ data + ST2)
 *
 * @return 0 on success, -1 on failure (WHO_AM_I mismatch => chip absent/dead).
 *         Caller leaves attitude filter in gyro-only mode — mag fields remain
 *         zero in all subsequent reports instead of feeding garbage into yaw.
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

    // Verify AK09916 WHO_AM_I (WIA2 at reg 0x01 should read 0x09).
    // Uses SLV0 for a one-byte read; reconfigured to 9-byte continuous
    // read once WHO_AM_I passes.
    mag_i2c_setup_read(AK09916_WIA2, 1);
    imu_delay_ms(20);  // allow one I2C master cycle (ODR=100Hz)
    uint8_t wia2 = imu_read_register(ICM20948_EXT_SLV_SENS_DATA_00);
    if (wia2 != AK09916_WIA2_VALUE)
    {
        BOOT_PRINTF("[IMU]   AK09916 WHO_AM_I = 0x%02X (expected 0x09) "
                    "— magnetometer NOT initialized\r\n", wia2);
        mag_initialized = 0;
        return -1;
    }
    BOOT_PRINTF("[IMU]   AK09916 WHO_AM_I = 0x09 OK\r\n");

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

/* Known WHO_AM_I values for chips that may be fitted on the ROSMaster V3.0 */
#define MPU9250_WHO_AM_I_VALUE      0x71
#define MPU6500_WHO_AM_I_VALUE      0x70

/**
 * @brief Initialize ICM-20948 IMU
 *
 * On failure the function prints the actual WHO_AM_I byte so the correct chip
 * can be identified. Known alternates on the ROSMaster V3.0 board:
 *   0xEA  ICM-20948  (expected)
 *   0x71  MPU-9250   (some board revisions)
 *   0x70  MPU-6500
 *   0xFF  SPI not responding (wiring / power issue)
 *   0x00  MISO stuck low
 */
robot_err_t imu_driver_init(void)
{
    uint8_t who_am_i;

    BOOT_PRINTF("\r\n[IMU] imu_driver_init() starting...\r\n");
    BOOT_PRINTF("[IMU] SPI2: PB12=CS PB13=SCK PB14=MISO PB15=MOSI\r\n");
    BOOT_PRINTF("[IMU] Step 1: select bank 0\r\n");

    imu_select_bank(0);

    BOOT_PRINTF("[IMU] Step 2: software reset (PWR_MGMT_1 = 0x80)\r\n");
    imu_write_register(ICM20948_PWR_MGMT_1, 0x80);
    imu_delay_ms(100);

    /* Verify reset completed — PWR_MGMT_1 should read 0x41 (sleep bit set,
     * clk_sel = 1 after internal reset sequence on ICM-20948). */
#if ENABLE_BOOT_MESSAGES
    {
        uint8_t pwr_mgmt_1_after_reset = imu_read_register(ICM20948_PWR_MGMT_1);
        BOOT_PRINTF("[IMU] Step 2b: PWR_MGMT_1 after reset = 0x%02X (expect 0x41)\r\n",
                    pwr_mgmt_1_after_reset);
    }
#endif

    BOOT_PRINTF("[IMU] Step 3: wake + auto-clock (PWR_MGMT_1 = 0x01)\r\n");
    imu_write_register(ICM20948_PWR_MGMT_1, 0x01);
    imu_delay_ms(10);

    BOOT_PRINTF("[IMU] Step 4: I2C_IF_DIS — force SPI-only mode (USER_CTRL = 0x10)\r\n");
    imu_write_register(ICM20948_USER_CTRL, 0x10);
    imu_delay_ms(1);

    BOOT_PRINTF("[IMU] Step 5: reading WHO_AM_I register (0x00)...\r\n");
    who_am_i = imu_read_register(ICM20948_WHO_AM_I);
    BOOT_PRINTF("[IMU] WHO_AM_I = 0x%02X", who_am_i);

    if (who_am_i == ICM20948_WHO_AM_I_VALUE)
    {
        BOOT_PRINTF(" -> ICM-20948 detected OK\r\n");
    }
    else if (who_am_i == MPU9250_WHO_AM_I_VALUE)
    {
        BOOT_PRINTF(" -> MPU-9250 detected! Firmware expects ICM-20948 (0xEA).\r\n");
        BOOT_PRINTF("[IMU] ERROR: Wrong IMU chip. Check board revision.\r\n");
        return ROBOT_ERR_HW;
    }
    else if (who_am_i == MPU6500_WHO_AM_I_VALUE)
    {
        BOOT_PRINTF(" -> MPU-6500 detected! Firmware expects ICM-20948 (0xEA).\r\n");
        BOOT_PRINTF("[IMU] ERROR: Wrong IMU chip. Check board revision.\r\n");
        return ROBOT_ERR_HW;
    }
    else if (who_am_i == 0xFF)
    {
        BOOT_PRINTF(" -> SPI MISO stuck HIGH (0xFF). Check:\r\n");
        BOOT_PRINTF("[IMU]   - PB14 (MISO) wiring\r\n");
        BOOT_PRINTF("[IMU]   - IMU VDD/VDDIO 3.3V power supply\r\n");
        BOOT_PRINTF("[IMU]   - SPI2 clock/mode (CPOL=0, CPHA=0, 4.5MHz)\r\n");
        return ROBOT_ERR_HW;
    }
    else if (who_am_i == 0x00)
    {
        BOOT_PRINTF(" -> SPI MISO stuck LOW (0x00). Check:\r\n");
        BOOT_PRINTF("[IMU]   - PB14 (MISO) connection to IMU SDO pin\r\n");
        BOOT_PRINTF("[IMU]   - IMU chip soldering\r\n");
        return ROBOT_ERR_HW;
    }
    else
    {
        BOOT_PRINTF(" -> UNKNOWN chip (expected 0xEA for ICM-20948).\r\n");
        BOOT_PRINTF("[IMU]   Possible causes:\r\n");
        BOOT_PRINTF("[IMU]   - SPI timing issue (try lower clock prescaler)\r\n");
        BOOT_PRINTF("[IMU]   - Wrong register bank selected after reset\r\n");
        BOOT_PRINTF("[IMU]   - CS (PB12) not asserting low properly\r\n");
        return ROBOT_ERR_HW;
    }

    BOOT_PRINTF("[IMU] Step 6: enable accel + gyro all axes (PWR_MGMT_2 = 0x00)\r\n");
    imu_write_register(ICM20948_PWR_MGMT_2, 0x00);
    imu_delay_ms(10);

    BOOT_PRINTF("[IMU] Step 7: configure gyro/accel in bank 2\r\n");
    imu_select_bank(2);

    /* Gyroscope: ±500 dps, DLPF 5.7Hz
     * GYRO_CONFIG_1 [5:3]=110 (DLPFCFG=6), [2:1]=01 (FS_SEL=±500dps), [0]=1 (FCHOICE on)
     * = 0b00110011 = 0x33
     * DLPF=6 → 5.7Hz bandwidth: attenuates motor vibration (333 RPM = 5.55Hz fundamental).
     * Range chosen so physical×1000 fits int16: max ±8727 milli-rad/s < 32767. */
    imu_write_register(ICM20948_GYRO_CONFIG_1, 0x33);
    gyro_scale = 500.0f / 32768.0f * (M_PI / 180.0f);
    BOOT_PRINTF("[IMU]   GYRO_CONFIG_1 = 0x33 (+/-500dps, DLPF 5.7Hz — motor vibration filter)\r\n");

    /* Accelerometer: ±2g, DLPF 5.7Hz
     * ACCEL_CONFIG [5:3]=110 (DLPFCFG=6), [2:1]=00 (FS_SEL=±2g), [0]=1 (FCHOICE on)
     * = 0b00110001 = 0x31
     * ACCEL_CONFIG_2: DLPFCFG=6 → 5.7Hz bandwidth (matches gyro filter).
     * Range chosen so physical×1000 fits int16: max ±19613 milli-m/s² < 32767. */
    imu_write_register(ICM20948_ACCEL_CONFIG, 0x31);
    imu_write_register(ICM20948_ACCEL_CONFIG_2, 0x06);

    /* FW-BUG-2 fix: empirical scale derived from hardware measurement.
     * ACCEL_CONFIG register readback confirmed 0x31 (±2g, FS_SEL=0), but chip
     * outputs 1.566× gravity: measured |accel| = 15.35 m/s² at rest (expected 9.81).
     * Back-calculated: 1g = 25644 raw ADC counts instead of the nominal 16384.
     * This is a persistent hardware characteristic of this ICM-20948 unit.
     * Nominal formula (wrong for this chip): 2.0f / 32768.0f * 9.80665f = 0.000599
     * Empirical formula (correct):           9.80665f / 25644.0f         = 0.000382 */
    accel_scale = 9.80665f / 25644.0f;
    BOOT_PRINTF("[IMU]   ACCEL_CONFIG = 0x31 (+/-2g), ACCEL_CONFIG_2 = 0x06 (DLPF 5.7Hz)\r\n");
    BOOT_PRINTF("[IMU]   accel_scale = 9.80665/25644 (empirical, FW-BUG-2 fix)\r\n");

    imu_select_bank(0);

    /* Sanity-read one accel sample to confirm data is flowing */
#if ENABLE_BOOT_MESSAGES
    {
        uint8_t sane_buf[6];
        imu_read_registers(ICM20948_ACCEL_XOUT_H, sane_buf, 6);
        int16_t ax = (int16_t)((sane_buf[0] << 8) | sane_buf[1]);
        int16_t ay = (int16_t)((sane_buf[2] << 8) | sane_buf[3]);
        int16_t az = (int16_t)((sane_buf[4] << 8) | sane_buf[5]);
        BOOT_PRINTF("[IMU] Step 7b: first accel sample: ax=%d ay=%d az=%d (raw ADC)\r\n",
                    (int)ax, (int)ay, (int)az);
        BOOT_PRINTF("[IMU]   (1g at +/-2g = ~16384 counts; Z should be ~16384 if flat)\r\n");
        if (ax == 0 && ay == 0 && az == 0)
        {
            BOOT_PRINTF("[IMU]   WARNING: all zeros after config — possible SPI MISO issue\r\n");
        }
    }
#endif

    BOOT_PRINTF("[IMU] Step 8: initializing AK09916 magnetometer...\r\n");
    if (mag_init() != 0)
    {
        mag_initialized = 0;
        BOOT_PRINTF("[IMU]   mag_init() FAILED — continuing without magnetometer\r\n");
    }
    else
    {
        BOOT_PRINTF("[IMU]   mag_init() OK\r\n");
    }

    BOOT_PRINTF("[IMU] Step 9: gyro+accel calibration (1000 samples, ~1s, keep robot still & level)...\r\n");
    imu_calibrate();
    BOOT_PRINTF("[IMU]   gyro+accel calibration done\r\n");

    BOOT_PRINTF("[IMU] imu_driver_init() SUCCESS\r\n\r\n");
    return ROBOT_OK;
}

/**
 * @brief Read raw sensor data from IMU
 */
robot_err_t imu_read_raw(imu_raw_data_t *data)
{
    uint8_t buffer[14];

    if (data == NULL)
    {
        return ROBOT_ERR_PARAM;
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

    return ROBOT_OK;
}

robot_err_t imu_read_both(imu_raw_data_t *raw, imu_data_t *cal)
{
    imu_raw_data_t raw_data;
    if (imu_read_raw(&raw_data) != ROBOT_OK)
        return ROBOT_ERR_HW;

    if (raw)
        *raw = raw_data;

    if (cal)
    {
        cal->accel_x = (raw_data.accel_x * accel_scale) - accel_offset_x;
        cal->accel_y = (raw_data.accel_y * accel_scale) - accel_offset_y;
        cal->accel_z = raw_data.accel_z * accel_scale;
        cal->gyro_x = (raw_data.gyro_x * gyro_scale) - gyro_offset_x;
        cal->gyro_y = (raw_data.gyro_y * gyro_scale) - gyro_offset_y;
        cal->gyro_z = (raw_data.gyro_z * gyro_scale) - gyro_offset_z;

        if (mag_cal.calibrated)
        {
            float raw_mx = raw_data.mag_x * mag_scale;
            float raw_my = raw_data.mag_y * mag_scale;
            float raw_mz = raw_data.mag_z * mag_scale;
            float hx = raw_mx - mag_cal.hard_iron_offset[0];
            float hy = raw_my - mag_cal.hard_iron_offset[1];
            float hz = raw_mz - mag_cal.hard_iron_offset[2];
            cal->mag_x = mag_cal.soft_iron_matrix[0] * hx + mag_cal.soft_iron_matrix[1] * hy + mag_cal.soft_iron_matrix[2] * hz;
            cal->mag_y = mag_cal.soft_iron_matrix[3] * hx + mag_cal.soft_iron_matrix[4] * hy + mag_cal.soft_iron_matrix[5] * hz;
            cal->mag_z = mag_cal.soft_iron_matrix[6] * hx + mag_cal.soft_iron_matrix[7] * hy + mag_cal.soft_iron_matrix[8] * hz;
        }
        else
        {
            cal->mag_x = raw_data.mag_x * mag_scale;
            cal->mag_y = raw_data.mag_y * mag_scale;
            cal->mag_z = raw_data.mag_z * mag_scale;
        }
        cal->temperature = ((float)raw_data.temperature / 333.87f) + 21.0f;
    }
    return ROBOT_OK;
}

/**
 * @brief Calibrate IMU (gyroscope + accelerometer zero-rate offsets)
 *
 * Device must be stationary on a level surface during calibration.
 * Computes gyro X/Y/Z offsets and accel X/Y offsets from 1000 samples.
 * Accel Z is NOT offset-corrected — Madgwick needs the gravity vector.
 *
 * Inspired by lgdxrobot2 firmware which calibrates both gyro and accel
 * at startup (imu.c:228-271), including gravity removal on Z axis.
 * We skip Z removal since Madgwick's remove_gravity_vector is false.
 */
int imu_calibrate(void)
{
    imu_raw_data_t raw_data;
    uint16_t valid_samples = 0;

    // Reset all offsets
    gyro_offset_x = 0.0f;
    gyro_offset_y = 0.0f;
    gyro_offset_z = 0.0f;
    accel_offset_x = 0.0f;
    accel_offset_y = 0.0f;

    // Welford's online algorithm accumulators for mean + variance in single pass.
    // Avoids storing 1000 samples in RAM (would need 24KB for 6 axes × float).
    // Reference: Welford (1962), Knuth TAOCP Vol 2, §4.2.2
    float mean_ax = 0, mean_ay = 0, mean_az = 0;
    float mean_gx = 0, mean_gy = 0, mean_gz = 0;
    float m2_ax = 0, m2_ay = 0, m2_az = 0;
    float m2_gx = 0, m2_gy = 0, m2_gz = 0;

    // Collect samples (robot must be stationary and level)
    for (uint16_t i = 0; i < CALIBRATION_SAMPLES; i++)
    {
        if (imu_read_raw(&raw_data) == 0)
        {
            valid_samples++;
            float n = (float)valid_samples;

            // Convert to physical units for variance computation
            float ax = raw_data.accel_x * accel_scale;
            float ay = raw_data.accel_y * accel_scale;
            float az = raw_data.accel_z * accel_scale;
            float gx = raw_data.gyro_x * gyro_scale;
            float gy = raw_data.gyro_y * gyro_scale;
            float gz = raw_data.gyro_z * gyro_scale;

            // Welford update: delta = x - old_mean; mean += delta/n; m2 += delta*(x - new_mean)
            float d;
            d = ax - mean_ax; mean_ax += d / n; m2_ax += d * (ax - mean_ax);
            d = ay - mean_ay; mean_ay += d / n; m2_ay += d * (ay - mean_ay);
            d = az - mean_az; mean_az += d / n; m2_az += d * (az - mean_az);
            d = gx - mean_gx; mean_gx += d / n; m2_gx += d * (gx - mean_gx);
            d = gy - mean_gy; mean_gy += d / n; m2_gy += d * (gy - mean_gy);
            d = gz - mean_gz; mean_gz += d / n; m2_gz += d * (gz - mean_gz);
        }

        imu_delay_ms(1);  // 1ms between samples
    }

    if (valid_samples < CALIBRATION_SAMPLES / 2)
    {
        return -1;  // Too few valid samples
    }

    // ---- Offsets (mean of stationary readings) ----
    // Gyro: all 3 axes (expected 0 rad/s when stationary)
    gyro_offset_x = mean_gx;
    gyro_offset_y = mean_gy;
    gyro_offset_z = mean_gz;

    // Accel: X/Y only (Z has gravity, don't offset it)
    accel_offset_x = mean_ax;
    accel_offset_y = mean_ay;

    // ---- Variance (sensor noise, for ROS2 Imu covariance) ----
    // variance = m2 / (n - 1) for sample variance
    float n_minus_1 = (float)(valid_samples - 1);
    accel_variance[0] = m2_ax / n_minus_1;
    accel_variance[1] = m2_ay / n_minus_1;
    accel_variance[2] = m2_az / n_minus_1;
    gyro_variance[0] = m2_gx / n_minus_1;
    gyro_variance[1] = m2_gy / n_minus_1;
    gyro_variance[2] = m2_gz / n_minus_1;

    BOOT_PRINTF("[IMU]   accel offsets: X=%.4f Y=%.4f m/s2\r\n",
                accel_offset_x, accel_offset_y);
    BOOT_PRINTF("[IMU]   accel variance: X=%.6f Y=%.6f Z=%.6f (m/s2)^2\r\n",
                accel_variance[0], accel_variance[1], accel_variance[2]);
    BOOT_PRINTF("[IMU]   gyro variance:  X=%.6f Y=%.6f Z=%.6f (rad/s)^2\r\n",
                gyro_variance[0], gyro_variance[1], gyro_variance[2]);

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

void imu_get_noise_variance(float accel_var[3], float gyro_var[3])
{
    if (accel_var)
    {
        accel_var[0] = accel_variance[0];
        accel_var[1] = accel_variance[1];
        accel_var[2] = accel_variance[2];
    }
    if (gyro_var)
    {
        gyro_var[0] = gyro_variance[0];
        gyro_var[1] = gyro_variance[1];
        gyro_var[2] = gyro_variance[2];
    }
}

/* ========================================================================
 * ATTITUDE ACCESSOR (simple forwarder to task_imu cache)
 * ======================================================================== */

void imu_get_attitude(float *roll, float *pitch, float *yaw)
{
    imu_task_get_attitude(roll, pitch, yaw);
}
