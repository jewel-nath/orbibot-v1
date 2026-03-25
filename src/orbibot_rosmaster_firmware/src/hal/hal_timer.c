/**
 * @file hal_timer.c
 * @brief Timer Hardware Abstraction Layer Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * CRITICAL ENCODER FIXES:
 * - Encoder counters initialized to midpoint (0x7FFF) for bidirectional counting
 * - TIM2 remapped to PA15/PB3 (JTAG disabled) to avoid PA0/PA1 conflict with TIM5
 * - hal_timer_read_encoder_delta() for velocity calculation
 */

#include "hal_timer.h"
#include "stm32f10x.h"
#include "orbibot_config.h"

// Use MOTOR_MAX_PULSE from orbibot_config.h (3600)
#define MOTOR_MAX_PWM           MOTOR_MAX_PULSE
#define ENCODER_TIM_PERIOD      0xFFFF
#define ENCODER_MIDPOINT        0x7FFF

/**
 * @brief Initialize PWM timers (TIM1, TIM8) for motor control
 *
 * Motor PWM configuration for ROSMaster V3.0 board.
 * See HARDWARE_DOC.md for complete pin mappings and timer specifications.
 *
 * Motor Pin Assignments:
 *   M1: PA11/PA8 (TIM8_CH1/CH2)
 *   M2: PB0/PB1 (TIM8_CH3/CH4)
 *   M3: PC6/PC7 (TIM1_CH4/CH1, partial remap)
 *   M4: PC8/PC9 (TIM1_CH2N/CH3N, complementary outputs)
 */
static void hal_timer_pwm_init(void)
{
    TIM_TimeBaseInitTypeDef TIM_TimeBaseStructure;
    TIM_OCInitTypeDef TIM_OCInitStructure;

    // Enable timer clocks and remap
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_TIM8 | RCC_APB2Periph_TIM1, ENABLE);
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_AFIO, ENABLE);
    GPIO_PinRemapConfig(GPIO_PartialRemap_TIM1, ENABLE);

    TIM_DeInit(TIM8);
    TIM_DeInit(TIM1);

    // GPIO AF_PP pins are configured by hal_gpio_init_motor_pwm_pins() in hal_gpio.c.
    // No duplicate GPIO init here.

    // Configure timer timebase
    TIM_TimeBaseStructure.TIM_Prescaler = 0;
    TIM_TimeBaseStructure.TIM_Period = 3600 - 1;
    TIM_TimeBaseStructure.TIM_ClockDivision = TIM_CKD_DIV1;
    TIM_TimeBaseStructure.TIM_CounterMode = TIM_CounterMode_Up;

    TIM_TimeBaseInit(TIM8, &TIM_TimeBaseStructure);
    TIM_TimeBaseInit(TIM1, &TIM_TimeBaseStructure);

    // ========== STEP 4: Configure PWM channels ==========

    // Standard outputs: TIM8 CH1-4 and TIM1 CH1, CH4
    TIM_OCStructInit(&TIM_OCInitStructure);
    TIM_OCInitStructure.TIM_OCMode = TIM_OCMode_PWM1;
    TIM_OCInitStructure.TIM_OutputState = TIM_OutputState_Enable;
    TIM_OCInitStructure.TIM_OCPolarity = TIM_OCPolarity_High;
    TIM_OCInitStructure.TIM_Pulse = 0;

    // TIM8 CH1-4 (M1, M2 motors)
    TIM_OC1Init(TIM8, &TIM_OCInitStructure);
    TIM_OC2Init(TIM8, &TIM_OCInitStructure);
    TIM_OC3Init(TIM8, &TIM_OCInitStructure);
    TIM_OC4Init(TIM8, &TIM_OCInitStructure);

    // TIM1 CH1, CH4 (M3 motor standard outputs)
    TIM_OC1Init(TIM1, &TIM_OCInitStructure);
    TIM_OC4Init(TIM1, &TIM_OCInitStructure);

    // TIM1 CH2N, CH3N (M4 motor complementary outputs)
    // PC8/PC9 are wired to complementary outputs, not standard channels
    TIM_OCInitStructure.TIM_OCMode = TIM_OCMode_PWM1;
    TIM_OCInitStructure.TIM_OutputState = TIM_OutputState_Disable;   // Disable CH2/CH3
    TIM_OCInitStructure.TIM_OutputNState = TIM_OutputNState_Enable;  // Enable CH2N/CH3N
    TIM_OCInitStructure.TIM_OCPolarity = TIM_OCPolarity_High;
    TIM_OCInitStructure.TIM_Pulse = 0;

    TIM_OC2Init(TIM1, &TIM_OCInitStructure);
    TIM_OC3Init(TIM1, &TIM_OCInitStructure);

    // ========== STEP 5: Enable PWM outputs ==========
    TIM_CtrlPWMOutputs(TIM8, ENABLE);
    TIM_CtrlPWMOutputs(TIM1, ENABLE);
    TIM_Cmd(TIM8, ENABLE);
    TIM_Cmd(TIM1, ENABLE);
}

