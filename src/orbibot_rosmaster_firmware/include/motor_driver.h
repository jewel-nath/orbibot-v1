/**
 * @file motor_driver.h
 * @brief Motor Driver Interface
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Minimal surface: init + per-motor speed. Bulk stop is
 * `motor_set_speed(i, 0)` for each i; direct brake/freewheel hardware
 * control lives in hal_timer.c for callers who need it.
 */

#ifndef MOTOR_DRIVER_H
#define MOTOR_DRIVER_H

#include <stdint.h>

int motor_driver_init(void);
void motor_set_speed(uint8_t motor, int16_t speed);

#endif // MOTOR_DRIVER_H
