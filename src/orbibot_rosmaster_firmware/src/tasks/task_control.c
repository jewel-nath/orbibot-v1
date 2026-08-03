/**
 * @file task_control.c
 * @brief Control Task Implementation
 * @author Jewel Nath
 * @date 2025-11-30
 */

#include "task_control.h"
#include "FreeRTOS.h"
#include "task.h"
#include "motor_driver.h"
#include "encoder_driver.h"
#include "pid_controller.h"
#include "mecanum_kinematics.h"
#include "odometry.h"
#include "imu_driver.h"
#include "flash_storage.h"
#include "task_monitoring.h"
#include "orbibot_config.h"
#include <math.h>

// Global State
static volatile robot_velocity_t target_vel = {0};
static volatile robot_velocity_t measured_vel = {0};  // Actual measured velocity from encoders
static pid_controller_t pid_motor[4];

// Single PID gains (stored for persistence and runtime updates)
static pid_gains_t motor_pid_gains = {
    .kp = PID_KP,
    .ki = PID_KI,
    .kd = PID_KD
};

// Yaw PID Controller (for heading drift compensation during straight-line motion)
// Uses IMU feedback to correct heading drift when moving straight
static pid_controller_t pid_yaw;
static float target_yaw = 0.0f;        // Target heading to maintain
static uint8_t yaw_control_active = 0; // Flag: is yaw control currently active?

// Command timeout tracking (CRIT-3 safety feature)
static volatile TickType_t last_command_time = 0;
static volatile uint8_t command_timeout_active = 0;  // Flag: has timeout occurred?

// Battery lockout: prevents motor commands when battery is critically low.
// Set by task_monitoring, cleared when voltage recovers above hysteresis threshold.
static volatile uint8_t g_battery_lockout = 0;

// Velocity ramp: desire speeds track ramped targets (mm/s, signed)
static float desire_wheel_speed_mm[4] = {0};

// Last valid wheel speed for encoder anomaly rejection (mm/s)
static float last_valid_wheel_speed_mm[4] = {0};

// Firmware-side odometry (integrated at 100Hz)
static odometry_t firmware_odom;

void task_control_init(void)
{
    // Initialize Motor PIDs
    // Max output must be (MOTOR_MAX_PULSE - MOTOR_IGNORE_PULSE) = 2000
    // Deadzone compensation is handled in motor_driver.c, not PID
    float max_output = (float)(MOTOR_MAX_PULSE - MOTOR_IGNORE_PULSE);
    for (int i = 0; i < 4; i++)
    {
        pid_init(&pid_motor[i], PID_KP, PID_KI, PID_KD, max_output);
    }

    // Initialize Yaw PID Controller for heading drift compensation
    // Corrects heading drift during straight-line motion using IMU feedback
    pid_init(&pid_yaw, YAW_PID_KP, YAW_PID_KI, YAW_PID_KD, YAW_PID_MAX_OUTPUT);
    yaw_control_active = 0;
    target_yaw = 0.0f;

    // Initialize firmware odometry
    odometry_init(&firmware_odom);

    // Load PID gains from flash (overrides defaults if valid)
    flash_storage_load();
}

void control_set_battery_lockout(uint8_t locked)
{
    g_battery_lockout = locked;
}

uint8_t control_get_battery_lockout(void)
{
    return g_battery_lockout;
}

void control_set_velocity(float vx, float vy, float omega)
{
    // Refuse non-zero velocity when battery is critically low
    if (g_battery_lockout && (fabsf(vx) > 1e-6f || fabsf(vy) > 1e-6f || fabsf(omega) > 1e-6f))
    {
        return;
    }

    taskENTER_CRITICAL();
    target_vel.vx = vx;
    target_vel.vy = vy;
    target_vel.omega = omega;
    taskEXIT_CRITICAL();
}

void control_get_measured_velocity(int16_t *vx, int16_t *vy, int16_t *vz)
{
    // Return measured velocity in protocol format:
    // vx, vy in mm/s, vz in mrad/s (milliradians per second)
    *vx = (int16_t)(measured_vel.vx * 1000.0f);   // m/s → mm/s
    *vy = (int16_t)(measured_vel.vy * 1000.0f);   // m/s → mm/s; ROS frame (positive = left)
    *vz = (int16_t)(measured_vel.omega * 1000.0f); // rad/s → mrad/s
}

