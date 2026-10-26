# Part 6: Yaw Control (Heading Control)

**Duration**: 25 minutes  
**Prerequisites**: [Part 6: Multi-Level PID](63-multi-level-pid.md)

---

## Learning Objectives

After this lesson, you will understand:
- Why yaw control is needed
- How OrbiBot maintains heading
- The yaw PID implementation
- Yaw error calculation with wraparound

---

## What is Yaw Control?

### The Problem

```
When robot rotates, it needs to:
1. Reach target heading (e.g., "turn 90 degrees")
2. Maintain heading while driving (e.g., "drive straight")

Without yaw control:
- Robot drifts while driving straight
- Rotation commands overshoot or undershoot
- Navigation becomes inaccurate

With yaw control:
- Robot maintains desired heading
- Precise rotation to target angle
- Stable straight-line driving
```

### Use Cases

| Scenario | Yaw Control Action |
|----------|------------------|
| Drive straight | Maintain constant heading (0° change) |
| Turn 90° | Rotate to new heading (+90°) |
| Follow path | Continuously adjust heading to follow trajectory |
| Correct drift | Counteract unwanted rotation |

---

## Yaw Angle Representation

### What is Yaw?

```
Yaw = Rotation around vertical axis (Z-axis)
      Also called "heading" or "azimuth"

        North (0°)
            ↑
            │
   West     │     East (90°)
   (270°) ←─┼─→  (90°) or (-270°)
            │
            ↓
        South (180°) or (-180°)
```

### Angle Wraparound

```
Problem: 359° and 1° are only 2° apart,
         but mathematically 358° apart!

Solution: Normalize to [-180°, +180°]

Examples:
  0° → 0°
  90° → 90°
  180° → 180° (or -180°)
  270° → -90°
  359° → -1°
  -200° → 160°
```

### Normalization Code

```c
// Normalize angle to [-PI, PI] range
float normalize_angle(float angle)
{
    while (angle > PI_F) {
        angle -= 2.0f * PI_F;
    }
    while (angle < -PI_F) {
        angle += 2.0f * PI_F;
    }
    return angle;
}

// Alternative using fmod (floating-point modulo)
float normalize_angle_fmod(float angle)
{
    angle = fmodf(angle + PI_F, 2.0f * PI_F);
    if (angle < 0) angle += 2.0f * PI_F;
    return angle - PI_F;
}
```

---

## Yaw Error Calculation

### The Challenge

```
Target heading: 350° (-10°)
Current heading: 10°

Naive error: 350 - 10 = 340° (wrong!)
Correct error: -10 - 10 = -20° (or +340° is wrong way)

Better: -20° (turn left 20°)
```

### Correct Error Calculation

```c
float calculate_yaw_error(float target_yaw, float current_yaw)
{
    // Calculate raw difference
    float error = target_yaw - current_yaw;
    
    // Normalize to [-PI, PI]
    error = normalize_angle(error);
    
    return error;
}
```

### Examples

| Target | Current | Raw Error | Normalized | Action |
|--------|---------|-----------|------------|--------|
| 10° | 0° | 10° | 10° | Turn left 10° |
| 0° | 10° | -10° | -10° | Turn right 10° |
| 350° | 10° | 340° | -20° | Turn left 20° |
| 10° | 350° | -340° | 20° | Turn right 20° |
| 179° | -179° | 358° | -2° | Turn right 2° |
| -179° | 179° | -358° | 2° | Turn left 2° |

---

## Yaw PID Implementation

### Yaw PID Structure

```c
// From task_control.c

typedef struct {
    // From IMU (calculated by task_imu)
    float current_yaw;      // Current heading (radians)
    
    // From command or navigation
    float target_yaw;       // Desired heading (radians)
    
    // PID controller
    pid_controller_t pid_yaw;
    
    // Output (angular velocity command)
    float omega_command;    // rad/s
} yaw_control_t;

yaw_control_t yaw_control;
```

### Yaw Control Function

```c
void yaw_control_update(float dt)
{
    // 1. Get current yaw from IMU (protected read)
    taskENTER_CRITICAL();
    float current = imu_attitude.yaw;
    taskEXIT_CRITICAL();
    
    // 2. Calculate error with wraparound
    float error = calculate_yaw_error(yaw_control.target_yaw, current);
    
    // 3. Check if error is small enough to ignore
    if (fabsf(error) < YAW_ERROR_THRESHOLD) {
        error = 0.0f;  // Within tolerance, no correction needed
    }
    
    // 4. Update PID
    yaw_control.pid_yaw.target = 0.0f;  // Target is zero error
    yaw_control.omega_command = pid_update(&yaw_control.pid_yaw, error, dt);
    
    // 5. Limit angular velocity command
    if (yaw_control.omega_command > MAX_OMEGA) {
        yaw_control.omega_command = MAX_OMEGA;
    } else if (yaw_control.omega_command < -MAX_OMEGA) {
        yaw_control.omega_command = -MAX_OMEGA;
    }
}
```

---

## Integrated with Motion Control

