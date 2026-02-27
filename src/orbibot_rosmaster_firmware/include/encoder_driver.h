/**
 * @file encoder_driver.h
 * @brief Encoder Driver Interface
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef ENCODER_DRIVER_H
#define ENCODER_DRIVER_H

#include <stdint.h>

int encoder_driver_init(void);

/**
 * @brief Read encoder delta with direction correction
 * @param encoder Encoder number (0-3)
 * @return Delta count since last read
 */
int16_t encoder_read_delta(uint8_t encoder);

/**
 * @brief Get all accumulated encoder counts
 * @param counts Array of 4 int32_t to store counts
 */
void encoder_get_all(int32_t *counts);

/**
 * @brief Reset all encoder counts
 */
void encoder_reset_all(void);

int32_t encoder_get_count(uint8_t encoder);
void encoder_reset(uint8_t encoder);

#endif // ENCODER_DRIVER_H
