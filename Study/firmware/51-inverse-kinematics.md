# Part 5: Inverse Kinematics

**Duration**: 35 minutes  
**Prerequisites**: [50-mecanum-wheel-theory.md](50-mecanum-wheel-theory.md)

---

## Learning Objectives

After this lesson, you will understand:
- What inverse kinematics means for mobile robots
- The mecanum inverse kinematics equations
- How to calculate wheel speeds from robot velocity
- The role of robot geometry (wheelbase, track width)

---

## What is Inverse Kinematics?

**Inverse Kinematics (IK)** = Given a desired robot motion, calculate what each motor must do.

```
Forward Kinematics (easier):
Wheel speeds → Robot velocity
(Given individual wheel speeds, what does the robot do?)

Inverse Kinematics (what we need):
Robot velocity → Wheel speeds
(Given desired robot motion, what should each wheel do?)
```

---

## Robot Coordinate System

ROS (and OrbiBot) uses this standard:

```
        Forward (+X)
            ↑
            │
    Left    │    Right
   (+Y) ←───┼───→ (-Y)
            │
            ↓
        Backward (-X)
            
Rotation (+ω): Counter-clockwise (top view)
```

---

## Robot Geometry Parameters

| Symbol | Parameter | OrbiBot Value |
|--------|-----------|---------------|
| R | Wheel radius | 50 mm (0.05 m) |
| L | Wheelbase (front to rear) | 260 mm (0.26 m) |
| W | Track width (left to right) | 360 mm (0.36 m) |
| a | Half wheelbase (L/2) | 130 mm |
| b | Half track width (W/2) | 180 mm |

```
        Front
          │
    FL ═══╪═══ FR
        │ │ │
        │ │ │
        │ │ │
        │ │ │
    BL ═══╪═══ BR
          │
         Rear
         
    ←──── W ────→
    ←─b─→   ←─b─→
    
    ↑ L (wheelbase)
```

---

## The Inverse Kinematics Equations

For mecanum wheels with ABBA arrangement:

```
Input: Robot velocity (Vx, Vy, ω)
Output: Wheel velocities (Vfl, Vfr, Vbl, Vbr)
```

### Equations

```
Vfl = Vx - Vy - ω × (a + b)
Vfr = Vx + Vy + ω × (a + b)
Vbl = Vx + Vy - ω × (a + b)
Vbr = Vx - Vy + ω × (a + b)
```

Where:
- Vfl = Front-Left wheel velocity
- Vfr = Front-Right wheel velocity  
- Vbl = Back-Left wheel velocity
- Vbr = Back-Right wheel velocity
- (a + b) = 310 mm for OrbiBot

---

## Understanding the Equations

### Vx Term (Forward/Backward)
```
All wheels get +Vx:
Vfl = +Vx    Vfr = +Vx
Vbl = +Vx    Vbr = +Vx

Result: All wheels turn same way → Robot moves forward
```

### Vy Term (Strafe)
```
Opposite signs for opposite sides:
Vfl = -Vy    Vfr = +Vy
Vbl = +Vy    Vbr = -Vy

Left side: -Vy
Right side: +Vy
Result: Opposite forces → Robot strafes sideways
```

### ω Term (Rotation)
```
Diagonal pairs get same sign:
Vfl = -ω×(a+b)    Vfr = +ω×(a+b)
Vbl = -ω×(a+b)    Vbr = +ω×(a+b)

Front-Left and Back-Left: same direction
Front-Right and Back-Right: opposite direction
Result: Robot rotates around center
```

---

## Worked Example

**Scenario**: Robot needs to move:
- Forward at 0.5 m/s (Vx = 0.5)
- Right at 0.3 m/s (Vy = -0.3)  
- Rotate at 0.2 rad/s (ω = 0.2)

**Given**: a + b = 0.31 m

**Calculate each wheel**:

```
Vfl = 0.5 - (-0.3) - 0.2 × 0.31
    = 0.5 + 0.3 - 0.062
    = 0.738 m/s

Vfr = 0.5 + (-0.3) + 0.2 × 0.31
    = 0.5 - 0.3 + 0.062
    = 0.262 m/s

Vbl = 0.5 + (-0.3) - 0.2 × 0.31
    = 0.5 - 0.3 - 0.062
    = 0.138 m/s

Vbr = 0.5 - (-0.3) + 0.2 × 0.31
    = 0.5 + 0.3 + 0.062
    = 0.862 m/s
```

