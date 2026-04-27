/**
 * @file encoder_driver.h
 * @brief Encoder Driver Interface
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Thin wrapper around hal_timer_read_encoder_delta that applies the
 * per-motor direction correction table (encoder_direction[]) and
 * accumulates a signed 32-bit tick count for odometry reporting.
 */

#ifndef ENCODER_DRIVER_H
#define ENCODER_DRIVER_H

#include <stdint.h>

int encoder_driver_init(void);

/**
 * @brief Read delta since last call, sign-correct, and add to accumulator.
 * @param encoder Motor index (0-3: M1=FL, M2=BL, M3=FR, M4=BR)
 * @return Sign-corrected delta (positive = forward wheel rotation)
 */
int16_t encoder_read_delta(uint8_t encoder);

/**
 * @brief Get accumulated count for one motor (used by REPORT_ENCODER packet).
 */
int32_t encoder_get_count(uint8_t encoder);

/**
 * @brief Zero all four accumulators AND the hardware CNT registers
 *        (backs the FUNC_RESET_ENCODERS protocol command).
 */
void encoder_reset_all(void);

#endif // ENCODER_DRIVER_H