/**
 * @brief Disable JTAG to free PA15/PB3 for TIM2 encoder
 *
 * ROSMaster board uses PA15 and PB3 for TIM2 encoder (Motor 1).
 * These pins are JTAG by default, so we disable JTAG while keeping SWD.
 *
 * Configuration:
 * - SWJ_CFG[2:0] = 010 means "JTAG-DP Disabled and SW-DP Enabled"
 * - This frees PA15 (JTDI) and PB3 (JTDO) for TIM2 use
 * - SWD debugging remains functional via PA13/PA14
 */
static void hal_timer_disable_jtag(void)
{
    // Enable AFIO clock (bit 0 of APB2ENR)
    RCC->APB2ENR |= (1 << 0);

    // Configure SWJ_CFG bits [26:24] in AFIO_MAPR
    // 010 = JTAG-DP Disabled, SW-DP Enabled (frees PA15/PB3)
    AFIO->MAPR &= 0xF8FFFFFF;  // Clear bits [26:24]
    AFIO->MAPR |= (0x01 << 25); // Set SWJ_CFG = 010
}

/**
 * @brief Initialize TIM2 encoder (Motor 1 - HAL3: PA15, PB3)
 *
 * CRITICAL: TIM2 requires partial remap to use PA15/PB3!
 * ROSMaster V3.0 encoder hardware configuration for Motor 1.
 */
static void hal_timer_encoder_init_tim2(void)
{
    TIM_TimeBaseInitTypeDef TIM_TimeBaseStructure;
    TIM_ICInitTypeDef TIM_ICInitStructure;
    GPIO_InitTypeDef GPIO_InitStructure;

    // Enable AFIO clock and apply TIM2 partial remap FIRST
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_AFIO, ENABLE);
    GPIO_PinRemapConfig(GPIO_PartialRemap1_TIM2, ENABLE);

    // CRITICAL: Disable JTAG AFTER GPIO_PinRemapConfig!
    // The STM32 standard library's GPIO_PinRemapConfig() clobbers the SWJ_CFG bits
    // (it does tmpreg |= ~DBGAFR_SWJCFG_MASK which sets bits [27:24] to 1111)
    // So we MUST call hal_timer_disable_jtag() AFTER to restore proper SWJ_CFG.
    hal_timer_disable_jtag();

    // Enable TIM2 clock
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM2, ENABLE);

    // Configure PA15 as input with pull-up (TIM2_CH1 = HAL_3A)
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_15;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    // Configure PB3 as input with pull-up (TIM2_CH2 = HAL_3B)
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_3;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    // Configure TIM2 timebase
    TIM_TimeBaseStructInit(&TIM_TimeBaseStructure);
    TIM_TimeBaseStructure.TIM_Prescaler = 0;
    TIM_TimeBaseStructure.TIM_Period = ENCODER_TIM_PERIOD;
    TIM_TimeBaseStructure.TIM_ClockDivision = TIM_CKD_DIV1;
    TIM_TimeBaseStructure.TIM_CounterMode = TIM_CounterMode_Up;
    TIM_TimeBaseInit(TIM2, &TIM_TimeBaseStructure);

    // Configure encoder interface
    TIM_EncoderInterfaceConfig(TIM2, TIM_EncoderMode_TI12,
                               TIM_ICPolarity_Rising, TIM_ICPolarity_Rising);

    // Configure input capture filter (10-sample digital filter for noise rejection)
    TIM_ICStructInit(&TIM_ICInitStructure);
    TIM_ICInitStructure.TIM_ICFilter = 10;
    TIM_ICInit(TIM2, &TIM_ICInitStructure);

    // Clear update flag (we poll CNT directly, no interrupt needed)
    TIM_ClearFlag(TIM2, TIM_FLAG_Update);

    // Set counter to midpoint for bidirectional counting
    TIM2->CNT = ENCODER_MIDPOINT;

    // Enable timer
    TIM_Cmd(TIM2, ENABLE);
}