**Verification**: Different wheel speeds combine to create desired motion!

---

## Converting to Motor Commands

Wheel velocity → Motor RPM → PWM value

### Step 1: Wheel Velocity to RPM

```
RPM = (V × 60) / (2 × π × R)

Where:
V = wheel velocity (m/s)
R = wheel radius (m) = 0.05 m
```

**Example**: V = 0.5 m/s
```
RPM = (0.5 × 60) / (2 × 3.14159 × 0.05)
    = 30 / 0.314
    = 95.5 RPM
```

### Step 2: Account for Gear Ratio

```
Motor_RPM = Wheel_RPM × Gear_Ratio

OrbiBot gear ratio = 30:1
Motor_RPM = 95.5 × 30 = 2865 RPM
```

### Step 3: RPM to PWM

This is where PID control comes in (see Part 6)!

```
Target_Motor_Speed = 2865 RPM
Measured_Motor_Speed = from encoder
PID_Output = PWM value to achieve target
```

---

## Special Cases

### Pure Forward Motion
```
Vx = 0.5, Vy = 0, ω = 0

Vfl = 0.5    Vfr = 0.5
Vbl = 0.5    Vbr = 0.5

All wheels same speed!
```

### Pure Strafe Right
```
Vx = 0, Vy = -0.3, ω = 0

Vfl = +0.3    Vfr = -0.3
Vbl = -0.3    Vbr = +0.3

Diagonal pairs have same speed!
```

### Pure Rotation
```
Vx = 0, Vy = 0, ω = 0.5

Vfl = -0.155    Vfr = +0.155
Vbl = -0.155    Vbr = +0.155

Left side opposite to right side!
```

---

## Exercise: Calculate Wheel Speeds

**Given**: 
- Vx = 0.3 m/s (forward)
- Vy = 0.2 m/s (left)
- ω = 0.1 rad/s (CCW)
- a + b = 0.31 m

**Calculate** all four wheel velocities.

**Answer**:

<details>
<summary>Click for answer</summary>

```
Vfl = 0.3 - 0.2 - 0.1 × 0.31
    = 0.3 - 0.2 - 0.031
    = 0.069 m/s

Vfr = 0.3 + 0.2 + 0.1 × 0.31
    = 0.3 + 0.2 + 0.031
    = 0.531 m/s

Vbl = 0.3 + 0.2 - 0.1 × 0.31
    = 0.3 + 0.2 - 0.031
    = 0.469 m/s

Vbr = 0.3 - 0.2 + 0.1 × 0.31
    = 0.3 - 0.2 + 0.031
    = 0.131 m/s
```

</details>

---

## Firmware Implementation

From `mecanum_kinematics.c`:

```c
void mecanum_inverse_kinematics(const robot_velocity_t *robot, 
                                 wheel_velocity_t *wheels)
{
    // OrbiBot geometry constant
    #define ROBOT_APB  (WHEEL_BASE_M/2 + TRACK_WIDTH_M/2)  // a + b
    
    float vx = robot->vx;
    float vy = robot->vy;
    float v_rot = robot->omega * ROBOT_APB;  // ω × (a+b)

    // Inverse kinematics equations
    wheels->fl = vx - vy - v_rot;  // Front-Left
    wheels->bl = vx + vy - v_rot;  // Back-Left
    wheels->fr = vx + vy + v_rot;  // Front-Right
    wheels->br = vx - vy + v_rot;  // Back-Right
}
```

---

## Summary

- **Inverse kinematics** converts desired robot motion to wheel speeds
- **Key parameters**: Vx (forward), Vy (strafe), ω (rotation)
- **Geometry matters**: Wheelbase and track width affect rotation term
- **Four equations** give four wheel velocities
- **Next step**: Convert wheel velocities to motor commands using PID control

---

## Next Lesson

[52-forward-kinematics.md](52-forward-kinematics.md) - Calculate robot velocity from wheel speeds (for odometry)

---

*OrbiBot Firmware Study Guide*  
*Part 5 of 10*