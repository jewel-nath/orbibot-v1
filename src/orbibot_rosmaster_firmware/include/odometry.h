/**
 * @file odometry.h
 * @brief Odometry Calculation
 * @author Jewel Nath
 * @date 2025-11-30
 */

#ifndef ODOMETRY_H
#define ODOMETRY_H

#include "mecanum_kinematics.h"

/**
 * @brief Odometry Pose Structure
 */
typedef struct {
    float x;        // X position (m)
    float y;        // Y position (m)
    float theta;    // Heading (rad)
    
    float vx;       // Linear velocity X (m/s)
    float vy;       // Linear velocity Y (m/s)
    float omega;    // Angular velocity Z (rad/s)
} odometry_t;

/**
 * @brief Initialize odometry
 * @param odom Pointer to odometry structure
 */
void odometry_init(odometry_t *odom);

/**
 * @brief Update odometry based on wheel velocities
 * @param odom Pointer to odometry structure
 * @param wheels Wheel velocities (m/s)
 * @param dt Time delta (seconds)
 */
void odometry_update(odometry_t *odom, const wheel_velocity_t *wheels, float dt);

/**
 * @brief Reset odometry pose to zero
 * @param odom Pointer to odometry structure
 */
void odometry_reset(odometry_t *odom);

#endif // ODOMETRY_H
