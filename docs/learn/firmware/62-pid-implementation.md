---
title: "Part 6: PID Implementation in Firmware"
type: learn
area: firmware
package: orbibot_rosmaster_firmware
duration: "25 minutes"
tags:
  - learn
  - firmware
---

# Part 6: PID Implementation in Firmware

**Duration**: 25 minutes  
**Prerequisites**: [[61-pid-tuning]]

---

## Learning Objectives

After this lesson, you will understand:
- How PID is implemented in OrbiBot firmware
- The 100Hz control loop structure
- Anti-windup implementation
- Output limiting and saturation

---

## PID Data Structure

### From `pid_controller.h`

```c
typedef struct {
    // Gains
    float kp;           // Proportional gain
    float ki;           // Integral gain
    float kd;           // Derivative gain
    
    // Setpoint and measurement
    float target;       // Desired value
    float measured;     // Current value
    
    // State variables
    float error;        // Current error
    float prev_error;   // Previous error (for derivative)
    float integral;     // Accumulated error
    
    // Limits
    float max_output;   // Maximum output (e.g., 3600 for PWM)
    float max_integral; // Anti-windup limit
    
    // Output
    float output;       // Calculated control output
} pid_controller_t;
```

---

## PID Initialization

### Setting Up a PID Controller

```c
// From task_control.c - Initialize 4 motor PIDs

pid_controller_t pid_motor[4];  // One per motor

void pid_init_all(void)
{
    for (int i = 0; i < 4; i++) {
        pid_init(&pid_motor[i], PID_KP, PID_KI, PID_KD, 3600);
    }
}

void pid_init(pid_controller_t *pid, float kp, float ki, float kd, 
              float max_output)
{
    // Set gains
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    
    // Initialize state
    pid->target = 0.0f;
    pid->measured = 0.0f;
    pid->error = 0.0f;
    pid->prev_error = 0.0f;
    pid->integral = 0.0f;
    
    // Set limits
    pid->max_output = max_output;
    pid->max_integral = max_output * 0.5f;  // Conservative anti-windup
    
    // Initial output
    pid->output = 0.0f;
}
```

---

## PID Update Function

### The Core Algorithm

```c
// Called at 100Hz (every 10ms)

float pid_update(pid_controller_t *pid, float measured, float dt)
{
    // Store measurement
    pid->measured = measured;
    
    // 1. Calculate error
    pid->error = pid->target - measured;
    
    // 2. Proportional term
    float p_term = pid->kp * pid->error;
    
    // 3. Integral term with anti-windup
    pid->integral += pid->error * dt;
    
    // Anti-windup: Clamp integral
    if (pid->integral > pid->max_integral) {
        pid->integral = pid->max_integral;
    } else if (pid->integral < -pid->max_integral) {
        pid->integral = -pid->max_integral;
    }
    
    float i_term = pid->ki * pid->integral;
    
    // 4. Derivative term
    float derivative = (pid->error - pid->prev_error) / dt;
    float d_term = pid->kd * derivative;
    
    // Save error for next iteration
    pid->prev_error = pid->error;
    
    // 5. Sum terms
    float output = p_term + i_term + d_term;
    
    // 6. Output limiting (saturation)
    if (output > pid->max_output) {
        output = pid->max_output;
    } else if (output < -pid->max_output) {
        output = -pid->max_output;
    }
    
    pid->output = output;
    return output;
}
```

---

## The 100Hz Control Loop

### Control Task Structure

```c
// From task_control.c

void task_control(void *params)
{
    // Timing setup
    TickType_t last_wake = xTaskGetTickCount();
    const TickType_t period = pdMS_TO_TICKS(10);  // 10ms = 100Hz
    
    // Encoder deltas
    int32_t enc_prev[4] = {0};
    int32_t enc_now[4];
    
    for (;;)
    {
        // 1. Read current encoder counts
        for (int i = 0; i < 4; i++) {
            enc_now[i] = encoder_get_count(i);
        }
        
        // 2. Calculate wheel speeds (mm/s)
        float wheel_speeds[4];
        for (int i = 0; i < 4; i++) {
            int32_t delta = enc_now[i] - enc_prev[i];
            enc_prev[i] = enc_now[i];
            
            // Convert delta counts to mm/s
            // delta counts per 10ms → mm/s
            wheel_speeds[i] = delta * ENCODER_TO_MM_PER_MS;
        }
        
        // 3. Get target wheel speeds (from ROS command)
        float target_speeds[4];
        get_target_wheel_speeds(target_speeds);  // Critical section
        
        // 4. PID control for each motor
        for (int i = 0; i < 4; i++) {
            // Set target
            pid_motor[i].target = target_speeds[i];
            
            // Calculate PID
            float pwm = pid_update(&pid_motor[i], wheel_speeds[i], 0.01f);
            
            // Send to motor
            motor_set_pwm(i, (int16_t)pwm);
        }
        
        // 5. Wait for next period
        vTaskDelayUntil(&last_wake, period);
    }
}
```