void control_update_command_time(void)
{
    // Update timestamp when motion command received (called from protocol.c)
    last_command_time = xTaskGetTickCount();
    command_timeout_active = 0;  // Clear timeout flag on new command
}

void control_set_motor_pid(float kp, float ki, float kd)
{
    // Reject NaN/Inf before range check (NaN fails all comparisons silently)
    if (!isfinite(kp) || !isfinite(ki) || !isfinite(kd)) return;
    // Validate range
    if (kp < 0.0f || kp > 10.0f) return;
    if (ki < 0.0f || ki > 10.0f) return;
    if (kd < 0.0f || kd > 10.0f) return;

    taskENTER_CRITICAL();
    motor_pid_gains.kp = kp;
    motor_pid_gains.ki = ki;
    motor_pid_gains.kd = kd;
    for (int i = 0; i < 4; i++)
    {
        pid_motor[i].kp = kp;
        pid_motor[i].ki = ki;
        pid_motor[i].kd = kd;
        pid_reset(&pid_motor[i]);
    }
    taskEXIT_CRITICAL();

    DEBUG_INFO("Motor PID updated: Kp=%.3f Ki=%.3f Kd=%.3f\n", kp, ki, kd);
}

const pid_gains_t *control_get_motor_pid(void)
{
    return &motor_pid_gains;
}

void control_get_firmware_odometry(float *x, float *y, float *theta,
                                   float *vx, float *vy, float *omega)
{
    // Critical section: firmware_odom is written at 100Hz by task_control.
    // 6-float struct read must be atomic to avoid torn values in odometry packets.
    taskENTER_CRITICAL();
    float lx = firmware_odom.x;
    float ly = firmware_odom.y;
    float lt = firmware_odom.theta;
    float lvx = firmware_odom.vx;
    float lvy = firmware_odom.vy;
    float lom = firmware_odom.omega;
    taskEXIT_CRITICAL();

    *x = lx;
    *y = ly;
    *theta = lt;
    *vx = lvx;
    *vy = lvy;
    *omega = lom;
}

void control_reset_odometry(void)
{
    taskENTER_CRITICAL();
    odometry_reset(&firmware_odom);
    taskEXIT_CRITICAL();

    DEBUG_INFO("Firmware odometry reset to zero\n");
}

void control_set_yaw_pid(float kp, float ki, float kd)
{
    if (!isfinite(kp) || !isfinite(ki) || !isfinite(kd)) return;
    if (kp < 0.0f || kp > 10.0f) return;
    if (ki < 0.0f || ki > 10.0f) return;
    if (kd < 0.0f || kd > 10.0f) return;

    taskENTER_CRITICAL();
    pid_yaw.kp = kp;
    pid_yaw.ki = ki;
    pid_yaw.kd = kd;
    pid_reset(&pid_yaw);
    taskEXIT_CRITICAL();

    DEBUG_INFO("Yaw PID updated: Kp=%.3f Ki=%.3f Kd=%.3f\n", kp, ki, kd);
}

