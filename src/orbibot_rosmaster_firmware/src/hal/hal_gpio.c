/**
 * @file hal_gpio.c
 * @brief GPIO Hardware Abstraction Layer Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Initializes GPIO pins for motor control based on ROSMaster board pinout.
 *
 * CRITICAL: Motor PWM pins MUST be configured as AF_PP (Alternate Function Push-Pull)
 * for TIM1/TIM8 PWM output to work correctly!
 *
 * ROSMaster V3.0 Motor PWM Pin Mapping (see HARDWARE_DOC.md for details):
 * - M1: PA11, PA8 -> TIM8->CCR1/CCR2
 * - M2: PB0, PB1 -> TIM8->CCR3/CCR4
 * - M3: PC6, PC7 -> TIM1->CCR4/CCR1 (with GPIO_PartialRemap_TIM1)
 * - M4: PC8, PC9 -> TIM1->CCR2/CCR3 (with GPIO_PartialRemap_TIM1)
 */

#include "hal_gpio.h"
#include "stm32f10x.h"
#include "orbibot_config.h"

// Motor PWM pin aliases (from orbibot_config.h)
#define M1A_PORT    MOTOR1_IN1_PORT
#define M1A_PIN     MOTOR1_IN1_PIN
#define M1B_PORT    MOTOR1_IN2_PORT
#define M1B_PIN     MOTOR1_IN2_PIN

#define M2A_PORT    MOTOR2_IN1_PORT
#define M2A_PIN     MOTOR2_IN1_PIN
#define M2B_PORT    MOTOR2_IN2_PORT
#define M2B_PIN     MOTOR2_IN2_PIN

#define M3A_PORT    MOTOR3_IN1_PORT
#define M3A_PIN     MOTOR3_IN1_PIN
#define M3B_PORT    MOTOR3_IN2_PORT
#define M3B_PIN     MOTOR3_IN2_PIN

#define M4A_PORT    MOTOR4_IN1_PORT
#define M4A_PIN     MOTOR4_IN1_PIN
#define M4B_PORT    MOTOR4_IN2_PORT
#define M4B_PIN     MOTOR4_IN2_PIN

/**
 * @brief Initialize motor PWM GPIO pins as AF_PP
 *
 * Without AF_PP, timer PWM outputs don't reach the motor drivers.
 */
static void hal_gpio_init_motor_pwm_pins(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;

    // M1 PWM pins (PA11, PA8)
    GPIO_InitStructure.GPIO_Pin = M1A_PIN;
    GPIO_Init(M1A_PORT, &GPIO_InitStructure);
    GPIO_InitStructure.GPIO_Pin = M1B_PIN;
    GPIO_Init(M1B_PORT, &GPIO_InitStructure);

    // M2 PWM pins (PB0, PB1)
    GPIO_InitStructure.GPIO_Pin = M2A_PIN;
    GPIO_Init(M2A_PORT, &GPIO_InitStructure);
    GPIO_InitStructure.GPIO_Pin = M2B_PIN;
    GPIO_Init(M2B_PORT, &GPIO_InitStructure);

    // M3 PWM pins (PC6, PC7)
    GPIO_InitStructure.GPIO_Pin = M3A_PIN;
    GPIO_Init(M3A_PORT, &GPIO_InitStructure);
    GPIO_InitStructure.GPIO_Pin = M3B_PIN;
    GPIO_Init(M3B_PORT, &GPIO_InitStructure);

    // M4 PWM pins (PC8, PC9)
    GPIO_InitStructure.GPIO_Pin = M4A_PIN;
    GPIO_Init(M4A_PORT, &GPIO_InitStructure);
    GPIO_InitStructure.GPIO_Pin = M4B_PIN;
    GPIO_Init(M4B_PORT, &GPIO_InitStructure);
}

/**
 * @brief Initialize all GPIO pins for OrbiBot
 */
int hal_gpio_init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_GPIOB |
                           RCC_APB2Periph_GPIOC | RCC_APB2Periph_GPIOD |
                           RCC_APB2Periph_AFIO, ENABLE);

    hal_gpio_init_motor_pwm_pins();

    // LED pins
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;

    GPIO_InitStructure.GPIO_Pin = LED1_PIN;
    GPIO_Init(LED1_PORT, &GPIO_InitStructure);
    GPIO_InitStructure.GPIO_Pin = LED2_PIN;
    GPIO_Init(LED2_PORT, &GPIO_InitStructure);

    GPIO_ResetBits(LED1_PORT, LED1_PIN);
    GPIO_ResetBits(LED2_PORT, LED2_PIN);

    // Buzzer pin
    GPIO_InitStructure.GPIO_Pin = BUZZER_PIN;
    GPIO_Init(BUZZER_PORT, &GPIO_InitStructure);

    BUZZER_OFF();

    // KEY1 button (active-low with pull-up)
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_InitStructure.GPIO_Pin = KEY1_PIN;
    GPIO_Init(KEY1_PORT, &GPIO_InitStructure);

    return 0;
}

/**
 * @brief Set LED state
 */
void hal_gpio_set_led(uint8_t led_num, uint8_t state)
{
    if (led_num == 0)
    {
        if (state)
            GPIO_SetBits(LED1_PORT, LED1_PIN);
        else
            GPIO_ResetBits(LED1_PORT, LED1_PIN);
    }
    else if (led_num == 1)
    {
        if (state)
            GPIO_SetBits(LED2_PORT, LED2_PIN);
        else
            GPIO_ResetBits(LED2_PORT, LED2_PIN);
    }
}

/**
 * @brief Toggle LED state
 */
void hal_gpio_toggle_led(uint8_t led_num)
{
    if (led_num == 0)
    {
        if (GPIO_ReadOutputDataBit(LED1_PORT, LED1_PIN))
            GPIO_ResetBits(LED1_PORT, LED1_PIN);
        else
            GPIO_SetBits(LED1_PORT, LED1_PIN);
    }
    else if (led_num == 1)
    {
        if (GPIO_ReadOutputDataBit(LED2_PORT, LED2_PIN))
            GPIO_ResetBits(LED2_PORT, LED2_PIN);
        else
            GPIO_SetBits(LED2_PORT, LED2_PIN);
    }
}


/**
 * @brief Set buzzer state
 * @param state 1 = ON, 0 = OFF
 */
void hal_gpio_set_buzzer(uint8_t state)
{
    if (state)
    {
        BUZZER_ON();
    }
    else
    {
        BUZZER_OFF();
    }
}

/**
 * @brief Beep buzzer for specified duration
 * @param duration_ms Duration in milliseconds (blocking)
 */
void hal_gpio_beep(uint16_t duration_ms)
{
    BUZZER_ON();

    // Simple delay (blocking) - for startup beep
    for (volatile uint32_t i = 0; i < (duration_ms * 7200); i++)
    {
        __NOP();
    }

    BUZZER_OFF();
}

/**
 * @brief Read KEY1 button state
 * @return 1 if pressed, 0 if released
 */
uint8_t hal_gpio_read_key1(void)
{
    return KEY1_PRESSED() ? 1 : 0;
}
