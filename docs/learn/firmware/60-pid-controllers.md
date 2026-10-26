# Part 6: PID Controllers

**Duration**: 35 minutes  
**Prerequisites**: [Part 5: Forward Kinematics](52-forward-kinematics.md)

---

## Learning Objectives

After this lesson, you will understand:
- What PID control is and why we use it
- Proportional, Integral, and Derivative terms
- How PID works for motor speed control
- Discrete PID implementation
- PID tuning basics

---

## What is PID Control?

**PID** = Proportional + Integral + Derivative

### The Problem

```
Motor Control Challenge:
- We want: Wheel speed = 0.5 m/s
- We send: PWM = 1000 (guess)
- Result: Speed = 0.3 m/s (too slow!)

Why not just add more PWM?
- Different loads need different PWM
- Battery voltage changes
- Friction varies

We need a system that AUTOMATICALLY adjusts!
```

### The Solution: Feedback Control

```
┌─────────────────────────────────────────────────────────┐
│              Closed-Loop Control System                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│   Target      Error        Controller      Plant         │
│   Speed   ┌─────────┐    ┌─────────┐   ┌─────────┐     │
│   0.5 ───→│  +    - │───→│   PID   │──→│  Motor  │     │
│  (m/s)    │         │    │         │    │         │     │
│           │    ↑    │    │  Kp,Ki, │    │  PWM    │     │
│           │    │    │    │    Kd   │    │  Power  │     │
│           │  Measured  │   │         │    │         │     │
│           │  Speed    │    └─────────┘    └────┬────┘    │
│           │  0.48 m/s │                        │         │
│           │           │←───────────────────────┘         │
│           └─────────┘         Sensor                     │
│                              (Encoder)                   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## PID Components

### 1. Proportional Term (P)

**Responds to current error**

```
Error = Target - Measured
Output = Kp × Error

Example:
  Target speed = 0.5 m/s
  Measured speed = 0.3 m/s
  Error = 0.5 - 0.3 = 0.2 m/s
  
  If Kp = 1000:
  Output = 1000 × 0.2 = 200 PWM
  
  Higher error → Higher output
```

**Visual Response**:

```
Error:    ████              (large error)
          ↓
P-term:   ████████          (large response)
          
Error:        ██            (small error)
          ↓
P-term:       ████          (small response)
```

**Problem with P-only**:
- Never reaches target perfectly (steady-state error)
- Oscillates if Kp too high

---

### 2. Integral Term (I)

**Responds to accumulated error over time**

```
Integral += Error × dt
Output = Ki × Integral

Example:
  Error has been 0.1 m/s for 1 second
  Integral = 0.1 × 1 = 0.1
  Ki = 500
  I-output = 500 × 0.1 = 50 PWM
  
  Persistent error → Builds up over time
```

**Purpose**: Eliminate steady-state error

```
Scenario: Robot going uphill
- P-term: Output = 800 PWM, but need 1000
- Speed stabilizes at 0.45 m/s (not 0.5)
- I-term: Error = 0.05, keeps accumulating
- After 2 seconds: I-output = 100, total = 900
- After 4 seconds: I-output = 200, total = 1000
- Robot reaches target speed!
```

**Anti-Windup**: Limit integral to prevent excessive buildup

```c
// Prevent integral windup
if (integral > MAX_INTEGRAL) integral = MAX_INTEGRAL;
if (integral < -MAX_INTEGRAL) integral = -MIN_INTEGRAL;
```

---

### 3. Derivative Term (D)

**Responds to rate of change of error**

```
Derivative = (Error - PreviousError) / dt
Output = Kd × Derivative

Example:
  Error was 0.2, now 0.1 (getting better)
  Change = 0.1 - 0.2 = -0.1
  dt = 0.01s (100Hz)
  Derivative = -0.1 / 0.01 = -10
  
  Kd = 10
  D-output = 10 × -10 = -100 PWM
  
  Fast improvement → Reduce output (braking effect)
```

**Purpose**: Reduce overshoot and oscillation

```
Without D-term:
  Target ───────┐
                ↓
  Speed    ╱╲      ╱╲      ╱╲
          ╱  ╲    ╱  ╲    ╱  ╲   (oscillates)
         ╱    ╲  ╱    ╲  ╱    ╲

With D-term:
  Target ───────┐
                ↓
  Speed    ╱──────╲
                ╲___╲_____    (smooth, no overshoot)
```

---

## Complete PID Formula

### Continuous Form (Theory)

```
u(t) = Kp × e(t) + Ki × ∫e(t)dt + Kd × de(t)/dt

Where:
  u(t) = Control output (PWM)
  e(t) = Error (target - measured)
  Kp   = Proportional gain
  Ki   = Integral gain  
  Kd   = Derivative gain
```

### Discrete Form (Firmware)

```c
// Runs at 100Hz (dt = 0.01s)
float pid_calculate(pid_controller_t *pid, float measured) {
    // 1. Calculate error
    float error = pid->target - measured;
    
    // 2. Proportional term
    float p_term = pid->kp * error;
    
    // 3. Integral term
    pid->integral += error * dt;
    // Anti-windup
    if (pid->integral > pid->max_integral) 
        pid->integral = pid->max_integral;
    if (pid->integral < -pid->max_integral) 
        pid->integral = -pid->max_integral;
    float i_term = pid->ki * pid->integral;
    
    // 4. Derivative term
    float derivative = (error - pid->prev_error) / dt;
    float d_term = pid->kd * derivative;
    pid->prev_error = error;
    
    // 5. Sum terms
    float output = p_term + i_term + d_term;
    
    // 6. Limit output
    if (output > pid->max_output) output = pid->max_output;
    if (output < -pid->max_output) output = -pid->max_output;
    
    return output;
}
```

---

## PID for Motor Control in OrbiBot

### The Control Loop

```
Each 10ms (100Hz):

