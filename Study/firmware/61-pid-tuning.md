# Part 6: PID Tuning Methods

**Duration**: 30 minutes  
**Prerequisites**: [60-pid-controllers.md](60-pid-controllers.md)

---

## Learning Objectives

After this lesson, you will understand:
- Manual tuning method (Ziegler-Nichols)
- How to recognize tuning problems
- Step-by-step tuning procedure
- Practical tuning tips for motors

---

## Why Tune PID?

### Default Gains May Not Work

```
Different systems need different PID gains:
- Small robot → Low inertia → Can use aggressive gains
- Heavy robot → High inertia → Needs conservative gains
- Fast motors → Responsive → Different Kp than slow motors
- Gear ratio affects → Higher gear = more responsive

OrbiBot default gains work for JGB37-520 motors,
but you might need to tune for:
- Different floor surfaces
- Different loads
- Different battery voltages
```

---

## Ziegler-Nichols Tuning Method

### Overview

A systematic method to find good starting gains.

### Step 1: Find Critical Gain (Kp_crit)

```
1. Set Ki = 0, Kd = 0
2. Start with small Kp (e.g., 0.1)
3. Command a step change (e.g., 0 to 0.5 m/s)
4. Observe response
5. Increase Kp until system oscillates continuously
6. This Kp is Kp_critical
7. Measure oscillation period (P_crit)
```

**Visual**:
```
Kp too low:         Kp good:           Kp critical:
│                   │                  ╱╲    ╱╲
│    ╱──╲          │      ╱──╲       ╱  ╲  ╱  ╲  (oscillates
│   ╱    ╲         │     ╱    ╲     ╱    ╲╱    ╲  forever)
│  ╱      ╲____    │    ╱      ╲___╱
│_╱                │___╱
Slow response      Good response      Oscillation
```

### Step 2: Calculate Initial Gains

Using Kp_crit and P_crit:

| Controller Type | Kp | Ki | Kd |
|-----------------|----|----|----|
| P-only | 0.5 × Kp_crit | 0 | 0 |
| PI | 0.45 × Kp_crit | 0.54 × Kp_crit / P_crit | 0 |
| **PID** | **0.6 × Kp_crit** | **1.2 × Kp_crit / P_crit** | **0.075 × Kp_crit × P_crit** |

---

## Practical Tuning for OrbiBot

### Step-by-Step Procedure

#### Step 1: Preparation

```c
// In orbibot_config.h, start with:
#define PID_KP  0.1f   // Very low
#define PID_KI  0.0f   // Zero
#define PID_KD  0.0f   // Zero

// Build and upload firmware
```

#### Step 2: Find Kp Critical

```bash
# Use test script to command velocity step
python3 test_pid_tuning.py --step 0.5

# Or manually via ROS2:
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.5}, angular: {z: 0.0}}"
```

**Observe**:
- If response is slow and sluggish → Increase Kp
- If response oscillates → You've found Kp_crit

**Example**:
```
Test results:
- Kp = 0.5: Good response, no oscillation
- Kp = 1.0: Slight overshoot
- Kp = 1.5: Oscillates with period ~0.2s

Kp_crit = 1.5
P_crit = 0.2s
```

#### Step 3: Calculate Gains

```
Kp = 0.6 × 1.5 = 0.9
Ki = 1.2 × 1.5 / 0.2 = 9.0 (too high! Use lower)
Kd = 0.075 × 1.5 × 0.2 = 0.0225 (too low)

Reality check for motors:
- Ki is usually 1/10 to 1/20 of Kp
- Kd is usually 1/2 to 1× Kp

Adjusted values:
Kp = 0.9
Ki = 0.06  (empirically determined)
Kd = 0.5   (empirically determined)
```

#### Step 4: Fine-Tune

```
Testing Kp = 0.9, Ki = 0.06, Kd = 0.5:

If oscillating:       → Decrease Kp by 10%
If slow response:     → Increase Kp by 10%
If steady-state error:→ Increase Ki
If overshoot:         → Increase Kd

Iterate until satisfied!
```

---

## Recognizing Tuning Problems

### Visual Guide

| Problem | Cause | Solution |
|---------|-------|----------|
| **Slow response** | Kp too low | Increase Kp |
| **Oscillation** | Kp too high | Decrease Kp |
| **Offset/steady-state error** | Ki too low | Increase Ki |
| **Integral windup** | Ki too high | Decrease Ki, add anti-windup |
| **Overshoot** | Kd too low | Increase Kd |
| **Jittery/noisy** | Kd too high | Decrease Kd |

### Example Responses

```
1. GOOD RESPONSE:
   Target ───────┐
                 ↓
   Actual   ╱──────╲
                 ╲___╲_____
   Fast, no overshoot, settles quickly

2. Kp TOO LOW:
   Target ───────┐
                 ↓
   Actual   ╱╲______________
           Slow rise, never reaches target
   
3. Kp TOO HIGH:
   Target ───────┐
                 ↓
   Actual   ╱╲      ╱╲      ╱╲
           ╱  ╲    ╱  ╲    ╱  ╲   (oscillates)
   
4. Ki TOO LOW:
   Target ───────┐
                 ↓
   Actual   ╱╲________
                ↑ Offset remains
   
5. Ki TOO HIGH (WINDUP):
   Target ───────┐
                 ↓
   Actual   ╱──────────╲
                     Huge overshoot
   
6. Kd TOO LOW:
   Target ───────┐
                 ↓
   Actual   ╱──╲
              ╲__╲___ (overshoots)
   
7. Kd TOO HIGH:
   Target ───────┐
                 ↓
   Actual   ╱╲╱╲╱╲╱╲╱╲ (jittery)
```