---

## Anti-Windup Explained

### What is Integral Windup?

```
Scenario: Robot stuck against wall
- Motor commanded to move forward
- Wheels can't move (blocked)
- Error stays large
- Integral keeps growing (winding up)
- When unblocked: HUGE overshoot!

Without anti-windup:
Integral: 0 → 100 → 200 → 300 → ... (keeps growing)
When freed: Output = Kp×error + Ki×300 → massive!

With anti-windup:
Integral: 0 → 100 → 150 → 150 → 150 (clamped)
When freed: Output = Kp×error + Ki×150 → manageable
```

### Implementation Details

```c
// Clamp integral to prevent windup
if (pid->integral > pid->max_integral) {
    pid->integral = pid->max_integral;
} else if (pid->integral < -pid->max_integral) {
    pid->integral = -pid->max_integral;
}
```

**Setting max_integral**:
```c
// Conservative: 50% of max output
pid->max_integral = pid->max_output * 0.5f;

// More aggressive: 100% of max output
pid->max_integral = pid->max_output;

// Very conservative: 25% of max output
pid->max_integral = pid->max_output * 0.25f;
```

---

## Output Limiting

### Why Limit Output?

```c
// PWM can only go 0-3600 (for AM2857 driver)
// Negative for reverse

// Without limiting:
// Output could be 50000 (impossible!)
// Causes overflow/wraparound

// With limiting:
// Output clamped to 3600 (valid)
```

### Limiting Code

```c
// Saturate output to valid range
if (output > pid->max_output) {
    output = pid->max_output;
} else if (output < -pid->max_output) {
    output = -pid->max_output;
}
```

---

## Complete Example Walkthrough

### Scenario: Motor Speed Control

**Initial conditions**:
- Target: 500 mm/s
- Current: 0 mm/s
- Kp=0.8, Ki=0.06, Kd=0.5
- dt = 0.01s (100Hz)

**First iteration (t=0)**:
```
measured = 0
target = 500
error = 500 - 0 = 500

P = 0.8 × 500 = 400
I = 0 + (0.06 × 500 × 0.01) = 0.3
D = 0.5 × (500 - 0) / 0.01 = 25000 (clamped!)

Wait, that's too high. Let's recalculate more carefully...

Actually D term:
derivative = (error - prev_error) / dt
           = (500 - 0) / 0.01 = 50000

D = 0.5 × 50000 = 25000 (way too high!)

Problem: Initial derivative spike

Solution: Use filtered derivative or limit change
```

### Improved D Term

```c
// Option 1: Limit derivative
float max_derivative = 1000.0f;  // Limit to reasonable value
if (derivative > max_derivative) derivative = max_derivative;
if (derivative < -max_derivative) derivative = -max_derivative;

// Option 2: Use filtered derivative (low-pass filter)
static float filtered_derivative = 0;
float alpha = 0.1f;  // Filter coefficient
filtered_derivative = alpha * derivative + (1 - alpha) * filtered_derivative;
float d_term = pid->kd * filtered_derivative;
```

---

## Tuning at Runtime

### Updating Gains Without Restart

```c
// From command handler (SET_MOTOR_PID command)

void control_set_pid_gains(float kp, float ki, float kd)
{
    for (int i = 0; i < 4; i++) {
        taskENTER_CRITICAL();
        pid_motor[i].kp = kp;
        pid_motor[i].ki = ki;
        pid_motor[i].kd = kd;
        
        // Reset integral to prevent jump
        pid_motor[i].integral = 0;
        taskEXIT_CRITICAL();
    }
}
```

**Why reset integral?**
```
Old Ki = 0.06, integral = 100 → I-term = 6
New Ki = 0.08, integral = 100 → I-term = 8 (sudden jump!)

Better: Reset integral to 0 when changing Ki
```

---

## Debugging PID

### Adding Debug Output

```c
// Enable with compile flag
#ifdef PID_DEBUG
void pid_print_debug(pid_controller_t *pid, int motor_id)
{
    printf("Motor %d: target=%.1f, meas=%.1f, err=%.1f, "
           "P=%.1f, I=%.1f, D=%.1f, out=%.1f\n",
           motor_id,
           pid->target,
           pid->measured,
           pid->error,
           pid->kp * pid->error,           // P-term
           pid->ki * pid->integral,        // I-term
           pid->kd * (pid->error - pid->prev_error) / 0.01f,  // D-term
           pid->output);
}
#endif
```

---

## Summary

- **PID structure**: Holds gains, state, and limits
- **Update function**: Called at 100Hz, calculates output
- **Anti-windup**: Clamps integral to prevent excessive buildup
- **Output limiting**: Ensures valid PWM range
- **100Hz loop**: Precise timing with vTaskDelayUntil

---

## Next Lesson

[[63-multi-level-pid]] - Different gains for different speeds

---

*OrbiBot Firmware Study Guide*  
*Part 6 of 10*