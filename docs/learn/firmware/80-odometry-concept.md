---
title: "Part 8: What is Odometry?"
type: learn
area: firmware
package: orbibot_rosmaster_firmware
duration: "20 minutes"
tags:
  - learn
  - firmware
---

# Part 8: What is Odometry?

**Duration**: 20 minutes  
**Prerequisites**: [[52-forward-kinematics]]

---

## Learning Objectives

After this lesson, you will understand:
- What odometry is and why we need it
- How robots track their position
- The concept of "dead reckoning"
- Why odometry has errors
- How OrbiBot uses odometry

---

## What is Odometry?

**Odometry** = Estimating position by counting wheel rotations

### Simple Analogy

```
You walk with your eyes closed:
  - You count your steps
  - You know each step is ~0.7 meters
  - After 10 steps, you estimate: "I'm ~7 meters from start"

BUT:
  - You might have veered left/right (drift)
  - Steps might not be exactly 0.7m (slippage)
  - Your estimate gets worse over time

That's odometry!
```

### Robot Version

```
Robot odometry:
  1. Count encoder ticks (wheel rotations)
  2. Calculate distance traveled
  3. Calculate direction change
  4. Integrate to get position (x, y, θ)
```

---

## Why Do We Need Odometry?

### The Problem

```
Robot needs to know:
  - "Where am I?"
  - "How far have I traveled?"
  - "Am I facing the right direction?"

Without odometry:
  - Robot drives blind
  - Cannot navigate autonomously
  - Cannot return to starting position
```

### Use Cases

| Application | Why Odometry Needed |
|-------------|-------------------|
| **SLAM** | Build map while tracking position |
| **Navigation** | Plan path from A to B |
| **Autonomous Driving** | Follow planned trajectory |
| **Return Home** | Return to charging station |
| **Collision Avoidance** | Know if near obstacles |

---

## How Odometry Works

### The Process

```
┌─────────────────────────────────────────────────────────┐
│                    Odometry Pipeline                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. ENCODER COUNTING                                     │
│     ↓                                                    │
│     Read wheel encoders (ticks)                          │
│     "FL: +132, FR: +128, BL: +130, BR: +131"            │
│                                                          │
│  2. WHEEL VELOCITY                                       │
│     ↓                                                    │
│     Convert ticks to speed (m/s)                         │
│     "Each wheel moved ~0.1m in 0.01s"                   │
│                                                          │
│  3. FORWARD KINEMATICS                                   │
│     ↓                                                    │
│     Calculate robot velocity (Vx, Vy, ω)                 │
│     "Moving forward at 0.5 m/s, turning 0.1 rad/s"      │
│                                                          │
│  4. INTEGRATION                                          │
│     ↓                                                    │
│     Add to position (x, y, θ)                            │
│     "New position: (1.25m, 0.5m, 0.3rad)"               │
│                                                          │
│  5. REPEAT                                               │
│     ↓                                                    │
│     Run at 100Hz (every 10ms)                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Math: From Velocity to Position

```c
// Each control loop (100Hz = every 10ms)
void update_odometry(void) {
    // 1. Get robot velocity (from forward kinematics)
    float vx = robot_velocity.vx;      // m/s forward
    float vy = robot_velocity.vy;      // m/s sideways
    float omega = robot_velocity.omega; // rad/s rotation
    
    // 2. Time step (0.01 seconds)
    float dt = 0.01;  // 10ms
    
    // 3. Calculate distance traveled in this step
    float dx = vx * dt;        // meters
    float dy = vy * dt;        // meters
    float dtheta = omega * dt; // radians
    
    // 4. Transform to global frame (account for current heading)
    float cos_theta = cos(robot_theta);
    float sin_theta = sin(robot_theta);
    
    float global_dx = dx * cos_theta - dy * sin_theta;
    float global_dy = dx * sin_theta + dy * cos_theta;
    
    // 5. Update position
    robot_x += global_dx;
    robot_y += global_dy;
    robot_theta += dtheta;
    
    // Normalize theta to -PI to +PI
    while (robot_theta > PI) robot_theta -= 2*PI;
    while (robot_theta < -PI) robot_theta += 2*PI;
}
```

---

## Odometry Errors

### Types of Errors

```
┌─────────────────────────────────────────────────────────┐
│                    Error Sources                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  1. WHEEL SLIPPAGE                                       │
│     ├── Wheels spin without robot moving                 │
│     ├── Common on slippery floors                        │
│     └── Encoder counts distance, but robot didn't move   │
│                                                          │
│  2. UNEVEN FLOOR                                         │
│     ├── Wheels lose contact with ground                  │
│     ├── One wheel spins free                             │
│     └── Incorrect distance calculation                   │
│                                                          │
│  3. IMPERFECT MEASUREMENTS                               │
│     ├── Wheel diameter not exact                         │
│     ├── Track width measurement error                    │
│     └── Encoder resolution limits                        │
│                                                          │
│  4. INTEGRATION DRIFT                                    │
│     ├── Small errors accumulate over time                │
│     ├── "Death by a thousand cuts"                       │
│     └── Position estimate drifts from reality            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Visual Example: Drift

