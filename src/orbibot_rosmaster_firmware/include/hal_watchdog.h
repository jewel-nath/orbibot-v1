/**
 * @file hal_watchdog.h
 * @brief Independent Watchdog (IWDG) HAL Interface
 * @author Jewel Nath
 * @date 2025-12-31
 *
 * The IWDG resets the MCU if not fed within the timeout period.
 * Used for system safety and fault recovery.
 */

#ifndef HAL_WATCHDOG_H
#define HAL_WATCHDOG_H

#include <stdint.h>

/**
 * @brief Initialize and start the Independent Watchdog
 *
 * Configures IWDG with approximately 5 second timeout.
 * Once started, IWDG cannot be stopped - must feed regularly.
 *
 * @return 0 on success
 */
int hal_watchdog_init(void);

/**
 * @brief Feed (reload) the watchdog timer
 *
 * Must be called periodically to prevent MCU reset.
 * Typical call rate: at least once per second.
 */
void hal_watchdog_feed(void);

#endif // HAL_WATCHDOG_H
