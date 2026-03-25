/**
 * @file pid_controller.c
 * @brief PID Controller Implementation with Multi-Level Gain Support
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Implements Incremental PID algorithm for motor speed control.
 * Formula: Output += Kp*(e - e_next) + Ki*e_trap + Kd*(e - 2*e_next + e_prev)
 *
 * Improvements over basic PID:
 * - Trapezoidal I-term integration: 0.5 * (e[k] + e[k-1])
 * - Conditional anti-windup: stops I accumulation when output is saturated
 *   in the same direction as the error
 * - Multi-level gain interpolation for speed-dependent tuning
 */

#include "pid_controller.h"

static const float PID_MAX_INTEGRAL_LIMIT = 4000.0f;

void pid_init(pid_controller_t *pid, float kp, float ki, float kd, float max_output)
{
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->max_output = max_output;
    pid->deadzone = 0.0f;

    pid_reset(pid);
}

void pid_reset(pid_controller_t *pid)
{
    pid->target = 0.0f;
    pid->output = 0.0f;
    pid->error = 0.0f;
    pid->error_prev = 0.0f;
    pid->error_next = 0.0f;
    pid->integral = 0.0f;
}

void pid_set_target(pid_controller_t *pid, float target)
{
    pid->target = target;
}

float pid_calculate_incremental(pid_controller_t *pid, float current_val)
{
    // Calculate current error
    pid->error = pid->target - current_val;

    // Incremental PID with trapezoidal I-term
    // Mapping: error = e[k], error_next = e[k-1], error_prev = e[k-2]

    // Trapezoidal integration: average of current and previous error
    float i_term = pid->ki * 0.5f * (pid->error + pid->error_next);

    // Track accumulated integral for anti-windup
    float new_integral = pid->integral + i_term;

    // Conditional anti-windup: don't accumulate I when output is saturated
    // in the same direction as the error (prevents windup during saturation)
    uint8_t saturated = 0;
    if (new_integral > PID_MAX_INTEGRAL_LIMIT)
    {
        new_integral = PID_MAX_INTEGRAL_LIMIT;
        saturated = 1;
    }
    else if (new_integral < -PID_MAX_INTEGRAL_LIMIT)
    {
        new_integral = -PID_MAX_INTEGRAL_LIMIT;
        saturated = 1;
    }

    // Conditional anti-windup: only stop accumulation when error pushes
    // integral further into saturation (same sign as accumulated integral)
    if (saturated && (pid->error * new_integral > 0.0f))
    {
        i_term = 0.0f;  // Stop accumulating in saturation direction
    }
    else
    {
        pid->integral = new_integral;
    }

    // Calculate P and D terms
    float p_term = pid->kp * (pid->error - pid->error_next);
    float d_term = pid->kd * (pid->error - 2.0f * pid->error_next + pid->error_prev);

    // Update output with P + I + D (incremental)
    pid->output += p_term + i_term + d_term;

    // Update error history
    pid->error_prev = pid->error_next;
    pid->error_next = pid->error;

    // Limit output (final clamp)
    if (pid->output > pid->max_output)
    {
        pid->output = pid->max_output;
    }
    else if (pid->output < -pid->max_output)
    {
        pid->output = -pid->max_output;
    }

    return pid->output;
}

