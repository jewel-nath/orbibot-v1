/**
 * @file motor_driver.h
 * @brief Motor Driver Interface
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef MOTOR_DRIVER_H
#define MOTOR_DRIVER_H

#include <stdint.h>

/**
 * Stop modes for motor control
 */
#define STOP_FREE       0   // Coast/freewheel - motor spins freely
#define STOP_BRAKE      1   // Active brake - motor stops quickly

int motor_driver_init(void);
void motor_set_speed(uint8_t motor, int16_t speed);
void motor_stop_all(void);

/**
 * @brief Stop all motors with specified mode
 * @param brake STOP_BRAKE for active braking, STOP_FREE for coast
 *
 * Stop modes:
 * - STOP_BRAKE: Both PWM pins HIGH = short-circuit braking
 * - STOP_FREE: Both PWM pins LOW = motor coasts
 */
void motor_stop(uint8_t brake);

#endif // MOTOR_DRIVER_H
