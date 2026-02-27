/**
 * @file task_monitoring.c
 * @brief Monitoring Task Implementation
 *
 * Handles system health monitoring:
 * - Battery voltage monitoring with 3-level response (normal/low/critical)
 * - Heartbeat LED toggling (1Hz)
 * - Optional OLED display status updates
 *
 * Battery thresholds from orbibot_config.h (do NOT redefine here):
 *   BATTERY_VOLTAGE_LOW      = 11.0V  — warn user with double-beep
 *   BATTERY_VOLTAGE_CRITICAL = 10.5V  — stop motors, continuous beep
 *
 * @author Jewel Nath
 * @date 2025-11-30
 */

#include "task_monitoring.h"
#include "FreeRTOS.h"
#include "task.h"
#include "battery_monitor.h"
#include "hal_gpio.h"
#include "hal_watchdog.h"
#include "protocol.h"
#include "task_control.h"
#include "orbibot_config.h"

#if ENABLE_OLED_DISPLAY
#include "oled_driver.h"
#endif

// Battery warning states (3-level)
typedef enum {
    BATTERY_STATE_NORMAL = 0,
    BATTERY_STATE_LOW,       // Below BATTERY_VOLTAGE_LOW — warn user
    BATTERY_STATE_CRITICAL,  // Below BATTERY_VOLTAGE_CRITICAL — stop motors
} battery_state_t;

static uint32_t heartbeat_count = 0;

void task_monitoring(void *params)
{
    (void)params;

    battery_state_t battery_state = BATTERY_STATE_NORMAL;

    for (;;)
    {
        heartbeat_count++;

        // Feed watchdog to prevent MCU reset (must be done within 5 seconds)
        hal_watchdog_feed();

        // Update buzzer state for timed beeps
        protocol_update_buzzer();

        // Read battery voltage
        float voltage = battery_get_voltage();

        // Toggle status LED to show system is alive
        hal_gpio_toggle_led(0);

        // =====================================================
        // BATTERY VOLTAGE MONITORING (3-level)
        // BATTERY_VOLTAGE_CRITICAL = 10.5V: stop motors, continuous beep
        // BATTERY_VOLTAGE_LOW      = 11.0V: warn, double-beep
        // =====================================================
        if (voltage < BATTERY_VOLTAGE_CRITICAL)
        {
            if (battery_state != BATTERY_STATE_CRITICAL)
            {
                battery_state = BATTERY_STATE_CRITICAL;

                // Stop motors immediately — prevents hard BMS cutoff during motion
                control_set_velocity(0.0f, 0.0f, 0.0f);

                // Continuous beep alert (always active, regardless of OLED state)
                BUZZER_ON();

#if ENABLE_OLED_DISPLAY
                oled_show_low_voltage();
#endif
            }
        }
        else if (voltage < BATTERY_VOLTAGE_LOW)
        {
            if (battery_state == BATTERY_STATE_NORMAL)
            {
                battery_state = BATTERY_STATE_LOW;

                // Double-beep warning (always active, regardless of OLED state)
                BUZZER_ON();
                vTaskDelay(pdMS_TO_TICKS(200));
                BUZZER_OFF();
                vTaskDelay(pdMS_TO_TICKS(200));
                BUZZER_ON();
                vTaskDelay(pdMS_TO_TICKS(200));
                BUZZER_OFF();

#if ENABLE_OLED_DISPLAY
                oled_show_low_voltage();
#endif
            }
        }
        else
        {
            // Voltage recovered — silence buzzer/display. Motors remain stopped;
            // a new cmd_vel from ROS 2 is required to resume motion.
            if (battery_state != BATTERY_STATE_NORMAL)
            {
                battery_state = BATTERY_STATE_NORMAL;
                BUZZER_OFF();

#if ENABLE_OLED_DISPLAY
                oled_show_ready();
#endif
            }
        }

        vTaskDelay(pdMS_TO_TICKS(1000));  // 1Hz monitoring
    }
}