/**
 * @brief Initialize TIM3 encoder (Motor 4 - HAL2: PA6, PA7)
 */
static void hal_timer_encoder_init_tim3(void)
{
    TIM_TimeBaseInitTypeDef TIM_TimeBaseStructure;
    TIM_ICInitTypeDef TIM_ICInitStructure;
    GPIO_InitTypeDef GPIO_InitStructure;

    // Enable TIM3 clock
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM3, ENABLE);

    // Configure PA6, PA7 as inputs with pull-up
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_6 | GPIO_Pin_7;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    // Configure TIM3 timebase
    TIM_TimeBaseStructInit(&TIM_TimeBaseStructure);
    TIM_TimeBaseStructure.TIM_Prescaler = 0;
    TIM_TimeBaseStructure.TIM_Period = ENCODER_TIM_PERIOD;
    TIM_TimeBaseStructure.TIM_ClockDivision = TIM_CKD_DIV1;
    TIM_TimeBaseStructure.TIM_CounterMode = TIM_CounterMode_Up;
    TIM_TimeBaseInit(TIM3, &TIM_TimeBaseStructure);

    // Configure encoder interface
    TIM_EncoderInterfaceConfig(TIM3, TIM_EncoderMode_TI12,
                               TIM_ICPolarity_Rising, TIM_ICPolarity_Rising);

    // Configure input capture filter
    TIM_ICStructInit(&TIM_ICInitStructure);
    TIM_ICInitStructure.TIM_ICFilter = 10;
    TIM_ICInit(TIM3, &TIM_ICInitStructure);

    // Clear update flag (don't enable interrupt - we poll CNT directly)
    TIM_ClearFlag(TIM3, TIM_FLAG_Update);

    TIM3->CNT = ENCODER_MIDPOINT;

    // Enable timer
    TIM_Cmd(TIM3, ENABLE);
}

/**
 * @brief Initialize TIM4 encoder (Motor 2 - HAL4: PB6, PB7)
 */
static void hal_timer_encoder_init_tim4(void)
{
    TIM_TimeBaseInitTypeDef TIM_TimeBaseStructure;
    TIM_ICInitTypeDef TIM_ICInitStructure;
    GPIO_InitTypeDef GPIO_InitStructure;

    // Enable TIM4 clock
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM4, ENABLE);

    // Configure PB6, PB7 as inputs with pull-up
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_6 | GPIO_Pin_7;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOB, &GPIO_InitStructure);

    // Configure TIM4 timebase
    TIM_TimeBaseStructInit(&TIM_TimeBaseStructure);
    TIM_TimeBaseStructure.TIM_Prescaler = 0;
    TIM_TimeBaseStructure.TIM_Period = ENCODER_TIM_PERIOD;
    TIM_TimeBaseStructure.TIM_ClockDivision = TIM_CKD_DIV1;
    TIM_TimeBaseStructure.TIM_CounterMode = TIM_CounterMode_Up;
    TIM_TimeBaseInit(TIM4, &TIM_TimeBaseStructure);

    // Configure encoder interface
    TIM_EncoderInterfaceConfig(TIM4, TIM_EncoderMode_TI12,
                               TIM_ICPolarity_Rising, TIM_ICPolarity_Rising);

    // Configure input capture filter
    TIM_ICStructInit(&TIM_ICInitStructure);
    TIM_ICInitStructure.TIM_ICFilter = 10;
    TIM_ICInit(TIM4, &TIM_ICInitStructure);

    // Clear update flag (don't enable interrupt - we poll CNT directly)
    TIM_ClearFlag(TIM4, TIM_FLAG_Update);

    TIM4->CNT = ENCODER_MIDPOINT;

    // Enable timer
    TIM_Cmd(TIM4, ENABLE);
}

