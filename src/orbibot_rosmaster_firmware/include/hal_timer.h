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
 * @brief Read encoder delta and reset to midpoint
 * @param encoder Encoder number (0-3)
 * @return Delta count since last read
 */
int16_t hal_timer_read_encoder_delta(uint8_t encoder);

/**
 * @brief Get encoder count
 * @param encoder Encoder number (0-3)
 * @return Encoder count
 */
int32_t hal_timer_get_encoder_count(uint8_t encoder);

/**
 * @brief Reset encoder count
 * @param encoder Encoder number (0-3)
 */
void hal_timer_reset_encoder(uint8_t encoder);

/**
 * @brief Stop all motors with brake or freewheel
 * @param brake 1 = active brake (both pins HIGH), 0 = freewheel (both pins LOW)
 *
 * Stop modes control H-bridge behavior for motor control
 */
void hal_timer_motor_stop(uint8_t brake);

#endif // HAL_TIMER_H