### Two-Level Control Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Yaw Control (outer loop)               │
│  Target Heading ──→ Yaw PID ──→ Omega Command           │
│                          ↑                              │
│                          └── Current Heading (IMU)      │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────┐
│                  Motion Control (inner loop)            │
│                                                          │
│  Target Velocity (Vx, Vy) ──┐                          │
│  Omega Command ────────────┼──→ Kinematics ──→ Motors   │
│                             ↓                            │
│                         Measured Speed (encoders)       │
└─────────────────────────────────────────────────────────┘
```

### Combining Commands

```c
void task_control(void *params)
{
    // ... setup ...
    
    for (;;)
    {
        // 1. Get target from ROS command
        float vx_target = target_velocity.vx;
        float vy_target = target_velocity.vy;
        
        // 2. Yaw control (if enabled)
        float omega_target;
        if (yaw_control_enabled) {
            yaw_control_update(dt);
            omega_target = yaw_control.omega_command;
        } else {
            // Use commanded omega directly
            omega_target = target_velocity.omega;
        }
        
        // 3. Inverse kinematics
        wheel_velocity_t wheels;
        robot_velocity_t robot_vel = {
            .vx = vx_target,
            .vy = vy_target,
            .omega = omega_target
        };
        mecanum_inverse_kinematics(&robot_vel, &wheels);
        
        // 4. Motor PID control...
        
        // ... wait for next period ...
    }
}
```

---

## Use Cases

### Case 1: Drive Straight

```c
// Command: Move forward at 0.5 m/s, maintain current heading

void drive_straight(float vx)
{
    // Set target velocity
    target_velocity.vx = vx;
    target_velocity.vy = 0;
    
    // Enable yaw control
    yaw_control_enabled = 1;
    
    // Lock current heading as target
    yaw_control.target_yaw = imu_attitude.yaw;
    
    // Omega will be controlled by yaw PID, not command
}
```

### Case 2: Rotate to Heading

```c
// Command: Turn to face North (0 degrees)

void rotate_to_heading(float target_heading)
{
    // Set target heading
    yaw_control.target_yaw = target_heading;
    
    // Enable yaw control
    yaw_control_enabled = 1;
    
    // Set velocities to zero (pure rotation)
    target_velocity.vx = 0;
    target_velocity.vy = 0;
    
    // Wait until aligned
    while (fabsf(calculate_yaw_error(target_heading, imu_attitude.yaw)) > 0.05f) {
        vTaskDelay(pdMS_TO_TICKS(10));
    }
    
    printf("Aligned to heading: %.1f°\n", RAD2DEG(target_heading));
}
```

### Case 3: Arc Turn (Combined Motion)

```c
// Command: Drive forward while turning

void arc_turn(float vx, float radius)
{
    // Calculate omega from radius: omega = v / r
    float omega = vx / radius;
    
    // Disable yaw control (use commanded omega)
    yaw_control_enabled = 0;
    
    // Set velocities
    target_velocity.vx = vx;
    target_velocity.vy = 0;
    target_velocity.omega = omega;
}
```

---

## Yaw PID Tuning

### Different from Motor PID

| Aspect | Motor PID | Yaw PID |
|--------|-----------|---------|
| Control variable | Wheel speed | Heading angle |
| Time constant | Fast (~0.1s) | Slower (~0.5s) |
| Noise | Moderate | Low (filtered IMU) |
| Gains | Kp ~0.8 | Kp ~2.0 |
| | Ki ~0.06 | Ki ~0.0 (optional) |
| | Kd ~0.5 | Kd ~0.2 |

### Recommended Values

```c
// Yaw PID gains
#define YAW_PID_KP  2.0f   // Higher for crisp heading control
#define YAW_PID_KI  0.0f   // Usually not needed for yaw
#define YAW_PID_KD  0.2f   // Moderate damping

#define YAW_ERROR_THRESHOLD  0.02f  // ~1 degree (radians)
#define MAX_OMEGA  2.0f  // rad/s (maximum rotation rate)
```

### Tuning Tips

```
1. Start with Kp only
   - Increase until slight oscillation
   - Back off 20%

2. Add Kd if needed
   - Reduces overshoot
   - Start with Kd = Kp / 10

3. Ki rarely needed
   - Yaw has no steady-state error source
   - Can cause windup during rotations
```

---

## Exercise: Calculate Yaw Correction

**Given**:
- Target heading: 45° (NE direction)
- Current heading: 30°
- Kp = 2.0

**Calculate**:
1. Yaw error (in radians)
2. Omega command (rad/s)

**Answer**:

<details>
<summary>Click for answer</summary>

```
1. Convert to radians:
   Target: 45° × (π/180) = 0.785 rad
   Current: 30° × (π/180) = 0.524 rad

2. Calculate error:
   Error = Target - Current
   Error = 0.785 - 0.524 = 0.261 rad (~15°)

3. No wraparound needed (error < 180°)

4. Calculate omega command:
   Omega = Kp × Error
   Omega = 2.0 × 0.261 = 0.522 rad/s

Result: Robot should rotate at 0.522 rad/s to align with target.
At this rate, it would take ~0.5s to reach target (assuming constant rate).
```

</details>

---

## Summary

- **Yaw control**: Maintains or achieves target heading
- **Wraparound**: Critical for correct error calculation
- **Two-level control**: Yaw PID → Omega command → Motor control
- **Use cases**: Straight driving, precise rotation, path following
- **Tuning**: Higher Kp than motor PID, usually no Ki

---

## Next Lesson

[02 - IMU Sensors](../localization/02-imu-sensors.md) - Introduction to IMU sensors

---

*OrbiBot Firmware Study Guide*  
*Part 6 of 10*