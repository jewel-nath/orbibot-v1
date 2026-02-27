/**
 * @file hal_watchdog.c
 * @brief Independent Watchdog (IWDG) HAL Implementation
 * @author Jewel Nath
 * @date 2025-12-31
 *
 * IWDG Configuration:
 * - Clock: LSI (40kHz nominal)
 * - Prescaler: 256
 * - Reload: 781 (~5 seconds timeout)
 *
 * Formula: timeout = (prescaler * reload) / LSI_freq
 *          5000ms ≈ (256 * 781) / 40000 = 4.99s
 */

#include "hal_watchdog.h"
#include "stm32f10x.h"
#include "stm32f10x_iwdg.h"
#include "orbibot_config.h"

int hal_watchdog_init(void)
{
#if ENABLE_WATCHDOG
    // Enable write access to IWDG registers
    IWDG_WriteAccessCmd(IWDG_WriteAccess_Enable);

    // Set prescaler to 256 (max timeout range)
    // IWDG clock = LSI / 256 = 40kHz / 256 ≈ 156.25Hz
    IWDG_SetPrescaler(IWDG_Prescaler_256);

    // Set reload value for ~5 second timeout
    // Timeout = (256 * 781) / 40000 ≈ 5 seconds
    IWDG_SetReload(781);

    // Reload counter
    IWDG_ReloadCounter();

    // Enable IWDG (cannot be disabled once enabled!)
    IWDG_Enable();
#endif
    return 0;
}

void hal_watchdog_feed(void)
{
#if ENABLE_WATCHDOG
    // Reload the counter (feed the watchdog)
    IWDG_ReloadCounter();
#endif
}
