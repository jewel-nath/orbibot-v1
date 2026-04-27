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

/* Per-task alive counters: each task increments its slot every iteration */
static volatile uint32_t alive_counters[ALIVE_TASK_COUNT] = {0};
static uint32_t alive_snapshot[ALIVE_TASK_COUNT] = {0};

void task_alive_kick(uint8_t task_id)
{
    if (task_id < ALIVE_TASK_COUNT)
        alive_counters[task_id]++;
}

void task_monitoring(void *params)
{
    (void)params;

    battery_state_t battery_state = BATTERY_STATE_NORMAL;

    for (;;)
    {
        heartbeat_count++;

        /* Check alive counters: feed watchdog only if all critical tasks
         * have incremented since the last monitoring cycle. */
        uint8_t all_alive = 1;
        for (uint8_t i = 0; i < ALIVE_TASK_COUNT; i++)
        {
            uint32_t current = alive_counters[i];
            if (current == alive_snapshot[i])
            {
                all_alive = 0;
                break;
            }
            alive_snapshot[i] = current;
        }

#if ENABLE_WATCHDOG
        if (all_alive)
            hal_watchdog_feed();
#else
        (void)all_alive;  /* suppress unused-variable when watchdog disabled */
#endif

        // Note: protocol_update_buzzer() is now called from task_communication at 1ms
        // cadence for accurate buzzer timing. No need to call it here.

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

                // Lock out motors and stop immediately
                control_set_battery_lockout(1);
                control_set_velocity(0.0f, 0.0f, 0.0f);

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

                // Non-blocking double-beep: state machine runs in task_communication
                // at 1ms cadence via protocol_update_buzzer(). This task is not blocked.
                protocol_start_double_beep();

#if ENABLE_OLED_DISPLAY
                oled_show_low_voltage();
#endif
            }
        }
        else
        {
            // Voltage recovered above LOW threshold — clear lockout with hysteresis
            if (battery_state != BATTERY_STATE_NORMAL)
            {
                battery_state = BATTERY_STATE_NORMAL;
                control_set_battery_lockout(0);
                BUZZER_OFF();

#if ENABLE_OLED_DISPLAY
                oled_show_ready();
#endif
            }
        }

        vTaskDelay(pdMS_TO_TICKS(1000));  // 1Hz monitoring
    }
}
