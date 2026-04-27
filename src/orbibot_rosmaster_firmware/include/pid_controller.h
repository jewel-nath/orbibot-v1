/**
 * @file pid_controller.h
 * @brief PID Controller Interface
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Incremental PID with trapezoidal I-term and conditional anti-windup.
 */

#ifndef PID_CONTROLLER_H
#define PID_CONTROLLER_H

#include <stdint.h>

/**
 * @brief PID gain triplet (Kp, Ki, Kd)
 */
typedef struct {
    float kp;
    float ki;
    float kd;
} pid_gains_t;

/**
 * @brief PID Controller Structure
 */
typedef struct {
    float kp;           // Active proportional gain
    float ki;           // Active integral gain
    float kd;           // Active derivative gain

    float target;       // Target value
    float output;       // Current output

    float error;        // Current error (e[k])
    float error_prev;   // Previous error (e[k-1])
    float error_next;   // Pre-previous error (e[k-2], used for incremental PID)

    float integral;     // Integral accumulator

    float max_output;   // Output limit
} pid_controller_t;

/**
 * @brief Initialize PID controller
 * @param pid Pointer to PID structure
 * @param kp Proportional gain
 * @param ki Integral gain
 * @param kd Derivative gain
 * @param max_output Maximum output value
 */
void pid_init(pid_controller_t *pid, float kp, float ki, float kd, float max_output);

/**
 * @brief Reset PID controller state
 * @param pid Pointer to PID structure
 */
void pid_reset(pid_controller_t *pid);

/**
 * @brief Set PID target value
 * @param pid Pointer to PID structure
 * @param target Target value
 */
void pid_set_target(pid_controller_t *pid, float target);

/**
 * @brief Calculate Incremental PID output
 *
 * Uses trapezoidal I-term integration with conditional anti-windup.
 *
 * @param pid Pointer to PID structure
 * @param current_val Current measured value
 * @return PID output value
 */
float pid_calculate_incremental(pid_controller_t *pid, float current_val);


#endif // PID_CONTROLLER_H
