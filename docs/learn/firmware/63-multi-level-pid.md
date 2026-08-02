---
title: "Part 6: Multi-Level PID"
type: learn
area: firmware
package: orbibot_rosmaster_firmware
duration: "20 minutes"
tags:
  - learn
  - firmware
---

# Part 6: Multi-Level PID

**Duration**: 20 minutes  
**Prerequisites**: [[62-pid-implementation]]

---

## Learning Objectives

After this lesson, you will understand:
- Why different speeds need different PID gains
- How multi-level PID works
- The three speed zones in OrbiBot
- Implementation and gain selection

---

## The Problem

### One Size Does Not Fit All

```
Low Speed (0-50 mm/s):
- High friction dominates
- Motors need more "push" to start
- Need higher Kp to overcome static friction
- But: Too high Kp causes oscillation at high speed

High Speed (200+ mm/s):
- Low friction, high momentum
- Need lower Kp to prevent oscillation
- But: Too low Kp causes sluggish response at low speed

Solution: Different gains for different speeds!
```

---

## Three Speed Zones

### OrbiBot's Multi-Level PID

| Zone | Speed Range | Characteristics | Kp | Ki | Kd |
|------|-------------|-----------------|----|----|----|
| **Low** | 0-50 mm/s | Friction dominates | 1.2 | 0.04 | 0.6 |
| **Medium** | 50-200 mm/s | Balanced | 0.8 | 0.06 | 0.5 |
| **High** | 200+ mm/s | Momentum dominates | 0.5 | 0.08 | 0.4 |

### Why These Values?

```
Low Speed:
- Kp = 1.2 (high): Overcome static friction
- Ki = 0.04 (low): Less integral accumulation
- Kd = 0.6 (high): More damping for stability

Medium Speed:
- Kp = 0.8 (medium): Balanced response
- Ki = 0.06 (medium): Standard integral action
- Kd = 0.5 (medium): Moderate damping

High Speed:
- Kp = 0.5 (low): Prevent oscillation
- Ki = 0.08 (high): Better steady-state accuracy
- Kd = 0.4 (low): Less derivative noise sensitivity
```

---

## Implementation

### Gain Table Structure

```c
// From pid_controller.h

typedef struct {
    float kp;
    float ki;
    float kd;
} pid_gains_t;

// Gain table for different speeds
typedef enum {
    PID_LEVEL_LOW = 0,      // 0-50 mm/s
    PID_LEVEL_MEDIUM,       // 50-200 mm/s
    PID_LEVEL_HIGH,         // 200+ mm/s
    PID_LEVEL_COUNT
} pid_level_t;

// Gain lookup table
static const pid_gains_t pid_gain_table[PID_LEVEL_COUNT] = {
    [PID_LEVEL_LOW]    = {1.2f, 0.04f, 0.6f},
    [PID_LEVEL_MEDIUM] = {0.8f, 0.06f, 0.5f},
    [PID_LEVEL_HIGH]   = {0.5f, 0.08f, 0.4f}
};
```

### Selecting Gains Based on Speed

```c
// Get appropriate gains for current speed
pid_level_t pid_get_level(float speed)
{
    // Use absolute speed
    float abs_speed = fabsf(speed);
    
    if (abs_speed < 50.0f) {
        return PID_LEVEL_LOW;
    } else if (abs_speed < 200.0f) {
        return PID_LEVEL_MEDIUM;
    } else {
        return PID_LEVEL_HIGH;
    }
}

// Get gains for level
void pid_get_gains(pid_level_t level, float *kp, float *ki, float *kd)
{
    *kp = pid_gain_table[level].kp;
    *ki = pid_gain_table[level].ki;
    *kd = pid_gain_table[level].kd;
}
```

### Updating Gains in Control Loop

```c
// From task_control.c

void task_control(void *params)
{
    // ... timing setup ...
    
    for (;;)
    {
        // ... read encoders, calculate speeds ...
        
        // PID control for each motor
        for (int i = 0; i < 4; i++) {
            // Get target speed
            float target = target_speeds[i];
            
            // Select PID level based on target (not measured)
            pid_level_t level = pid_get_level(target);
            
            // Get gains for this level
            float kp, ki, kd;
            pid_get_gains(level, &kp, &ki, &kd);
            
            // Update PID gains
            pid_motor[i].kp = kp;
            pid_motor[i].ki = ki;
            pid_motor[i].kd = kd;
            
            // Calculate PID
            float pwm = pid_update(&pid_motor[i], wheel_speeds[i], 0.01f);
            motor_set_pwm(i, (int16_t)pwm);
        }
        
        // ... wait for next period ...
    }
}
```

