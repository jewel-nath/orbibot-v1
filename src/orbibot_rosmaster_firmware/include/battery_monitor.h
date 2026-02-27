/**
 * @file battery_monitor.h
 * @brief Battery Monitor Interface
 *
 * Provides battery voltage monitoring with low/critical threshold detection.
 *
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef BATTERY_MONITOR_H
#define BATTERY_MONITOR_H

#include <stdint.h>

/**
 * @brief Initialize battery monitor
 * @return 0 on success
 */
int battery_monitor_init(void);

/**
 * @brief Get current battery voltage
 * @return Battery voltage in volts (filtered)
 */
float battery_get_voltage(void);

/**
 * @brief Check if battery voltage is low
 * @return 1 if voltage is below BATTERY_VOLTAGE_LOW, 0 otherwise
 */
int battery_is_low(void);

/**
 * @brief Check if battery voltage is critical
 * @return 1 if voltage is below BATTERY_VOLTAGE_CRITICAL, 0 otherwise
 */
int battery_is_critical(void);

#endif /* BATTERY_MONITOR_H */
