/**
 * @file mecanum_kinematics.h
 * @brief Mecanum Wheel Kinematics
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef MECANUM_KINEMATICS_H
#define MECANUM_KINEMATICS_H

#include "orbibot_config.h"

/**
 * @brief Robot Velocity Structure
 */
typedef struct {
    float vx;       // Linear velocity X (m/s) - Forward
    float vy;       // Linear velocity Y (m/s) - Left
    float omega;    // Angular velocity Z (rad/s) - Counter-clockwise
} robot_velocity_t;

/**
 * @brief Wheel Velocity Structure
 */
typedef struct {
    float fl;       // Front-Left wheel velocity (m/s)
    float bl;       // Back-Left wheel velocity (m/s)
    float fr;       // Front-Right wheel velocity (m/s)
    float br;       // Back-Right wheel velocity (m/s)
} wheel_velocity_t;

/**
 * @brief Calculate wheel velocities from robot velocity (Inverse Kinematics)
 * @param robot Robot velocity (input)
 * @param wheels Wheel velocities (output)
 */
void mecanum_inverse_kinematics(const robot_velocity_t *robot, wheel_velocity_t *wheels);

/**
 * @brief Calculate robot velocity from wheel velocities (Forward Kinematics)
 * @param wheels Wheel velocities (input)
 * @param robot Robot velocity (output)
 */
void mecanum_forward_kinematics(const wheel_velocity_t *wheels, robot_velocity_t *robot);

#endif // MECANUM_KINEMATICS_H
