/**
 * @file hal_timer.h
 * @brief Timer Hardware Abstraction Layer
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Provides timer interfaces for:
 * - PWM generation for motor control (TIM1, TIM8)
 * - Encoder quadrature decoding (TIM2-TIM5)
 */

#ifndef HAL_TIMER_H
#define HAL_TIMER_H

#include <stdint.h>

/**
 * @brief Initialize all timers
 * @return 0 on success, -1 on failure
 */
int hal_timer_init(void);

/**
 * @brief Set motor PWM duty cycle
 * @param motor Motor number (0-3)
 * @param pwm PWM value (-3600 to +3600, negative = reverse)
 */
void hal_timer_set_motor_pwm(uint8_t motor, int16_t pwm);

/**
 * @brief Read encoder delta since the previous call (atomic, no reset)
 * @param encoder Encoder number (0-3)
 * @return Signed delta; 16-bit modular subtraction handles CNT wrap.
 */
int16_t hal_timer_read_encoder_delta(uint8_t encoder);

/**
 * @brief Reset encoder CNT register to midpoint (used by 0x08 protocol cmd)
 * @param encoder Encoder number (0-3)
 */
void hal_timer_reset_encoder(uint8_t encoder);

#endif // HAL_TIMER_H
