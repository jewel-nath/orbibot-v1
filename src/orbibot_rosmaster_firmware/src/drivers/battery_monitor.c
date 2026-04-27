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

/* ADC full-scale count (12-bit: 0..4095 → 4095 = 3.3 V).
 * Must match ADC_MAX_VALUE in hal_adc.c — both sides use 4095 now.
 * Dividing by 4096 would give a ~0.024 % low voltage reading. */
#define ADC_MAX_VALUE       4095.0f

/* Number of samples to average per read */
#define ADC_SAMPLE_COUNT    4

/* EMA filter coefficient (0.0–1.0, lower = smoother, slower response)
 * At 1Hz monitoring rate: alpha=0.3 gives ~3s settling time */
#define BATTERY_EMA_ALPHA   0.3f

static float ema_voltage = 0.0f;
static uint8_t ema_initialized = 0;

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

    /* Convert ADC value to voltage */
    float measured_voltage = (float)adc_avg * (ADC_VREF / ADC_MAX_VALUE);
    float raw_voltage = measured_voltage * BATTERY_ADC_RATIO;

    /* Apply EMA filter across calls to smooth transient dips
     * (e.g., motor inrush current causing false low-voltage warnings) */
    if (!ema_initialized)
    {
        ema_voltage = raw_voltage;
        ema_initialized = 1;
    }
    else
    {
        ema_voltage = BATTERY_EMA_ALPHA * raw_voltage + (1.0f - BATTERY_EMA_ALPHA) * ema_voltage;
    }

    return ema_voltage;
}