/**
 * @brief Initialize TIM5 encoder (Motor 3 - HAL1: PA0, PA1)
 */
static void hal_timer_encoder_init_tim5(void)
{
    TIM_TimeBaseInitTypeDef TIM_TimeBaseStructure;
    TIM_ICInitTypeDef TIM_ICInitStructure;
    GPIO_InitTypeDef GPIO_InitStructure;

    // Enable TIM5 clock
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM5, ENABLE);

    // Configure PA0, PA1 as inputs with pull-up
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_0 | GPIO_Pin_1;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    // Configure TIM5 timebase
    TIM_TimeBaseStructInit(&TIM_TimeBaseStructure);
    TIM_TimeBaseStructure.TIM_Prescaler = 0;
    TIM_TimeBaseStructure.TIM_Period = ENCODER_TIM_PERIOD;
    TIM_TimeBaseStructure.TIM_ClockDivision = TIM_CKD_DIV1;
    TIM_TimeBaseStructure.TIM_CounterMode = TIM_CounterMode_Up;
    TIM_TimeBaseInit(TIM5, &TIM_TimeBaseStructure);

    // Configure encoder interface
    TIM_EncoderInterfaceConfig(TIM5, TIM_EncoderMode_TI12,
                               TIM_ICPolarity_Rising, TIM_ICPolarity_Rising);

    // Configure input capture filter
    TIM_ICStructInit(&TIM_ICInitStructure);
    TIM_ICInitStructure.TIM_ICFilter = 10;
    TIM_ICInit(TIM5, &TIM_ICInitStructure);

    // Clear update flag (don't enable interrupt - we poll CNT directly)
    TIM_ClearFlag(TIM5, TIM_FLAG_Update);

    TIM5->CNT = ENCODER_MIDPOINT;

    // Enable timer
    TIM_Cmd(TIM5, ENABLE);
}

/**
 * @brief Initialize all encoder timers
 *
 * Encoder to Motor mapping (ROSMaster V3.0):
 * - TIM2 (PA15, PB3) -> M1 (Front-Left)  - HAL3
 * - TIM4 (PB6, PB7)  -> M2 (Back-Left)   - HAL4
 * - TIM5 (PA0, PA1)  -> M3 (Front-Right) - HAL1
 * - TIM3 (PA6, PA7)  -> M4 (Back-Right)  - HAL2
 */
static void hal_timer_encoder_init(void)
{
    hal_timer_encoder_init_tim2();  // M1
    hal_timer_encoder_init_tim4();  // M2
    hal_timer_encoder_init_tim5();  // M3
    hal_timer_encoder_init_tim3();  // M4
}

/**
 * @brief Initialize all timers
 */
int hal_timer_init(void)
{
    hal_timer_pwm_init();
    hal_timer_encoder_init();
    return 0;
}

/* Table-driven motor-to-timer mapping (ROSMaster V3.0).
 * Each entry maps a motor index to its forward/reverse CCR registers
 * and direction sign. Changing wiring is now a config change, not code.
 * CCR registers are 16-bit on STM32F1. */
typedef struct {
    volatile uint16_t *ccr_fwd;
    volatile uint16_t *ccr_rev;
    int8_t direction;        // +1 normal, -1 inverted (left-side motors)
} motor_hw_map_t;

static const motor_hw_map_t motor_map[4] = {
    { &TIM8->CCR1, &TIM8->CCR2, -1 },  // M1 Front-Left  (inverted)
    { &TIM8->CCR3, &TIM8->CCR4, -1 },  // M2 Back-Left   (inverted)
    { &TIM1->CCR4, &TIM1->CCR1,  1 },  // M3 Front-Right (normal)
    { &TIM1->CCR2, &TIM1->CCR3,  1 },  // M4 Back-Right  (normal)
};

