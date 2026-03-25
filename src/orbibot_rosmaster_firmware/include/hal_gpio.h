/**
 * @file hal_gpio.h
 * @brief GPIO Hardware Abstraction Layer
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Provides GPIO initialization for all OrbiBot peripherals:
 * - Motor control pins (PWM + direction)
 * - Encoder input pins (quadrature capture)
 * - LED indicators
 * - Buzzer control
 * - Button inputs (KEY1)
 */

#ifndef HAL_GPIO_H
#define HAL_GPIO_H

#include <stdint.h>

/**
 * @brief Initialize all GPIO pins for OrbiBot
 *
 * Configures:
 * - Motor control pins (direction + enable)
 * - LED indicators (PD3, PD4)
 * - Buzzer (PC5)
 * - KEY1 button (PD2)
 *
 * @return 0 on success, -1 on failure
 */
int hal_gpio_init(void);

/**
 * @brief Set LED state
 * @param led_num LED number (0-1 for 2 status LEDs)
 * @param state 1 = ON, 0 = OFF
 */
void hal_gpio_set_led(uint8_t led_num, uint8_t state);

/**
 * @brief Toggle LED state
 * @param led_num LED number (0-1)
 */
void hal_gpio_toggle_led(uint8_t led_num);


/**
 * @brief Set buzzer state
 * @param state 1 = ON, 0 = OFF
 */
void hal_gpio_set_buzzer(uint8_t state);

/**
 * @brief Beep buzzer for specified duration (blocking)
 * @param duration_ms Duration in milliseconds
 */
void hal_gpio_beep(uint16_t duration_ms);

/**
 * @brief Read KEY1 button state
 * @return 1 if pressed, 0 if released
 */
uint8_t hal_gpio_read_key1(void);

#endif // HAL_GPIO_H