---

## OrbiBot-Specific Tuning

### Motor Characteristics

| Parameter | Value | Implication |
|-----------|-------|-------------|
| Motor type | JGB37-520 | Brushed DC, 333 RPM |
| Gear ratio | 30:1 | High torque, responsive |
| Encoder PPR | 1320 | Good resolution |
| Driver | AM2857 | PWM controlled |

### Recommended Starting Values

```c
// For JGB37-520 motors at 12V
#define PID_KP_START  0.8f
#define PID_KI_START  0.06f
#define PID_KD_START  0.5f

// These work for most cases
// Fine-tune from here
```

### Tuning for Different Speeds

OrbiBot uses **multi-level PID**:

```c
// Low speed (0-50 mm/s): Needs more Kp to overcome friction
#define PID_KP_LOW  1.2f
#define PID_KI_LOW  0.04f
#define PID_KD_LOW  0.6f

// Medium speed (50-200 mm/s): Balanced
#define PID_KP_MED  0.8f
#define PID_KI_MED  0.06f
#define PID_KD_MED  0.5f

// High speed (200+ mm/s): Less Kp to prevent oscillation
#define PID_KP_HIGH 0.5f
#define PID_KI_HIGH 0.08f
#define PID_KD_HIGH 0.4f
```

---

## Testing Procedures

### Step Response Test

```python
# test_step_response.py
import serial
import time

# Connect to robot
ser = serial.Serial('/dev/ttyUSB0', 115200)

# Enable auto-report
send_auto_report(ser, enable=True)

# Send step command: 0 → 0.5 m/s
send_motion(ser, vx=0.5, vy=0, vz=0)

# Record response
data = []
start_time = time.time()
while time.time() - start_time < 2.0:  # 2 seconds
    packet = ser.read(12)
    if is_speed_report(packet):
        vx, vy, vz, battery = parse_speed(packet)
        data.append((time.time() - start_time, vx))
        print(f"Time: {t:.2f}s, Vx: {vx} mm/s")

# Plot response
plot_response(data)
```

### Expected Good Response

```
Time (s) | Speed (mm/s) | Assessment
---------|--------------|-----------
0.00     | 0            | Start
0.05     | 200          | Rising
0.10     | 400          | Rising
0.15     | 480          | Approaching
0.20     | 500          | At target
0.25     | 500          | Stable
0.30     | 500          | Stable

Settles within 0.2s, no overshoot = Good!
```

---

## Common Mistakes

### Mistake 1: Too Aggressive Gains

```c
// BAD: Motors will oscillate and overheat
#define PID_KP  5.0f   // Way too high!
#define PID_KI  1.0f   // Way too high!
#define PID_KD  2.0f   // Way too high!

// GOOD: Conservative, stable
#define PID_KP  0.8f
#define PID_KI  0.06f
#define PID_KD  0.5f
```

### Mistake 2: Not Testing Step Response

```
Don't just test at constant speed!
Always test step response (sudden change).

Bad test: Command 0.3 m/s, see if it works
Good test: Command 0→0.3 m/s, observe transient
```

### Mistake 3: Ignoring Anti-Windup

```c
// Without anti-windup:
// Motor saturates at max PWM
// Integral keeps growing
// When target changes, huge overshoot!

// Always include:
if (integral > MAX_INTEGRAL) integral = MAX_INTEGRAL;
```

---

## Exercise: Tune Your Robot

**Scenario**: Your robot has these symptoms:
- Slow to reach target speed
- Slight steady-state error (stops at 0.45 m/s instead of 0.5 m/s)
- No oscillation

**Current gains**: Kp=0.3, Ki=0.0, Kd=0.0

**What should you adjust?**

**Answer**:

<details>
<summary>Click for answer</summary>

```
Problem analysis:
- Slow response → Kp too low
- Steady-state error → Ki needed

Solution:
1. Increase Kp to 0.6 (double it)
2. Add small Ki = 0.03
3. Test step response
4. If still slow, increase Kp more
5. If overshoots, add Kd or reduce Kp

Recommended next values:
Kp = 0.6, Ki = 0.03, Kd = 0.0
Then fine-tune!
```

</details>

---

## Summary

- **Ziegler-Nichols**: Systematic method to find initial gains
- **Kp critical**: Gain where system oscillates continuously
- **Fine-tuning**: Adjust based on observed response
- **Symptoms**: Learn to recognize what each gain controls
- **Multi-level**: Different gains for different speeds

---

## Next Lesson

[62-pid-tuning-practical.md](62-pid-tuning-practical.md) - Hands-on tuning guide with examples

---

*OrbiBot Firmware Study Guide*  
*Part 6 of 10*