void hal_timer_set_motor_pwm(uint8_t motor, int16_t pwm)
{
    if (motor >= 4) return;

    if (pwm > MOTOR_MAX_PWM) pwm = MOTOR_MAX_PWM;
    if (pwm < -MOTOR_MAX_PWM) pwm = -MOTOR_MAX_PWM;

    const motor_hw_map_t *m = &motor_map[motor];
    pwm *= m->direction;

    if (pwm >= 0)
    {
        *m->ccr_fwd = (uint16_t)pwm;
        *m->ccr_rev = 0;
    }
    else
    {
        *m->ccr_fwd = 0;
        *m->ccr_rev = (uint16_t)(-pwm);
    }
}

/* Encoder timer mapping: motor index → hardware timer.
 * M1=TIM2, M2=TIM4, M3=TIM5, M4=TIM3 (ROSMaster V3.0 wiring). */
static TIM_TypeDef * const encoder_tim[4] = { TIM2, TIM4, TIM5, TIM3 };

/* Previous counter values for atomic delta calculation.
 * 16-bit modular subtraction avoids the non-atomic read-then-reset pattern. */
static uint16_t encoder_prev_cnt[4] = {
    ENCODER_MIDPOINT, ENCODER_MIDPOINT, ENCODER_MIDPOINT, ENCODER_MIDPOINT
};

/**
 * @brief Read encoder delta (single read, no reset — fully atomic)
 *
 * 16-bit unsigned subtraction handles hardware counter wrap correctly
 * as long as |delta| < 32768 per read (always true at 100Hz).
 */
int16_t hal_timer_read_encoder_delta(uint8_t encoder)
{
    if (encoder >= 4) return 0;

    uint16_t current = (uint16_t)encoder_tim[encoder]->CNT;
    int16_t delta = (int16_t)(current - encoder_prev_cnt[encoder]);
    encoder_prev_cnt[encoder] = current;
    return delta;
}

/**
 * @brief Get raw encoder count relative to midpoint
 */
int32_t hal_timer_get_encoder_count(uint8_t encoder)
{
    if (encoder >= 4) return 0;
    return (int32_t)((int16_t)encoder_tim[encoder]->CNT - ENCODER_MIDPOINT);
}

/**
 * @brief Reset encoder count to midpoint
 */
void hal_timer_reset_encoder(uint8_t encoder)
{
    if (encoder >= 4) return;
    encoder_tim[encoder]->CNT = ENCODER_MIDPOINT;
    encoder_prev_cnt[encoder] = ENCODER_MIDPOINT;
}

/**
 * @brief Stop all motors with brake or freewheel
 *
 * Stop modes:
 * - brake=1: Both PWM pins HIGH (short-circuit braking)
 * - brake=0: Both PWM pins LOW (motor coasts/freewheels)
 */
void hal_timer_motor_stop(uint8_t brake)
{
    if (brake)
    {
        // Active braking: set both PWM pins HIGH
        // This creates a short-circuit that resists motor rotation
        TIM8->CCR1 = MOTOR_MAX_PWM;  // M1A
        TIM8->CCR2 = MOTOR_MAX_PWM;  // M1B
        TIM8->CCR3 = MOTOR_MAX_PWM;  // M2A
        TIM8->CCR4 = MOTOR_MAX_PWM;  // M2B
        TIM1->CCR4 = MOTOR_MAX_PWM;  // M3A
        TIM1->CCR1 = MOTOR_MAX_PWM;  // M3B
        TIM1->CCR2 = MOTOR_MAX_PWM;  // M4A
        TIM1->CCR3 = MOTOR_MAX_PWM;  // M4B
    }
    else
    {
        // Freewheel: set both PWM pins LOW
        // Motor coasts to a stop
        TIM8->CCR1 = 0;  // M1A
        TIM8->CCR2 = 0;  // M1B
        TIM8->CCR3 = 0;  // M2A
        TIM8->CCR4 = 0;  // M2B
        TIM1->CCR4 = 0;  // M3A
        TIM1->CCR1 = 0;  // M3B
        TIM1->CCR2 = 0;  // M4A
        TIM1->CCR3 = 0;  // M4B
    }
}