┌─────────────────────────────────────────────────────────┐
│  1. Read encoder → current speed (measured)             │
│  2. Calculate error = target - measured                 │
│  3. PID calculation → PWM output                        │
│  4. Send PWM to motor driver                            │
└─────────────────────────────────────────────────────────┘
```

### Code Implementation

```c
// From: src/control/pid_controller.c

typedef struct {
    float kp, ki, kd;           // Gains
    float target;               // Desired value
    float integral;             // Accumulated error
    float prev_error;           // Previous error
    float max_output;           // Output limit
    float max_integral;         // Anti-windup limit
} pid_controller_t;

void pid_init(pid_controller_t *pid, float kp, float ki, float kd, 
              float max_output) {
    pid->kp = kp;
    pid->ki = ki;
    pid->kd = kd;
    pid->target = 0;
    pid->integral = 0;
    pid->prev_error = 0;
    pid->max_output = max_output;
    pid->max_integral = max_output * 0.5f;  // Conservative
}

float pid_update(pid_controller_t *pid, float measured, float dt) {
    // Calculate error
    float error = pid->target - measured;
    
    // P term
    float p = pid->kp * error;
    
    // I term (with anti-windup)
    pid->integral += error * dt;
    if (pid->integral > pid->max_integral) 
        pid->integral = pid->max_integral;
    if (pid->integral < -pid->max_integral) 
        pid->integral = -pid->max_integral;
    float i = pid->ki * pid->integral;
    
    // D term
    float d = pid->kd * (error - pid->prev_error) / dt;
    pid->prev_error = error;
    
    // Calculate output
    float output = p + i + d;
    
    // Clamp output
    if (output > pid->max_output) output = pid->max_output;
    if (output < -pid->max_output) output = -pid->max_output;
    
    return output;
}
```

### Multi-Level PID (OrbiBot Feature)

Different speeds need different PID gains:

```c
// Low speed: High Kp for crisp response
#define PID_KP_LOW  1.2f
#define PID_KI_LOW  0.04f
#define PID_KD_LOW  0.6f

// Medium speed: Balanced
#define PID_KP_MED  0.8f
#define PID_KI_MED  0.06f
#define PID_KD_MED  0.5f

// High speed: Lower Kp to reduce oscillation
#define PID_KP_HIGH 0.5f
#define PID_KI_HIGH 0.08f
#define PID_KD_HIGH 0.4f

// Interpolate based on current speed
pid_gains_t pid_get_gains_for_speed(float speed) {
    if (speed < 50) return low_speed_gains;
    if (speed < 200) return med_speed_gains;
    return high_speed_gains;
}
```

---

## PID Tuning Basics

### Manual Tuning Method (Ziegler-Nichols)

```
Step 1: Set Ki = 0, Kd = 0
        Increase Kp until system oscillates
        This is Kp_critical

Step 2: Set Kp = 0.6 × Kp_critical
        Ki = 2 × Kp / Period
        Kd = Kp × Period / 8

Step 3: Fine-tune by observation
```

### Tuning Guidelines

| Symptom | Cause | Fix |
|---------|-------|-----|
| Slow response | Kp too low | Increase Kp |
| Oscillation | Kp too high | Decrease Kp |
| Steady-state error | Ki too low | Increase Ki |
| Integral windup | Ki too high | Decrease Ki, add anti-windup |
| Overshoot | Kd too low | Increase Kd |
| Noisy output | Kd too high | Decrease Kd |

### OrbiBot Default Gains

```c
// Tuned for JGB37-520 motors with AM2857 drivers
#define DEFAULT_KP  0.8f
#define DEFAULT_KI  0.06f
#define DEFAULT_KD  0.5f

// At 100Hz control rate
// Max integral: 4000 (prevents excessive windup)
// Max output: ±3600 (PWM range)
```

---

## Exercise: PID Calculation

**Given**:
- Target speed = 1.0 m/s
- Current speed = 0.6 m/s
- Previous error = 0.5 m/s (from last cycle)
- dt = 0.01s (100Hz)
- Kp = 0.8, Ki = 0.06, Kd = 0.5
- Current integral = 0.02

**Calculate**:
1. Error
2. P-term
3. I-term (after update)
4. D-term
5. Total output

**Answer**:

<details>
<summary>Click for answer</summary>

```
1. Error = Target - Measured
        = 1.0 - 0.6
        = 0.4 m/s

2. P-term = Kp × Error
         = 0.8 × 0.4
         = 0.32

3. I-term:
   Integral += Error × dt
            = 0.02 + (0.4 × 0.01)
            = 0.02 + 0.004
            = 0.024
   
   I-term = Ki × Integral
          = 0.06 × 0.024
          = 0.00144

4. D-term = Kd × (Error - Previous) / dt
          = 0.5 × (0.4 - 0.5) / 0.01
          = 0.5 × (-0.1) / 0.01
          = 0.5 × (-10)
          = -5.0

5. Output = P + I + D
         = 0.32 + 0.00144 + (-5.0)
         = -4.678

(Note: In practice, output would be clamped to valid PWM range)
```

</details>

---

## Summary

- **PID** = Proportional + Integral + Derivative
- **P-term**: Responds to current error
- **I-term**: Eliminates steady-state error (accumulated)
- **D-term**: Reduces overshoot (rate of change)
- **Discrete PID**: Runs at fixed rate (100Hz in OrbiBot)
- **Multi-level**: Different gains for different speeds
- **Anti-windup**: Prevents integral from growing too large

---

## Next Lesson

[Part 6: PID Tuning Methods](61-pid-tuning.md) - Advanced tuning methods and practical tips

---

*OrbiBot Firmware Study Guide*  
*Part 6 of 10*