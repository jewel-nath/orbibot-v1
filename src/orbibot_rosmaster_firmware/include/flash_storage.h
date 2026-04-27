/**
 * @file flash_storage.h
 * @brief Flash Persistence for PID and Magnetometer Calibration
 * @author Jewel Nath
 * @date 2025-12-01
 *
 * Stores configuration data in STM32F103RCT6 internal flash.
 * Uses last 2KB page at 0x0803F800 (page 127 of 128 × 2KB).
 *
 * Data survives power cycles. Written on explicit save command.
 * Read once at startup, cached in RAM.
 */

#ifndef FLASH_STORAGE_H
#define FLASH_STORAGE_H

#include <stdint.h>
#include "pid_controller.h"
#include "imu_driver.h"

// STM32F103RCT6: 256KB flash, 2KB pages. Use last page.
#define FLASH_STORAGE_PAGE_ADDR     0x0803F800U
#define FLASH_STORAGE_MAGIC         0xA5

/**
 * @brief Flash storage data structure
 *
 * Packed to ensure consistent memory layout for flash read/write.
 * Total size must be < 2KB (2048 bytes).
 */
#pragma pack(push, 1)
typedef struct {
    uint8_t magic;                                  // FLASH_STORAGE_MAGIC if valid

    // Single PID gains (3 floats)
    pid_gains_t pid_gains;                          // 12 bytes

    uint8_t reserved[36];                           // Reserved for future use (was multi-level PID)

    // Magnetometer calibration
    mag_calibration_t mag_cal;                      // 3+9 floats + 1 byte = 49 bytes

    uint8_t checksum;                               // Additive sum checksum over all preceding bytes
} flash_data_t;
#pragma pack(pop)

/**
 * @brief Load stored data from flash (call once at startup)
 * @return 0 if valid data loaded, -1 if no valid data (defaults used)
 */
int flash_storage_load(void);

/**
 * @brief Save current configuration to flash
 *
 * Collects current PID gains and mag calibration, then writes to flash.
 * Erases the storage page first (2KB), then writes half-words.
 *
 * @return 0 on success, -1 on failure
 */
int flash_storage_save(void);

#endif // FLASH_STORAGE_H
