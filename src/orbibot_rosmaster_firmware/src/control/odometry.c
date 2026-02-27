/**
 * @file odometry.c
 * @brief Odometry Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 */

#include "odometry.h"
#include "orbibot_config.h"
#include <math.h>

void odometry_init(odometry_t *odom)
{
    odometry_reset(odom);
}

void odometry_reset(odometry_t *odom)
{
    odom->x = 0.0f;
    odom->y = 0.0f;
    odom->theta = 0.0f;
    odom->vx = 0.0f;
    odom->vy = 0.0f;
    odom->omega = 0.0f;
}

void odometry_update(odometry_t *odom, const wheel_velocity_t *wheels, float dt)
{
    robot_velocity_t robot_vel;
    
    // Calculate robot velocity from wheel velocities
    mecanum_forward_kinematics(wheels, &robot_vel);
    
    // Update current velocities
    odom->vx = robot_vel.vx;
    odom->vy = robot_vel.vy;
    odom->omega = robot_vel.omega;
    
    // Integrate position (Runge-Kutta 2nd order or simple Euler)
    // Using simple Euler for efficiency on MCU
    
    // Transform velocity to global frame
    float cos_theta = cosf(odom->theta);
    float sin_theta = sinf(odom->theta);
    
    float delta_x = (robot_vel.vx * cos_theta - robot_vel.vy * sin_theta) * dt;
    float delta_y = (robot_vel.vx * sin_theta + robot_vel.vy * cos_theta) * dt;
    float delta_theta = robot_vel.omega * dt;
    
    // Update pose
    odom->x += delta_x;
    odom->y += delta_y;
    odom->theta += delta_theta;
    
    // Normalize theta to -PI ~ PI
    while (odom->theta > PI_F) odom->theta -= 2.0f * PI_F;
    while (odom->theta < -PI_F) odom->theta += 2.0f * PI_F;
}
