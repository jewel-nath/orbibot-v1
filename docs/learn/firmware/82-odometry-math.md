# Part 8: Odometry Mathematics

**Duration**: 25 minutes  
**Prerequisites**: [Part 8: From Encoders to Distance](81-encoder-to-distance.md)

---

## Learning Objectives

After this lesson, you will understand:
- The mathematical derivation of odometry
- How to update position from velocity
- Coordinate frame transformations
- The integration process step-by-step

---

## The Core Problem

Given robot velocity (vx, vy, omega) at each time step, calculate the new position (x, y, theta).

```
┌─────────────────────────────────────────────────────────┐
│  Given at time t:                                        │
│  • Current position: (x, y, θ)                          │
│  • Robot velocity: (vx, vy, ω) in robot frame           │
│                                                          │
│  Find at time t+dt:                                     │
│  • New position: (x', y', θ')                           │
└─────────────────────────────────────────────────────────┘
```

---

## Step 1: Update Heading

The simplest update - just add rotation.

```
θ' = θ + ω × dt

Example:
  θ = 0° (facing forward)
  ω = 0.5 rad/s
  dt = 0.01s (10ms)
  
  θ' = 0 + 0.5 × 0.01 = 0.005 rad ≈ 0.29°
```

---

## Step 2: Calculate Distance Traveled

In the robot's local frame:

```
Distance in robot frame:
  dx_robot = vx × dt
  dy_robot = vy × dt
  
Example:
  vx = 0.5 m/s
  vy = 0.0 m/s
  dt = 0.01s
  
  dx_robot = 0.5 × 0.01 = 0.005 m = 5 mm
  dy_robot = 0.0 × 0.01 = 0.0 m
```

---

## Step 3: Transform to Global Frame

The robot moved in its own frame, but we need to know where it went in the world.

### Rotation Matrix

To transform from robot frame to global frame, rotate by θ:

```
Global displacement = Rotation(θ) × Robot displacement

┌    ┐   ┌              ┐   ┌        ┐
│ dx │   │  cos(θ)  -sin(θ) │   │ dx_robot │
│ dy │ = │  sin(θ)   cos(θ) │ × │ dy_robot │
└    ┘   └              ┘   └        ┘

Which gives:
  dx = dx_robot × cos(θ) - dy_robot × sin(θ)
  dy = dx_robot × sin(θ) + dy_robot × cos(θ)
```

### Visual Explanation

```
Robot frame (before rotation):
              ↑ Y_robot
              │
              │
    X_robot ←─┼─→ Robot moved 5mm forward
              │
              
Global frame (after applying rotation):
    θ = 30°
              ↗ Y_global
             ╱
            ╱  Robot moved at 30° angle
           ╱   in global frame
    X_global ⟶
```

### Example Calculation

```
Given:
  dx_robot = 5 mm = 0.005 m
  dy_robot = 0 mm
  θ = 30° = 0.524 rad
  dt = 10 ms

Calculate global displacement:
  cos(30°) = 0.866
  sin(30°) = 0.5

  dx = 0.005 × 0.866 - 0 × 0.5 = 0.00433 m
  dy = 0.005 × 0.5 + 0 × 0.866 = 0.0025 m

Result: Robot moved 4.33mm in X, 2.5mm in Y (global frame)
```

---

## Step 4: Update Position

Simply add the displacement to current position:

```
x' = x + dx
y' = y + dy
θ' = θ + dθ  (already calculated)

Example (continued):
  x = 1.000 m
  y = 0.500 m
  θ = 30°
  
  x' = 1.000 + 0.00433 = 1.00433 m
  y' = 0.500 + 0.0025 = 0.5025 m
  θ' = 30° + 0.29° = 30.29°
```

---

## Complete Integration Formula

Putting it all together:

```
┌─────────────────────────────────────────────────────────┐
│  ODOMETRY UPDATE EQUATIONS                               │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  // 1. Calculate time step                              │
│  dt = current_time - previous_time                      │
│                                                          │
│  // 2. Calculate robot frame displacement               │
│  dx_robot = vx × dt                                      │
│  dy_robot = vy × dt                                      │
│  dtheta = omega × dt                                     │
│                                                          │
│  // 3. Transform to global frame                        │
│  dx = dx_robot × cos(θ) - dy_robot × sin(θ)            │
│  dy = dx_robot × sin(θ) + dy_robot × cos(θ)            │
│                                                          │
│  // 4. Update position                                  │
│  x = x + dx                                              │
│  y = y + dy                                              │
│  θ = θ + dtheta                                          │
│                                                          │
│  // 5. Normalize angle                                  │
│  θ = normalize_angle(θ)  // Keep in [-π, π]            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Complete Example Walkthrough

### Scenario

```
Initial state:
  x = 0 m, y = 0 m, θ = 0°
  
Command:
  Move forward at 0.3 m/s for 1 second
  Then turn 90° while continuing forward
