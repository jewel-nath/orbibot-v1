/**
 * @file pid_controller.h
 * @brief PID Controller Interface with Multi-Level Gain Support
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Supports speed-dependent PID gains with linear interpolation between
 * 3 gain levels (low/medium/high speed). Based on LGDXRobot2 pattern.
 */

#ifndef PID_CONTROLLER_H
#define PID_CONTROLLER_H

#include <stdint.h>

#define PID_MAX_LEVELS  3

/**
 * @brief PID gain triplet (Kp, Ki, Kd)
 */
typedef struct {
    float kp;
    float ki;
    float kd;
} pid_gains_t;

/**
 * @brief Multi-level PID configuration
 *
 * Stores 3 gain levels and speed thresholds.
 * pid_get_gains_for_speed() interpolates between adjacent levels.
 */
typedef struct {
    pid_gains_t levels[PID_MAX_LEVELS];     // Gain sets per level
    float speed_thresholds[PID_MAX_LEVELS]; // Speed boundaries (mm/s)
} pid_multilevel_t;

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
    float deadzone;     // Output deadzone (ignore pulse)
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

/**
 * @brief Get interpolated PID gains for a given speed
 *
 * Linear interpolation between adjacent gain levels based on absolute speed.
 * Below lowest threshold: returns Level 0 gains.
 * Above highest threshold: returns Level 2 gains.
 * Between thresholds: linearly interpolates Kp, Ki, Kd.
 *
 * @param ml Pointer to multi-level configuration
 * @param speed_mm_s Absolute wheel speed in mm/s
 * @return Interpolated gains
 */
pid_gains_t pid_get_gains_for_speed(const pid_multilevel_t *ml, float speed_mm_s);

#endif // PID_CONTROLLER_H
