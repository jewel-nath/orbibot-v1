/**
 * @file task_control.h
 * @brief Control Task Interface
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef TASK_CONTROL_H
#define TASK_CONTROL_H

#include "mecanum_kinematics.h"
#include "pid_controller.h"

/**
 * @brief Initialize Control Task
 */
void task_control_init(void);

/**
 * @brief Control Task Entry Point
 * @param params Task parameters
 */
void task_control(void *params);

/**
 * @brief Set/clear battery lockout (blocks non-zero motor commands)
 * @param locked 1 = motors locked out, 0 = normal operation
 */
void control_set_battery_lockout(uint8_t locked);

/**
 * @brief Check if battery lockout is active
 * @return 1 if locked out, 0 if normal
 */
uint8_t control_get_battery_lockout(void);

/**
 * @brief Set target robot velocity
 * @param vx Linear X (m/s)
 * @param vy Linear Y (m/s)
 * @param omega Angular Z (rad/s)
 *
 * Non-zero commands are silently rejected when battery lockout is active.
 */
void control_set_velocity(float vx, float vy, float omega);

/**
 * @brief Get current measured robot velocity (from encoders)
 * @param vx Pointer to linear X velocity (mm/s)
 * @param vy Pointer to linear Y velocity (mm/s)
 * @param vz Pointer to angular Z velocity (mrad/s)
 *
 * This returns the ACTUAL measured velocity, not the commanded velocity.
 * Used by protocol auto-report for velocity feedback.
 */
void control_get_measured_velocity(int16_t *vx, int16_t *vy, int16_t *vz);

/**
 * @brief Update command timestamp (call when motion command received)
 *
 * This should be called from protocol_handle_motion() to track when
 * the last valid command was received. If COMMAND_TIMEOUT_MS elapses
 * without a command, motors will automatically stop for safety.
 */
void control_update_command_time(void);

/**
 * @brief Set motor PID gains at runtime
 * @param kp Proportional gain [0, 10.0]
 * @param ki Integral gain [0, 10.0]
 * @param kd Derivative gain [0, 10.0]
 *
 * Updates all 4 motor PID controllers atomically using a critical section.
 * Resets PID state after update to prevent accumulated error spikes.
 */
void control_set_motor_pid(float kp, float ki, float kd);

/**
 * @brief Set yaw PID gains at runtime
 * @param kp Proportional gain [0, 10.0]
 * @param ki Integral gain [0, 10.0]
 * @param kd Derivative gain [0, 10.0]
 *
 * Updates yaw drift compensation PID atomically using a critical section.
 * Resets PID state after update to prevent accumulated error spikes.
 */
void control_set_yaw_pid(float kp, float ki, float kd);

/**
 * @brief Get firmware-side odometry (x, y, theta, vx, vy, omega)
 * @param x Pointer to X position (m)
 * @param y Pointer to Y position (m)
 * @param theta Pointer to heading (rad)
 * @param vx Pointer to linear X velocity (m/s)
 * @param vy Pointer to linear Y velocity (m/s)
 * @param omega Pointer to angular velocity (rad/s)
 */
void control_get_firmware_odometry(float *x, float *y, float *theta,
                                   float *vx, float *vy, float *omega);

/**
 * @brief Reset firmware odometry to zero
 */
void control_reset_odometry(void);

/**
 * @brief Get current motor PID gains (read-only)
 * @return Pointer to pid_gains_t
 */
const pid_gains_t *control_get_motor_pid(void);

#endif /* TASK_CONTROL_H */
