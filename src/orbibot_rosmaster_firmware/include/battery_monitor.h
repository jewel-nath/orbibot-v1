/**
 * @file battery_monitor.h
 * @brief Battery Monitor Interface
 *
 * Reads battery voltage via ADC1_CH14, applies an EMA filter, and returns
 * the smoothed value in volts. Threshold comparisons live in the caller
 * (task_monitoring.c) against the BATTERY_VOLTAGE_* constants from
 * orbibot_config.h.
 *
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef BATTERY_MONITOR_H
#define BATTERY_MONITOR_H

#include <stdint.h>

/**
 * @brief Initialize battery monitor (no-op; ADC init is done in hal_adc_init)
 * @return 0 on success
 */
int battery_monitor_init(void);

/**
 * @brief Get current battery voltage in volts (EMA-filtered)
 */
float battery_get_voltage(void);

#endif /* BATTERY_MONITOR_H */