```
Expected Path (perfect):
Start →→→→→→→→→→→→ Goal
       (straight line)

Actual Path (with drift):
Start →→↗→↗→↘→→↗→↘→?
                    ↑
                    Actually here, but thinks it's at Goal

The longer you drive, the bigger the error!
```

---

## OrbiBot Odometry System

### Specifications

| Parameter | Value |
|-----------|-------|
| Update Rate | 100 Hz (every 10ms) |
| Encoder Resolution | 1320 counts/revolution |
| Wheel Diameter | 100 mm |
| Position Precision | ~0.1 mm per encoder count |
| Typical Drift | 1-5% of distance traveled |

### Firmware Implementation

```c
// From: control/odometry.c

typedef struct {
    float x;        // meters
    float y;        // meters
    float theta;    // radians
    float vx;       // m/s
    float vy;       // m/s
    float omega;    // rad/s
} odometry_t;

void odometry_update(odometry_t *odom, 
                     const wheel_velocity_t *wheels,
                     float dt) {
    robot_velocity_t robot_vel;
    
    // 1. Forward kinematics: wheels → robot velocity
    mecanum_forward_kinematics(wheels, &robot_vel);
    
    // 2. Store current velocity
    odom->vx = robot_vel.vx;
    odom->vy = robot_vel.vy;
    odom->omega = robot_vel.omega;
    
    // 3. Calculate position change
    float cos_theta = cosf(odom->theta);
    float sin_theta = sinf(odom->theta);
    
    // Transform to global frame
    float dx = (robot_vel.vx * cos_theta - 
                robot_vel.vy * sin_theta) * dt;
    float dy = (robot_vel.vx * sin_theta + 
                robot_vel.vy * cos_theta) * dt;
    float dtheta = robot_vel.omega * dt;
    
    // 4. Update position
    odom->x += dx;
    odom->y += dy;
    odom->theta += dtheta;
    
    // 5. Normalize angle
    while (odom->theta > PI_F) odom->theta -= 2*PI_F;
    while (odom->theta < -PI_F) odom->theta += 2*PI_F;
}
```

---

## Odometry vs GPS

### Comparison

| Feature | Odometry | GPS |
|---------|----------|-----|
| **Accuracy** | Millimeters (short term) | Meters |
| **Drift** | Yes (accumulates error) | No (absolute position) |
| **Indoor** | ✅ Works | ❌ Doesn't work |
| **Update Rate** | 100 Hz | 1-10 Hz |
| **Latency** | <1ms | 100-500ms |
| **Cost** | Cheap (encoders) | Expensive module |

### Why Use Both?

```
INDOOR (No GPS):
  → Only odometry available
  → Use IMU to reduce drift
  → Use landmarks for correction

OUTDOOR (GPS available):
  → GPS for absolute position
  → Odometry for high-rate updates (100Hz)
  → Fuse together for best accuracy

OrbiBot primarily uses:
  → Odometry (100Hz)
  → IMU for heading correction
  → Laser scan matching (SLAM) for drift correction
```

---

## Exercise: Calculate Position

**Scenario**: Robot drives:
- Forward at 0.5 m/s for 2 seconds
- Then rotates at 0.5 rad/s for 1 second
- Then forward at 0.3 m/s for 3 seconds

**Calculate** final position (x, y, θ), assuming start at (0, 0, 0)

**Answer**:

<details>
<summary>Click for answer</summary>

```
Phase 1 (0-2s): Forward 0.5 m/s
  Distance = 0.5 × 2 = 1.0 m
  Position: (1.0, 0, 0)

Phase 2 (2-3s): Rotate 0.5 rad/s
  Rotation = 0.5 × 1 = 0.5 rad (~28.6°)
  Position: (1.0, 0, 0.5)

Phase 3 (3-6s): Forward 0.3 m/s
  Distance = 0.3 × 3 = 0.9 m
  Direction: 0.5 rad from X-axis
  
  dx = 0.9 × cos(0.5) = 0.9 × 0.877 = 0.789 m
  dy = 0.9 × sin(0.5) = 0.9 × 0.479 = 0.431 m
  
  Final position:
    x = 1.0 + 0.789 = 1.789 m
    y = 0 + 0.431 = 0.431 m
    θ = 0.5 rad

Answer: (1.79m, 0.43m, 0.5rad or 28.6°)
```

</details>

---

## Summary

- **Odometry** = Position estimation from wheel rotations
- **Process**: Encoders → Wheel speed → Robot velocity → Position
- **Runs at** 100Hz in OrbiBot (control loop rate)
- **Errors**: Wheel slippage, uneven floor, integration drift
- **Used for**: Navigation, SLAM, autonomous driving
- **Limitation**: Drifts over time, needs correction (IMU, SLAM)

---

## Next Lesson

[[81-encoder-to-distance]] - How encoder counts become distance

---

*OrbiBot Firmware Study Guide*  
*Part 8 of 10*