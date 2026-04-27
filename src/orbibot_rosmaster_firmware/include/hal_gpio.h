/**
 * @file hal_gpio.h
 * @brief GPIO Hardware Abstraction Layer
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Initializes the non-timer GPIOs (motor PWM pin muxing as AF_PP, LEDs,
 * buzzer, KEY1 input). Buzzer drive is via the BUZZER_ON / BUZZER_OFF
 * macros in orbibot_config.h; LED is toggled from task_monitoring.
 */

#ifndef HAL_GPIO_H
#define HAL_GPIO_H

#include <stdint.h>

/**
 * @brief Initialize all GPIO pins for OrbiBot.
 * @return 0 on success, -1 on failure.
 */
int hal_gpio_init(void);

/**
 * @brief Toggle LED state (heartbeat from task_monitoring).
 * @param led_num 0 or 1 (PD3, PD4)
 */
void hal_gpio_toggle_led(uint8_t led_num);

#endif // HAL_GPIO_H
