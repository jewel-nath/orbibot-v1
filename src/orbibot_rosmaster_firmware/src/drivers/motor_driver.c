/**
 * @file motor_driver.c
 * @brief Motor Driver Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Includes deadzone compensation for AM2857 motor drivers
 * that require minimum PWM to overcome static friction
 */

#include "motor_driver.h"
#include "hal_timer.h"
#include "orbibot_config.h"

int motor_driver_init(void)
{
    return 0;
}

/**
 * @brief Apply deadzone compensation to motor speed
 *
 * AM2857 motor drivers require minimum PWM to overcome static friction.
 * PWM values below ~1600 don't produce enough torque to move the motors.
 * This function adds the deadzone offset to any non-zero speed command.
 *
 * Algorithm:
 *   if (pulse > 0) return pulse + MOTOR_IGNORE_PULSE;
 *   if (pulse < 0) return pulse - MOTOR_IGNORE_PULSE;
 *   return 0;
 *
 * @param speed Input speed from PID (range: -2000 to +2000)
 * @return Compensated speed (range: -3600 to +3600)
 */
static int16_t motor_apply_deadzone(int16_t speed)
{
    if (speed > 0)
    {
        return speed + MOTOR_IGNORE_PULSE;
    }
    else if (speed < 0)
    {
        return speed - MOTOR_IGNORE_PULSE;
    }
    return 0;
}

void motor_set_speed(uint8_t motor, int16_t speed)
{
    if (motor >= 4) return;

    int16_t compensated_speed = motor_apply_deadzone(speed);
    hal_timer_set_motor_pwm(motor, compensated_speed);
}

void motor_stop_all(void)
{
    for (uint8_t i = 0; i < 4; i++)
    {
        hal_timer_set_motor_pwm(i, 0);
    }
}

void motor_stop(uint8_t brake)
{
    // Call HAL function for brake/freewheel stop
    hal_timer_motor_stop(brake);
}
