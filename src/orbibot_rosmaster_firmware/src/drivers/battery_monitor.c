/**
 * @file battery_monitor.c
 * @brief Battery Monitor Implementation
 *
 * Monitors battery voltage using ADC with voltage divider.
 * Uses multi-sample averaging for accurate readings (matches reference firmware).
 *
 * Hardware configuration:
 * - ADC1 Channel 14 (PC4)
 * - Voltage divider ratio: ~4.03 (10k + 3.3k resistors)
 *
 * @author Jewel Nath
 * @date 2025-11-30
 */

#include "battery_monitor.h"
#include "hal_adc.h"
#include "orbibot_config.h"

/* ADC reference voltage */
#define ADC_VREF            3.3f

/* ADC resolution (12-bit) */
#define ADC_MAX_VALUE       4096.0f

/* Number of samples to average (matches reference firmware) */
#define ADC_SAMPLE_COUNT    4

/**
 * @brief Initialize battery monitor
 * @return 0 on success
 */
int battery_monitor_init(void)
{
    /* ADC initialization is done in hal_adc_init() called from main */
    return 0;
}

/**
 * @brief Get current battery voltage
 * @return Battery voltage in volts
 *
 * Reads ADC multiple times and averages for accuracy.
 * Matches reference firmware approach: 4-sample averaging, no filter.
 *
 * Formula: V_battery = (ADC_avg / 4096) × 3.3V × BATTERY_ADC_RATIO
 */
float battery_get_voltage(void)
{
    uint32_t adc_sum = 0;
    uint16_t adc_value;
    int valid_samples = 0;

    /* Take multiple ADC samples and average (matches reference firmware) */
    for (int i = 0; i < ADC_SAMPLE_COUNT; i++)
    {
        adc_value = hal_adc_read_battery();
        if (adc_value > 0)  /* Check for ADC error (timeout returns 0) */
        {
            adc_sum += adc_value;
            valid_samples++;
        }
    }

    /* Return 0 if no valid samples */
    if (valid_samples == 0)
    {
        return 0.0f;
    }

    /* Calculate average (use bit shift for power of 2, matches reference) */
    uint16_t adc_avg;
    if (valid_samples == 4)
    {
        adc_avg = adc_sum >> 2;  /* Fast divide by 4 */
    }
    else
    {
        adc_avg = adc_sum / valid_samples;
    }

    /* Convert ADC value to voltage (matches reference firmware formula) */
    float measured_voltage = (float)adc_avg * (ADC_VREF / ADC_MAX_VALUE);
    float battery_voltage = measured_voltage * BATTERY_ADC_RATIO;

    return battery_voltage;
}

/**
 * @brief Check if battery voltage is low
 * @return 1 if voltage is below BATTERY_VOLTAGE_LOW threshold, 0 otherwise
 */
int battery_is_low(void)
{
    return (battery_get_voltage() < BATTERY_VOLTAGE_LOW) ? 1 : 0;
}

/**
 * @brief Check if battery voltage is critical
 * @return 1 if voltage is below BATTERY_VOLTAGE_CRITICAL threshold, 0 otherwise
 */
int battery_is_critical(void)
{
    return (battery_get_voltage() < BATTERY_VOLTAGE_CRITICAL) ? 1 : 0;
}
