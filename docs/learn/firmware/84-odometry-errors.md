# Part 8: Odometry Errors and Drift

**Duration**: 20 minutes  
**Prerequisites**: [Part 8: Odometry Implementation](83-odometry-implementation.md)

---

## Learning Objectives

After this lesson, you will understand:
- Types of odometry errors
- Why errors accumulate over time
- How to minimize errors
- When odometry is not sufficient

---

## Types of Odometry Errors

### 1. Systematic Errors

**Definition**: Consistent, predictable errors from imperfect calibration.

| Error Source | Effect | Example |
|--------------|--------|---------|
| Wheel diameter incorrect | Scale error | Think you moved 1m, actually moved 1.05m |
| Track width wrong | Rotation error | Think you turned 90°, actually turned 85° |
| Wheel misalignment | Skew | Robot drifts left when driving straight |

### 2. Non-Systematic Errors

**Definition**: Random errors from environmental factors.

| Error Source | Effect |
|--------------|--------|
| Wheel slippage | Underestimated distance |
| Uneven floor | One wheel travels more than other |
| Obstacles | Unexpected rotation |
| Cable drag | External force on robot |

---

## Visual Example of Drift

```
Expected Path (no errors):
Start →→→→→→→→→→→ Goal
(perfectly straight, 5 meters)

Actual Path (with drift):
Start →→↗→↗→↘→→↗→↘→?
                    ↑
                    Actually here
                    (3.8m from goal)
                    
After 10 meters of travel:
- Position error: ~30-50 cm
- Heading error: ~5-10°
```

---

## Error Propagation

### Why Errors Grow

```
Each small error adds up:

Step 1: Move 1m with 1% error
  True position: (1.0, 0)
  Odometry: (1.01, 0)
  Error: 1 cm

Step 2: Turn 90° with 2° error
  True heading: 90°
  Odometry: 92°
  
Step 3: Move 1m with 1% error
  True position: (1.0, 1.0)
  Odometry thinks: move at 92° for 1.01m
  Odometry: (1.01 - 0.035, 0 + 1.00) = (0.975, 1.00)
  
Total error: ~5 cm + angular misalignment
```

### The Math

Error grows roughly with **distance traveled**:

```
Position error ≈ distance × error_rate

Typical error rates:
- Good surfaces: 1-2% of distance
- Carpet: 5-10% of distance
- Poor surfaces: >10% of distance

Example: After driving 10m on carpet:
Error = 10m × 7% = 0.7m (70 cm off!)
```

---

## Error Sources in Detail

### Wheel Slippage

```
Scenario: Robot accelerates quickly
- Wheels spin before robot moves
- Encoder counts increase
- Odometry thinks robot moved
- Actually: Robot stayed still!

Solution:
- Gentle acceleration
- Lower PID gains at start
- IMU fusion to detect slip
```

### Uneven Floor

```
Scenario: One wheel on carpet, one on tile
- Carpet wheel: More friction, less slip
- Tile wheel: Less friction, more slip
- Result: Robot turns unexpectedly
- Odometry doesn't know about turn

Solution:
- Avoid mixed surfaces
- Use IMU to detect unexpected rotation
```

### Wheel Diameter Error

```
Calibration: Measured 100mm diameter
Actual: 102mm diameter (2% error)

Effect:
- Odometry: Think moved 314mm per rev
- Actual: Moved 320mm per rev
- After 10 rev: 200mm error!

Solution:
- Calibrate wheels precisely
- Measure actual distance traveled
```

---

## Minimizing Errors

### 1. Good Calibration

```c
// Calibrate wheel diameter by driving known distance
void calibrate_wheel_diameter(void)
{
    // Reset odometry
    odometry_reset();
    
    // Drive exactly 2 meters (measured with tape)
    move_distance(2.0);
    
    // Check odometry
    float measured_distance = sqrt(x*x + y*y);
    
    // Calculate correction factor
    float correction = 2.0 / measured_distance;
    
    // Apply to encoder constant
    encoder_correction *= correction;
}
```

### 2. IMU Fusion

Use gyroscope to correct heading drift:

```c
void odometry_update_with_imu(const wheel_velocity_t *wheels, 
                               float dt)
{
    // Standard odometry update
    odometry_update(wheels, dt);
    
    // Get IMU heading
    float imu_yaw = imu_get_yaw();
    
    // Blend odometry and IMU (complementary filter)
    // Trust IMU more for rotation
    float alpha = 0.98f;  // IMU weight
    robot_odom.theta = alpha * imu_yaw + 
                       (1 - alpha) * robot_odom.theta;
}
```

### 3. Regular Resets

Reset odometry when position is known:

```c
// At charging station (known location)
void on_reach_charging_station(void)
{
    odometry_set_position(CHARGER_X, CHARGER_Y, CHARGER_THETA);
}

// After localization with landmarks
void on_localize_with_landmarks(float x, float y, float theta)
{
    odometry_set_position(x, y, theta);
}
```

---

## When Odometry Fails

### Scenarios Where Odometry is Insufficient

1. **Long distances** (>10-20 meters)
   - Errors accumulate too much
   
2. **SLAM/navigation**
   - Need absolute position, not just relative
   
3. **Kidnapped robot problem**
   - Robot moved without odometry knowing

### Solutions

| Problem | Solution |
|---------|----------|
| Long distance | Periodic localization (landmarks, GPS) |
| SLAM | Laser scan matching, visual odometry |
| Kidnapped robot | External localization system |

---

## Error Budget

### Typical OrbiBot Performance

| Scenario | Expected Error |
|----------|----------------|
| 1m straight on tile | ±1-2 cm |
| 1m straight on carpet | ±2-5 cm |
| 90° turn on tile | ±2-3° |
| 90° turn on carpet | ±5-10° |
| 10m travel | ±20-50 cm |

### Acceptable Use Cases

✅ **Good for**:
- Short movements (<5m)
- Between localization updates
- Relative positioning

❌ **Not good for**:
- Long autonomous runs
- Precise positioning without correction
- Navigation without external reference

---

## Exercise: Calculate Expected Error

**Scenario**: Robot drives 5 meters on carpet (5% error rate)

**Calculate**:
1. Expected position error
2. Is this acceptable for navigation?

**Answer**:

<details>
<summary>Click for answer</summary>

```
1. Expected error:
   Error = 5m × 5% = 0.25m = 25 cm

2. Acceptability:
   For general navigation: OK (can correct with sensors)
   For precise docking: NOT OK (need <5cm accuracy)
   
   Solution: Use visual markers or other localization
   for the final approach to charging station.
```

</details>

---

## Summary

- **Systematic errors**: Calibration issues (fixable)
- **Non-systematic errors**: Environmental (minimize)
- **Error growth**: Proportional to distance traveled
- **Typical drift**: 1-10% of distance
- **Solutions**: Calibration, IMU fusion, periodic resets

---

## Next Lesson

[Part 9: Project Structure](90-project-structure.md) - Complete project overview (or continue to Part 9)

---

*OrbiBot Firmware Study Guide*  
*Part 8 of 10*