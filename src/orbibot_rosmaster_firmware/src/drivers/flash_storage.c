/**
 * @file flash_storage.c
 * @brief Flash Persistence Implementation for STM32F103RCT6
 * @author Jewel Nath
 * @date 2025-12-01
 *
 * STM32F103 flash specifics:
 * - Page erase: 2KB at a time (FLASH_ErasePage)
 * - Write: half-word (16-bit) at a time (FLASH_ProgramHalfWord)
 * - Must unlock before write, lock after
 * - Data size must be even (padded if needed)
 */

#include "flash_storage.h"
#include "task_control.h"
#include "imu_driver.h"
#include "orbibot_config.h"
#include "stm32f10x_flash.h"
#include <string.h>

static flash_data_t flash_cache;
static uint8_t flash_loaded = 0;

/**
 * @brief Calculate additive checksum over data bytes
 *
 * Uses additive sum (same as protocol.c) rather than XOR.
 * XOR misses even-count bit errors and byte transpositions;
 * additive sum catches more common corruption patterns.
 */
static uint8_t calculate_checksum(const flash_data_t *data)
{
    const uint8_t *bytes = (const uint8_t *)data;
    // Checksum covers everything except the checksum byte itself (last byte)
    uint16_t sum = 0;
    for (size_t i = 0; i < sizeof(flash_data_t) - 1; i++)
    {
        sum += bytes[i];
    }
    return (uint8_t)(sum & 0xFF);
}

int flash_storage_load(void)
{
    // Read flash page into cache
    const uint8_t *flash_ptr = (const uint8_t *)FLASH_STORAGE_PAGE_ADDR;
    memcpy(&flash_cache, flash_ptr, sizeof(flash_data_t));

    flash_loaded = 1;

    // Validate magic and checksum
    if (flash_cache.magic != FLASH_STORAGE_MAGIC)
    {
        DEBUG_INFO("Flash: no stored data (magic=0x%02X)\n", flash_cache.magic);
        return -1;
    }

    uint8_t expected = calculate_checksum(&flash_cache);
    if (flash_cache.checksum != expected)
    {
        DEBUG_INFO("Flash: checksum mismatch (got 0x%02X, expected 0x%02X)\n",
                   flash_cache.checksum, expected);
        return -1;
    }

    // Apply single PID gains
    control_set_motor_pid(
        flash_cache.pid_gains.kp,
        flash_cache.pid_gains.ki,
        flash_cache.pid_gains.kd
    );

    // Apply mag calibration
    if (flash_cache.mag_cal.calibrated)
    {
        imu_set_mag_calibration(&flash_cache.mag_cal);
    }

    DEBUG_INFO("Flash: loaded PID + mag calibration\n");
    return 0;
}

int flash_storage_save(void)
{
    // Collect current PID gains (single PID)
    const pid_gains_t *gains = control_get_motor_pid();
    flash_cache.pid_gains = *gains;

    // Collect current mag calibration
    imu_get_mag_calibration(&flash_cache.mag_cal);

    // Set magic and compute checksum
    flash_cache.magic = FLASH_STORAGE_MAGIC;
    flash_cache.checksum = calculate_checksum(&flash_cache);

    // Write to flash: unlock → erase page → program half-words → lock
    FLASH_Unlock();

    FLASH_Status status = FLASH_ErasePage(FLASH_STORAGE_PAGE_ADDR);
    if (status != FLASH_COMPLETE)
    {
        FLASH_Lock();
        DEBUG_ERROR("Flash: page erase failed (status=%d)\n", status);
        return -1;
    }

    // Write data as half-words (16-bit aligned)
    const uint16_t *src = (const uint16_t *)&flash_cache;
    uint32_t addr = FLASH_STORAGE_PAGE_ADDR;
    // Round up to even number of bytes for half-word writes
    size_t half_words = (sizeof(flash_data_t) + 1) / 2;

    for (size_t i = 0; i < half_words; i++)
    {
        status = FLASH_ProgramHalfWord(addr, src[i]);
        if (status != FLASH_COMPLETE)
        {
            FLASH_Lock();
            DEBUG_ERROR("Flash: write failed at 0x%08lX (status=%d)\n", addr, status);
            return -1;
        }
        addr += 2;
    }

    FLASH_Lock();

    DEBUG_INFO("Flash: saved PID + mag calibration (%u bytes)\n",
               (unsigned)sizeof(flash_data_t));
    return 0;
}

int flash_storage_is_valid(void)
{
    if (!flash_loaded)
    {
        const uint8_t *flash_ptr = (const uint8_t *)FLASH_STORAGE_PAGE_ADDR;
        memcpy(&flash_cache, flash_ptr, sizeof(flash_data_t));
        flash_loaded = 1;
    }

    if (flash_cache.magic != FLASH_STORAGE_MAGIC)
        return 0;

    return (flash_cache.checksum == calculate_checksum(&flash_cache)) ? 1 : 0;
}
