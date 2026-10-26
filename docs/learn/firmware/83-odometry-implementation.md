# Part 8: Odometry Implementation

**Duration**: 25 minutes  
**Prerequisites**: [Part 8: Odometry Mathematics](82-odometry-math.md)

---

## Learning Objectives

After this lesson, you will understand:
- How odometry is implemented in OrbiBot firmware
- The data structures used
- Integration with the 100Hz control loop
- How to reset and access odometry data

---

## Data Structures

### Odometry State

```c
// From control/odometry.h

typedef struct {
    // Position (meters, global frame)
    float x;        // X coordinate
    float y;        // Y coordinate
    float theta;    // Heading (radians)
    
    // Velocity (m/s, robot frame)
    float vx;       // Forward velocity
    float vy;       // Lateral velocity
    float omega;    // Angular velocity
    
    // Timestamp
    uint32_t last_update_tick;
} odometry_t;

// Global odometry instance
odometry_t robot_odom;
```

### Initialization

```c
void odometry_init(void)
{
    robot_odom.x = 0.0f;
    robot_odom.y = 0.0f;
    robot_odom.theta = 0.0f;
    robot_odom.vx = 0.0f;
    robot_odom.vy = 0.0f;
    robot_odom.omega = 0.0f;
    robot_odom.last_update_tick = xTaskGetTickCount();
}
```

---

## Update Function

### The Core Implementation

```c
// Called from task_control at 100Hz

void odometry_update(const wheel_velocity_t *wheels, float dt)
{
    // 1. Calculate robot velocity from wheel speeds (forward kinematics)
    robot_velocity_t vel;
    mecanum_forward_kinematics(wheels, &vel);
    
    // Store velocity for reporting
    robot_odom.vx = vel.vx;
    robot_odom.vy = vel.vy;
    robot_odom.omega = vel.omega;
    
    // 2. Calculate displacement in robot frame
    float dx_robot = vel.vx * dt;
    float dy_robot = vel.vy * dt;
    float dtheta = vel.omega * dt;
    
    // 3. Transform to global frame using current heading
    float cos_theta = cosf(robot_odom.theta);
    float sin_theta = sinf(robot_odom.theta);
    
    float dx = dx_robot * cos_theta - dy_robot * sin_theta;
    float dy = dx_robot * sin_theta + dy_robot * cos_theta;
    
    // 4. Update position (critical section for thread safety)
    taskENTER_CRITICAL();
    robot_odom.x += dx;
    robot_odom.y += dy;
    robot_odom.theta += dtheta;
    
    // 5. Normalize angle to [-PI, PI]
    while (robot_odom.theta > PI_F) {
        robot_odom.theta -= 2.0f * PI_F;
    }
    while (robot_odom.theta < -PI_F) {
        robot_odom.theta += 2.0f * PI_F;
    }
    taskEXIT_CRITICAL();
    
    // Update timestamp
    robot_odom.last_update_tick = xTaskGetTickCount();
}
```

---

## Integration with Control Task

### Where Odometry Fits

```c
// From task_control.c

void task_control(void *params)
{
    TickType_t last_wake = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(10);  // 100Hz
    int32_t enc_prev[4] = {0};
    
    for (;;)
    {
        // 1. Read encoders
        int32_t enc_now[4];
        for (int i = 0; i < 4; i++) {
            enc_now[i] = encoder_get_count(i);
        }
        
        // 2. Calculate wheel velocities
        wheel_velocity_t wheels;
        for (int i = 0; i < 4; i++) {
            int32_t delta = enc_now[i] - enc_prev[i];
            enc_prev[i] = enc_now[i];
            wheels.v[i] = delta * ENCODER_TO_MM_PER_MS * 1000.0f;  // m/s
        }
        
        // 3. UPDATE ODOMETRY
        odometry_update(&wheels, 0.01f);
        
        // 4. PID control (rest of control task...)
        // ...
        
        vTaskDelayUntil(&last_wake, period);
    }
}
```

---

## Accessing Odometry Data

### Thread-Safe Read

```c
// For other tasks to read odometry safely

void odometry_get_position(float *x, float *y, float *theta)
{
    taskENTER_CRITICAL();
    *x = robot_odom.x;
    *y = robot_odom.y;
    *theta = robot_odom.theta;
    taskEXIT_CRITICAL();
}

void odometry_get_velocity(float *vx, float *vy, float *omega)
{
    taskENTER_CRITICAL();
    *vx = robot_odom.vx;
    *vy = robot_odom.vy;
    *omega = robot_odom.omega;
    taskEXIT_CRITICAL();
}
```

### For Communication Task

```c
// Send odometry data to ROS

void protocol_send_odometry(void)
{
    float x, y, theta, vx, vy, omega;
    
    // Read current state
    odometry_get_position(&x, &y, &theta);
    odometry_get_velocity(&vx, &vy, &omega);
    
    // Convert to mm and mrad for protocol
    int32_t x_mm = (int32_t)(x * 1000.0f);
    int32_t y_mm = (int32_t)(y * 1000.0f);
    int32_t theta_mrad = (int32_t)(theta * 1000.0f);
    int16_t vx_mm_s = (int16_t)(vx * 1000.0f);
    int16_t vy_mm_s = (int16_t)(vy * 1000.0f);
    int16_t omega_mrad_s = (int16_t)(omega * 1000.0f);
    
    // Build and send packet...
}
```

---

## Reset Function

### When to Reset

- Robot picked up and moved manually
- Starting a new navigation task
- After calibration
- When position is known (e.g., at charging station)

### Implementation

```c
void odometry_reset(void)
{
    taskENTER_CRITICAL();
    robot_odom.x = 0.0f;
    robot_odom.y = 0.0f;
    robot_odom.theta = 0.0f;
    robot_odom.vx = 0.0f;
    robot_odom.vy = 0.0f;
    robot_odom.omega = 0.0f;
    taskEXIT_CRITICAL();
    
    DEBUG_INFO("Odometry reset to (0, 0, 0)\n");
}

// Can also reset to specific position
void odometry_set_position(float x, float y, float theta)
{
    taskENTER_CRITICAL();
    robot_odom.x = x;
    robot_odom.y = y;
    robot_odom.theta = theta;
    taskEXIT_CRITICAL();
    
    DEBUG_INFO("Odometry set to (%.2f, %.2f, %.2f)\n", x, y, theta);
}
```

---

## Example: Complete Odometry Session

```
Session Start:
  Reset odometry to (0, 0, 0)
  
Drive forward 1 meter:
  Commands: vx=0.3 m/s, vy=0, omega=0
  After 3.33 seconds:
    Odometry reads: x≈1.0, y≈0, theta=0
  
Turn 90° in place:
  Commands: vx=0, vy=0, omega=0.5 rad/s
  After 3.14 seconds:
    Odometry reads: x≈1.0, y≈0, theta≈1.57 (90°)
  
Drive forward 1 meter:
  Commands: vx=0.3 m/s, vy=0, omega=0
  After 3.33 seconds:
    Odometry reads: x≈1.0, y≈1.0, theta≈1.57
  
Return to start:
  Navigate back using odometry feedback
  Final position: x≈0, y≈0, theta≈0
```

---

## Summary

- **Update rate**: 100Hz (with control task)
- **Thread safety**: Critical sections for shared data
- **Integration**: Simple Euler method
- **Access**: Protected read functions
- **Reset**: Can reset to origin or specific position

---

## Next Lesson

[Part 8: Odometry Errors and Drift](84-odometry-errors.md) - Understanding and handling odometry errors

---

*OrbiBot Firmware Study Guide*  
*Part 8 of 10*