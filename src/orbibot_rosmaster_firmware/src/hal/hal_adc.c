/**
 * @file hal_adc.c
 * @brief ADC Hardware Abstraction Layer Implementation
 *
 * Provides ADC functionality for battery voltage monitoring.
 * Uses ADC1 Channel 14 (PC4) with voltage divider (~4.03 ratio).
 *
 * Battery voltage calculation:
 *   V_battery = (ADC_value / 4095) * 3.3V * 4.03 (voltage divider ratio)
 *
 * @author Jewel Nath
 * @date 2025-11-30
 */

#include "hal_adc.h"
#include "stm32f10x.h"
#include "orbibot_config.h"

/* ADC reference voltage (3.3V) */
#define ADC_VREF            3.3f

/* ADC resolution (12-bit = 4096 levels) */
#define ADC_MAX_VALUE       4095

/**
 * @brief Initialize ADC1 for battery voltage monitoring
 * @return 0 on success, -1 on error
 *
 * Configuration:
 * - ADC1, Channel (Configured in orbibot_config.h)
 * - Single conversion mode
 * - Software trigger
 * - 12-bit resolution
 */
int hal_adc_init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    ADC_InitTypeDef ADC_InitStructure;

    /* Enable clocks */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_ADC1 | BATTERY_ADC_GPIO_CLK, ENABLE);

    /* Configure ADC clock (max 14MHz, PCLK2=72MHz / 6 = 12MHz) */
    RCC_ADCCLKConfig(RCC_PCLK2_Div6);

    /* Configure ADC pin as analog input */
    GPIO_InitStructure.GPIO_Pin = BATTERY_ADC_PIN;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_AIN;
    GPIO_Init(BATTERY_ADC_GPIO_PORT, &GPIO_InitStructure);

    /* ADC1 configuration */
    ADC_InitStructure.ADC_Mode = ADC_Mode_Independent;
    ADC_InitStructure.ADC_ScanConvMode = DISABLE;
    ADC_InitStructure.ADC_ContinuousConvMode = DISABLE;
    ADC_InitStructure.ADC_ExternalTrigConv = ADC_ExternalTrigConv_None;
    ADC_InitStructure.ADC_DataAlign = ADC_DataAlign_Right;
    ADC_InitStructure.ADC_NbrOfChannel = 1;
    ADC_Init(ADC1, &ADC_InitStructure);

    /* Configure ADC1 regular channel */
    ADC_RegularChannelConfig(ADC1, BATTERY_ADC_CHANNEL, 1, ADC_SampleTime_239Cycles5);

    /* Enable ADC1 */
    ADC_Cmd(ADC1, ENABLE);

    /* ADC1 calibration */
    ADC_ResetCalibration(ADC1);
    while (ADC_GetResetCalibrationStatus(ADC1))
        ;

    ADC_StartCalibration(ADC1);
    while (ADC_GetCalibrationStatus(ADC1))
        ;

    return 0;
}

/**
 * @brief Read battery voltage ADC value
 * @return Raw ADC value (0-4095)
 *
 * Performs single ADC conversion on configured channel.
 * Use battery_get_voltage() for actual voltage in volts.
 */
uint16_t hal_adc_read_battery(void)
{
    /* Start ADC1 software conversion */
    ADC_SoftwareStartConvCmd(ADC1, ENABLE);

    /* Wait for conversion to complete (with timeout) */
    uint32_t timeout = 100000;
    while (ADC_GetFlagStatus(ADC1, ADC_FLAG_EOC) == RESET)
    {
        if (--timeout == 0)
        {
            return 0;  /* Timeout - return 0 to indicate error */
        }
    }

    /* Return ADC conversion result */
    return ADC_GetConversionValue(ADC1);
}