```

### Time Steps (simplified to 100ms steps for clarity)

```
t=0:  x=0.000,  y=0.000,  θ=0.000°
t=0.1: vx=0.3, vy=0, omega=0
  dx_robot = 0.3 × 0.1 = 0.03 m
  dy_robot = 0
  cos(0)=1, sin(0)=0
  dx = 0.03 × 1 - 0 × 0 = 0.03 m
  dy = 0.03 × 0 + 0 × 1 = 0 m
  x = 0 + 0.03 = 0.03 m
  y = 0 + 0 = 0 m
  θ = 0 + 0 = 0°
  
t=0.2 to t=0.9: Continue straight...
  At t=1.0: x=0.300, y=0.000, θ=0°

t=1.0: Start turning, omega = π/2 rad/s (90°/s)
  vx=0.3, vy=0, omega=1.57
  dx_robot = 0.3 × 0.1 = 0.03 m
  dtheta = 1.57 × 0.1 = 0.157 rad = 9°
  
  θ before update = 0°
  cos(0)=1, sin(0)=0
  dx = 0.03 × 1 - 0 = 0.03
  dy = 0.03 × 0 + 0 = 0
  x = 0.30 + 0.03 = 0.33 m
  y = 0 + 0 = 0 m
  θ = 0 + 0.157 = 0.157 rad = 9°

t=1.1: Continuing turn...
  θ before update = 9°
  cos(9°)=0.988, sin(9°)=0.156
  dx = 0.03 × 0.988 - 0 = 0.0296 m
  dy = 0.03 × 0.156 + 0 = 0.0047 m
  x = 0.33 + 0.0296 = 0.3596 m
  y = 0 + 0.0047 = 0.0047 m
  θ = 9° + 9° = 18°

...continue for 1 second total...

t=2.0: After completing 90° turn
  x ≈ 0.3 + 0.3/√2 ≈ 0.51 m
  y ≈ 0.3/√2 ≈ 0.21 m
  θ = 90° = π/2 rad
```

---

## Mathematical Derivation

### For the Curious: Why This Works

The odometry equations are a discrete approximation of integrating differential drive kinematics:

```
Continuous time:
  dx/dt = vx × cos(θ) - vy × sin(θ)
  dy/dt = vx × sin(θ) + vy × cos(θ)
  dθ/dt = omega

Discrete approximation (Euler integration):
  x(k+1) = x(k) + [vx × cos(θ) - vy × sin(θ)] × dt
  y(k+1) = y(k) + [vx × sin(θ) + vy × cos(θ)] × dt
  θ(k+1) = θ(k) + omega × dt
```

This is called **Euler integration** - simple but accumulates error over time.

---

## Higher Order Integration (Optional)

### Runge-Kutta (More Accurate)

For better accuracy, use midpoint (Runge-Kutta 2nd order):

```
// Calculate displacement at current heading
dx1 = vx × dt × cos(θ)
dy1 = vy × dt × sin(θ)

// Calculate displacement at mid-angle
theta_mid = θ + omega × dt / 2
dx2 = vx × dt × cos(theta_mid)
dy2 = vy × dt × sin(theta_mid)

// Use midpoint displacement
x = x + dx2
y = y + dy2
θ = θ + omega × dt
```

**Benefit**: More accurate for curved paths  
**Cost**: More computation

OrbiBot uses simple Euler (sufficient at 100Hz).

---

## Exercise: Calculate Position Update

**Given**:
- Current position: x=1.0m, y=2.0m, θ=45°
- Velocity: vx=0.2 m/s, vy=0.1 m/s, omega=0.5 rad/s
- dt = 0.01s (10ms)

**Calculate**:
1. Robot frame displacement
2. Global frame displacement
3. New position and heading

**Answer**:

<details>
<summary>Click for answer</summary>

```
1. Robot frame displacement:
   dx_robot = 0.2 × 0.01 = 0.002 m = 2 mm
   dy_robot = 0.1 × 0.01 = 0.001 m = 1 mm
   dtheta = 0.5 × 0.01 = 0.005 rad ≈ 0.29°

2. Transform to global frame:
   θ = 45° = 0.785 rad
   cos(45°) = 0.707
   sin(45°) = 0.707
   
   dx = 0.002 × 0.707 - 0.001 × 0.707 = 0.000707 m
   dy = 0.002 × 0.707 + 0.001 × 0.707 = 0.002121 m

3. New position:
   x' = 1.0 + 0.000707 = 1.000707 m
   y' = 2.0 + 0.002121 = 2.002121 m
   θ' = 45° + 0.29° = 45.29°
```

</details>

---

## Summary

- **Step 1**: Calculate robot frame displacement
- **Step 2**: Rotate by current heading to get global displacement
- **Step 3**: Add to current position
- **Step 4**: Update heading
- **Step 5**: Normalize angle

---

## Next Lesson

[Part 8: Odometry Implementation](83-odometry-implementation.md) - Firmware implementation details

---

*OrbiBot Firmware Study Guide*  
*Part 8 of 10*