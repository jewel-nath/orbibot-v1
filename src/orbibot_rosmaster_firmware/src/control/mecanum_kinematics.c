/**
 * @file mecanum_kinematics.c
 * @brief Mecanum Wheel Kinematics Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 *
 * Implements inverse and forward kinematics for 4-wheel mecanum robot.
 * Standard mecanum kinematics with ROS coordinate frame (X=Forward, Y=Left, Z=Up).
 */

#include "mecanum_kinematics.h"

// APB (Axle-Pedal-Base) = (Wheelbase + Trackwidth) / 2
// Used for rotation calculation
#define ROBOT_APB  WHEELBASE_PLUS_TRACK

void mecanum_inverse_kinematics(const robot_velocity_t *robot, wheel_velocity_t *wheels)
{
    // Standard Mecanum Formula (ROS coordinate frame: X=Forward, Y=Left, Z=Up):
    // FL = Vx - Vy - (lx + ly)*omega
    // FR = Vx + Vy + (lx + ly)*omega
    // BL = Vx + Vy - (lx + ly)*omega
    // BR = Vx - Vy + (lx + ly)*omega
    //
    // Where:
    // - Vx: forward velocity (m/s)
    // - Vy: lateral velocity (m/s)
    // - omega: angular velocity (rad/s)
    // - APB: (wheelbase + trackwidth) / 2

    float vx = robot->vx;
    float vy = -robot->vy;  // Physical wheel layout has vy inverted vs ROS standard (positive=left)
    float v_rot = robot->omega * ROBOT_APB;

    wheels->fl = vx - vy - v_rot;
    wheels->bl = vx + vy - v_rot;
    wheels->fr = vx + vy + v_rot;
    wheels->br = vx - vy + v_rot;
}

void mecanum_forward_kinematics(const wheel_velocity_t *wheels, robot_velocity_t *robot)
{
    // Forward Kinematics - convert wheel velocities to robot velocity
    // Vx = (FL + FR + BL + BR) / 4
    // Vy = (-FL + FR + BL - BR) / 4
    // Omega = (-FL + FR - BL + BR) / (4 * APB)
    //
    // Where:
    // - FL, FR, BL, BR: wheel velocities (m/s)
    // - APB: (wheelbase + trackwidth) / 2

    robot->vx = (wheels->fl + wheels->bl + wheels->fr + wheels->br) / 4.0f;
    robot->vy = (-wheels->fl + wheels->bl + wheels->fr - wheels->br) / 4.0f;
    robot->omega = (-wheels->fl - wheels->bl + wheels->fr + wheels->br) / (4.0f * ROBOT_APB);
}
