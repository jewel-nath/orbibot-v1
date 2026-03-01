# Part 8: From Encoders to Distance

**Duration**: 20 minutes  
**Prerequisites**: [80-odometry-concept.md](80-odometry-concept.md)

---

## Learning Objectives

After this lesson, you will understand:
- How encoders measure wheel rotation
- Converting encoder counts to distance
- Calculating wheel velocity
- The math behind encoder resolution

---

## What is an Encoder?

### Basic Principle

An encoder counts how many times a wheel rotates. More counts = more precision.

```
Encoder = Rotation Counter

  Wheel rotates → Encoder counts pulses
  More rotation → Higher count
  
Example:
  Start: 0 counts
  Rotate 1/4 turn: 330 counts
  Rotate 1/2 turn: 660 counts
  Rotate full turn: 1320 counts
```

### Quadrature Encoders

OrbiBot uses **quadrature encoders** which can detect:
- Rotation amount (how much)
- Rotation direction (clockwise vs counter-clockwise)

```
Quadrature Encoding:

Channel A:  ░░░████░░░████░░░████░░░
Channel B:  ░████░░░████░░░████░░░█

A leads B → Clockwise
B leads A → Counter-clockwise

Resolution: 4× counts per pulse (A and B edges)
```

---

## Encoder Specifications

### OrbiBot Encoder Specs

| Parameter | Value |
|-----------|-------|
| Encoder PPR (pulses/rev) | 330 |
| Quadrature multiplier | 4× |
| **Counts per revolution** | **1320** |
| Wheel diameter | 100 mm |
| Wheel circumference | 314.16 mm |

### Where 1320 Comes From

```
Motor encoder: 11 pulses per motor revolution
Gear ratio: 30:1 (motor turns 30× for 1 wheel turn)
Pulses per wheel rev: 11 × 30 = 330
Quadrature (4×): 330 × 4 = 1320 counts per wheel revolution
```

---

## Counts to Distance

### The Formula

```
Distance = (Counts / Counts_Per_Rev) × Wheel_Circumference

Or simplified:
Distance = Counts × Distance_Per_Count
```

### Calculating Distance Per Count

```c
// Constants
#define ENCODER_CPR         1320        // Counts per revolution
#define WHEEL_DIAMETER_MM   100.0f      // mm
#define PI_F                3.14159f

// Wheel circumference
#define WHEEL_CIRCUMFERENCE_MM (PI_F * WHEEL_DIAMETER_MM)  // 314.16 mm

// Distance per encoder count
#define MM_PER_COUNT (WHEEL_CIRCUMFERENCE_MM / ENCODER_CPR)  // 0.238 mm

// Or as a single calculation:
// MM_PER_COUNT = (π × 100) / 1320 = 0.238 mm per count
```

### Example Calculations

| Counts | Calculation | Distance |
|--------|-------------|----------|
| 1320 | 1320 × 0.238 | 314.2 mm (1 revolution) |
| 660 | 660 × 0.238 | 157.1 mm (1/2 revolution) |
| 100 | 100 × 0.238 | 23.8 mm |
| 1 | 1 × 0.238 | 0.238 mm |

**Precision**: Each encoder count = 0.238 mm of wheel movement!

---

## Velocity from Encoders

### Measuring Speed

```
Velocity = Distance / Time

In firmware:
- Read encoder count at time t1
- Wait Δt (e.g., 10ms)
- Read encoder count at time t2
- Velocity = (count2 - count1) × MM_PER_COUNT / Δt
```

### Code Implementation

```c
// Called at 100Hz (every 10ms)

float calculate_wheel_velocity(int motor_id, float dt)
{
    static int32_t prev_count[4] = {0};
    
    // Read current encoder count
    int32_t current_count = encoder_get_count(motor_id);
    
    // Calculate delta
    int32_t delta = current_count - prev_count[motor_id];
    prev_count[motor_id] = current_count;
    
    // Convert to distance (mm)
    float distance_mm = delta * MM_PER_COUNT;
    
    // Convert to velocity (mm/s)
    float velocity_mm_s = distance_mm / dt;
    
    return velocity_mm_s;
}
```

### Example