---

## Smooth Transitions

### Hysteresis to Prevent Oscillation

```c
// Problem: At boundary (50 mm/s), level constantly switches
// Solution: Add hysteresis

pid_level_t pid_get_level_with_hysteresis(float speed, pid_level_t current_level)
{
    float abs_speed = fabsf(speed);
    
    switch (current_level) {
        case PID_LEVEL_LOW:
            // Stay low until > 60 mm/s
            if (abs_speed > 60.0f) {
                return PID_LEVEL_MEDIUM;
            }
            return PID_LEVEL_LOW;
            
        case PID_LEVEL_MEDIUM:
            // Go high if > 220 mm/s
            if (abs_speed > 220.0f) {
                return PID_LEVEL_HIGH;
            }
            // Go low if < 40 mm/s
            if (abs_speed < 40.0f) {
                return PID_LEVEL_LOW;
            }
            return PID_LEVEL_MEDIUM;
            
        case PID_LEVEL_HIGH:
            // Stay high until < 180 mm/s
            if (abs_speed < 180.0f) {
                return PID_LEVEL_MEDIUM;
            }
            return PID_LEVEL_HIGH;
            
        default:
            return PID_LEVEL_MEDIUM;
    }
}
```

### Visual Example

```
Speed increasing:
0 mm/s → 40 mm/s → 60 mm/s → 200 mm/s → 220 mm/s
  ↓        ↓          ↓          ↓          ↓
 LOW      LOW      MEDIUM     MEDIUM     HIGH
 
Speed decreasing:
220 mm/s → 180 mm/s → 50 mm/s → 40 mm/s
    ↓          ↓         ↓         ↓
   HIGH      MEDIUM    MEDIUM    LOW
   
Note: 40-60 and 180-220 are hysteresis zones
```

---

## Benefits

### Performance Comparison

| Scenario | Single PID | Multi-Level PID |
|----------|------------|-----------------|
| Start from stop | Sluggish OR oscillates | Smooth, quick |
| Low speed precision | Poor | Good |
| High speed stability | Oscillates | Stable |
| Overall | Compromise | Optimized |

### Real-World Results

```
Test: 0 → 300 mm/s step response

Single PID (Kp=0.8):
- Time to 90%: 0.4s
- Overshoot: 15%
- Settling time: 0.8s

Multi-Level PID:
- Time to 90%: 0.2s
- Overshoot: 5%
- Settling time: 0.3s

Improvement: 2x faster, 3x less overshoot!
```

---

## Tuning Multi-Level PID

### Procedure

```
1. Tune LOW speed gains first
   - Command 20 mm/s
   - Adjust until smooth start and steady run
   
2. Tune MEDIUM speed gains
   - Command 100 mm/s
   - Balance response and stability
   
3. Tune HIGH speed gains
   - Command 300 mm/s
   - Minimize oscillation while maintaining response
   
4. Test transitions
   - Command speed changes between zones
   - Ensure smooth handoff
```

---

## Exercise: Design Gain Table

**Scenario**: You have a heavier robot with:
- High inertia at all speeds
- Very high static friction
- Maximum speed 500 mm/s

**Design** a 3-level PID table:

| Zone | Speed | Kp | Ki | Kd | Reasoning |
|------|-------|----|----|----|-----------|
| Low | 0-100 | ? | ? | ? | High friction |
| Medium | 100-300 | ? | ? | ? | Moderate |
| High | 300+ | ? | ? | ? | High inertia |

**Answer**:

<details>
<summary>Click for answer</summary>

```
Low (0-100 mm/s):
- Kp = 1.5 (very high to overcome static friction)
- Ki = 0.03 (low, prevent windup)
- Kd = 0.8 (high damping for stability)

Medium (100-300 mm/s):
- Kp = 1.0 (moderate)
- Ki = 0.05 (standard)
- Kd = 0.6 (moderate)

High (300+ mm/s):
- Kp = 0.6 (lower to prevent oscillation from inertia)
- Ki = 0.08 (higher for accuracy at speed)
- Kd = 0.4 (lower, less noise sensitive)

Heavier robot needs generally higher Kp at low speed,
but must reduce Kp more at high speed due to inertia.
```

</details>

---

## Summary

- **Multi-level PID**: Different gains for different speeds
- **Three zones**: Low (0-50), Medium (50-200), High (200+)
- **Hysteresis**: Prevents rapid switching at boundaries
- **Benefits**: Optimized performance across all speeds

---

## Next Lesson

[[64-yaw-control]] - Heading control with yaw PID

---

*OrbiBot Firmware Study Guide*  
*Part 6 of 10*