void task_control(void *params)
{
    (void)params;

    TickType_t last_wake_time = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(1000 / CONTROL_LOOP_RATE_HZ); // 10ms
    const float pulse_to_mm = (2.0f * PI_F * WHEEL_RADIUS_M * 1000.0f) / ENCODER_PPR;

    for (;;)
    {
        // =====================================================
        // COMMAND TIMEOUT CHECK (CRIT-3 Safety Feature)
        // If no command received for COMMAND_TIMEOUT_MS, stop motors
        // =====================================================
        TickType_t current_time = xTaskGetTickCount();
        if (last_command_time > 0)  // Only check after first command received
        {
            TickType_t elapsed = current_time - last_command_time;
            if (elapsed > pdMS_TO_TICKS(COMMAND_TIMEOUT_MS))
            {
                if (!command_timeout_active)
                {
                    // Timeout just occurred - stop motors (critical section protects write)
                    taskENTER_CRITICAL();
                    target_vel.vx = 0.0f;
                    target_vel.vy = 0.0f;
                    target_vel.omega = 0.0f;
                    taskEXIT_CRITICAL();
                    command_timeout_active = 1;
                    DEBUG_INFO("Command timeout! Motors stopped for safety.\n");
                }
            }
        }

        // Read encoder deltas
        int16_t delta[4];
        for (int i = 0; i < 4; i++)
        {
            delta[i] = encoder_read_delta(i);  // HAL handles midpoint, driver handles direction
        }

        // Calculate wheel speeds (mm/s for PID, m/s for odometry)
        float wheel_speed_mm_s[4];
        float wheel_speeds[4];  // m/s for odometry
        for (int i = 0; i < 4; i++)
        {
            wheel_speed_mm_s[i] = (float)delta[i] * pulse_to_mm * CONTROL_LOOP_RATE_HZ;

            // Encoder anomaly rejection: discard readings beyond physical motor limits.
            // EMI spikes or loose connectors can produce huge deltas (e.g., 60000 mm/s)
            // which cause PID overshoot → dangerous motor jerk.
            // lgdxrobot2 uses same approach (motor.c:406-407).
            if (fabsf(wheel_speed_mm_s[i]) > MAX_WHEEL_SPEED_MMS)
            {
                wheel_speed_mm_s[i] = last_valid_wheel_speed_mm[i];
            }
            else
            {
                last_valid_wheel_speed_mm[i] = wheel_speed_mm_s[i];
            }

            wheel_speeds[i] = wheel_speed_mm_s[i] / 1000.0f;  // Convert to m/s
        }

        wheel_velocity_t current_wheel_vel;
        current_wheel_vel.fl = wheel_speeds[0];
        current_wheel_vel.bl = wheel_speeds[1];
        current_wheel_vel.fr = wheel_speeds[2];
        current_wheel_vel.br = wheel_speeds[3];

        // Store measured velocity (critical section: comm task reads at 20Hz)
        robot_velocity_t meas_local;
        mecanum_forward_kinematics(&current_wheel_vel, &meas_local);
        taskENTER_CRITICAL();
        measured_vel.vx = meas_local.vx;
        measured_vel.vy = meas_local.vy;
        measured_vel.omega = meas_local.omega;
        taskEXIT_CRITICAL();

        // Update firmware odometry
        const float dt = 1.0f / (float)CONTROL_LOOP_RATE_HZ;
        odometry_update(&firmware_odom, &current_wheel_vel, dt);

        // Copy target velocity (critical section: protocol task writes)
        robot_velocity_t target_local;
        taskENTER_CRITICAL();
        target_local.vx = target_vel.vx;
        target_local.vy = target_vel.vy;
        target_local.omega = target_vel.omega;
        taskEXIT_CRITICAL();

        wheel_velocity_t target_wheel_vel;
        mecanum_inverse_kinematics(&target_local, &target_wheel_vel);

        // PID operates in mm/s
        float target_wheel_speeds[4] = {
            target_wheel_vel.fl * 1000.0f,  // Convert m/s to mm/s
            target_wheel_vel.bl * 1000.0f,
            target_wheel_vel.fr * 1000.0f,
            target_wheel_vel.br * 1000.0f
        };

        // Stop check: prevents PID runaway when wheels are manually moved
        float total_target = fabsf(target_local.vx) + fabsf(target_local.vy) + fabsf(target_local.omega);
        uint8_t is_stopped = (total_target < 0.001f);

        // =====================================================
        // ASYMMETRIC VELOCITY RAMP
        // Accel (same direction):  accept target immediately (responsive)
        // Decel or sign-change:    ramp toward target gradually (smooth, no shock)
        // Stop:                    immediate zero + PID reset (safe)
        // =====================================================
        for (int i = 0; i < 4; i++)
        {
            float target = target_wheel_speeds[i];
            float desire = desire_wheel_speed_mm[i];

            // Detect sign change: treat as deceleration to prevent instant reversal
            uint8_t sign_change = ((target > 0.0f && desire < 0.0f) ||
                                   (target < 0.0f && desire > 0.0f));

            if (is_stopped)
            {
                // Immediate stop — desire resets to zero
                desire_wheel_speed_mm[i] = 0.0f;
            }
            else if (!sign_change && fabsf(target) >= fabsf(desire))
            {
                // Accelerating in same direction — accept immediately
                desire_wheel_speed_mm[i] = target;
            }
            else
            {
                // Decelerating or direction reversal — ramp toward target gradually
                // Move desire toward target by RAMP per tick (passes through zero on reversal)
                if (desire > target)
                {
                    desire_wheel_speed_mm[i] -= MOTOR_DECEL_RAMP_MMS;
                    if (desire_wheel_speed_mm[i] < target)
                        desire_wheel_speed_mm[i] = target;
                }
                else
                {
                    desire_wheel_speed_mm[i] += MOTOR_DECEL_RAMP_MMS;
                    if (desire_wheel_speed_mm[i] > target)
                        desire_wheel_speed_mm[i] = target;
                }
            }

            // PID uses ramped desire speed, not raw target
            target_wheel_speeds[i] = desire_wheel_speed_mm[i];
        }

        // =====================================================
        // YAW PID CONTROLLER - Heading Drift Compensation
        // Uses IMU feedback to maintain heading during straight-line motion
        // =====================================================
        float yaw_correction = 0.0f;

        // Only apply yaw correction during straight-line motion (no rotation command)
        // and when robot speed exceeds threshold
        float speed_magnitude = sqrtf(target_local.vx * target_local.vx + target_local.vy * target_local.vy);
        uint8_t should_yaw_control = (fabsf(target_local.omega) < 0.01f) &&
                                      (speed_magnitude > YAW_ENABLE_THRESHOLD);

        if (is_stopped)
        {
            // Robot stopped - reset yaw control
            yaw_control_active = 0;
            pid_reset(&pid_yaw);
        }
        else if (should_yaw_control)
        {
            // Get current yaw from IMU
            float roll, pitch, current_yaw;
            imu_get_attitude(&roll, &pitch, &current_yaw);

            if (!yaw_control_active)
            {
                // Just started moving straight - capture target heading
                target_yaw = current_yaw;
                yaw_control_active = 1;
                pid_reset(&pid_yaw);
            }

            // Calculate yaw error and PID correction
            pid_set_target(&pid_yaw, target_yaw);
            float yaw_offset = pid_calculate_incremental(&pid_yaw, current_yaw);

            // Use PID output directly (speed multiplication caused saturation)
            yaw_correction = yaw_offset;
        }
        else
        {
            // Turning or too slow - disable yaw correction
            yaw_control_active = 0;
            pid_reset(&pid_yaw);
        }

        // Signal alive to monitoring task (watchdog fed only by task_monitoring
        // after verifying all tasks are alive)
        task_alive_kick(ALIVE_TASK_CONTROL);

        // Apply motor control with yaw correction and speed-dependent PID gains
        for (int i = 0; i < 4; i++)
        {
            if (is_stopped)
            {
                // Reset PID state when stopped to prevent accumulated error
                // This is critical: without reset, manually moving wheels causes runaway
                pid_reset(&pid_motor[i]);
                motor_set_speed(i, 0);
            }
            else
            {
                // Single PID gains - already set in pid_motor structure
                // Gains can be updated via control_set_motor_pid()
                pid_set_target(&pid_motor[i], target_wheel_speeds[i]);
                float pwm_out = pid_calculate_incremental(&pid_motor[i], wheel_speed_mm_s[i]);

                // Apply yaw correction: left wheels subtract, right wheels add
                // This creates differential thrust to correct heading
                if (i == 0 || i == 1)  // FL, BL (left side)
                {
                    pwm_out -= yaw_correction;
                }
                else  // FR, BR (right side)
                {
                    pwm_out += yaw_correction;
                }

                motor_set_speed(i, (int16_t)pwm_out);
            }
        }

        vTaskDelayUntil(&last_wake_time, period);
    }
}