```
At 100Hz (dt = 0.01s):
Delta counts = 13
Distance = 13 × 0.238 = 3.094 mm
Velocity = 3.094 / 0.01 = 309.4 mm/s ≈ 0.31 m/s
```

---

## Encoder Reading Hardware

### How STM32 Reads Encoders

```c
// STM32 timer in encoder mode
// Automatically counts up/down based on quadrature signals

void encoder_init(void)
{
    // Configure TIM2 for encoder 1
    TIM2->SMCR = 0x03;  // Encoder mode 3 (counts on both edges)
    TIM2->CCER = 0x00;  // Rising edges
    TIM2->ARR = 0xFFFF; // Auto-reload (16-bit counter)
    TIM2->CNT = 0;      // Start at 0
    TIM2->CR1 = 0x01;   // Enable timer
}

int32_t encoder_get_count(int motor_id)
{
    switch(motor_id) {
        case 0: return (int16_t)TIM2->CNT;  // Read TIM2 counter
        case 1: return (int16_t)TIM3->CNT;
        case 2: return (int16_t)TIM4->CNT;
        case 3: return (int16_t)TIM5->CNT;
    }
}
```

### Handling Overflow

```c
// 16-bit counter overflows at 65535
// Need to track total count with overflow handling

int32_t encoder_get_total_count(int motor_id)
{
    static int32_t total_count[4] = {0};
    static uint16_t prev_raw[4] = {0};
    
    uint16_t raw = encoder_get_count(motor_id);
    int16_t delta = (int16_t)(raw - prev_raw[motor_id]);
    
    total_count[motor_id] += delta;
    prev_raw[motor_id] = raw;
    
    return total_count[motor_id];
}
```

---

## Practical Example

### Robot Moving Forward

```
Initial state:
All encoders: 0 counts

After 1 second at 0.5 m/s:
Expected distance: 500 mm
Expected counts: 500 / 0.238 ≈ 2101 counts

Actual encoder readings:
FL: +2101, FR: +2105, BL: +2098, BR: +2103

Slight differences due to:
- Wheel diameter variations
- Slippage
- Surface irregularities
```

### Calculating Robot Velocity

```c
void calculate_robot_velocity(float *vx, float *vy, float *omega)
{
    float wheel_v[4];
    
    // Get each wheel velocity
    for (int i = 0; i < 4; i++) {
        wheel_v[i] = calculate_wheel_velocity(i, 0.01f);
    }
    
    // Forward kinematics (see Part 5)
    *vx = (wheel_v[0] + wheel_v[1] + wheel_v[2] + wheel_v[3]) / 4.0f;
    *vy = (-wheel_v[0] + wheel_v[1] + wheel_v[2] - wheel_v[3]) / 4.0f;
    *omega = (-wheel_v[0] - wheel_v[1] + wheel_v[2] + wheel_v[3]) 
             / (4.0f * (WHEEL_BASE/2 + TRACK_WIDTH/2));
}
```

---

## Exercise: Calculate Distance

**Given**:
- Wheel diameter: 100 mm
- Encoder CPR: 1320
- Measured counts: +5280

**Calculate**:
1. Distance per count
2. Total distance traveled
3. Number of wheel revolutions

**Answer**:

<details>
<summary>Click for answer</summary>

```
1. Distance per count:
   Circumference = π × 100 = 314.16 mm
   MM_PER_COUNT = 314.16 / 1320 = 0.238 mm

2. Total distance:
   Distance = 5280 × 0.238 = 1256.6 mm ≈ 1.26 meters

3. Wheel revolutions:
   Revolutions = 5280 / 1320 = 4 revolutions
   
   (Check: 4 × 314.16 = 1256.6 mm ✓)
```

</details>

---

## Summary

- **Encoder CPR**: 1320 counts per wheel revolution
- **Distance per count**: 0.238 mm
- **Velocity**: (Δcounts × 0.238) / Δt
- **Precision**: Sub-millimeter (0.238 mm resolution)

---

## Next Lesson

[82-odometry-math.md](82-odometry-math.md) - Mathematical derivation of position update

---

*OrbiBot Firmware Study Guide*  
*Part 8 of 10*