# OrbiBot Advanced Mecanum Control Guide

This guide documents the advanced mecanum wheel control capabilities of OrbiBot, showcasing full holonomic movement patterns.

## What are Mecanum Wheels?

Mecanum wheels are special omnidirectional wheels with angled rollers that enable **holonomic movement** - the ability to move in any direction while independently controlling rotation. This gives the robot **3 degrees of freedom (DOF)**:

- **vx**: Linear velocity forward/backward
- **vy**: Linear velocity left/right (strafe)
- **wz**: Angular velocity (rotation)

## Movement Capabilities

### Basic Movements
1. **Forward/Backward** - Standard linear movement (vx only)
2. **Strafe Left/Right** - Pure sideways movement (vy only) - **HOLONOMIC!**
3. **Rotate/Pivot** - Spin in place (wz only)

### Advanced Movements
4. **Diagonal** - 45° movements (vx + vy combined)
5. **Crab Walk** - Strafe while rotating (vy + wz)
6. **Arc/Circle** - Drive in curves (vx + wz)
7. **Complex** - All three DOF simultaneously (vx + vy + wz)

## Controller Packages

### 1. Standard PS Controller (`ps_controller.py`)
Basic mecanum control with safety features.

**Features:**
- Free control of all three DOF
- Multi-gear speed control
- R2 trigger as dead-man switch
- Emergency stop

**Launch:**
```bash
ros2 launch orbibot_teleop controller.launch.py
```

**Controls:**
- Left Stick: Forward/back + strafe
- Right Stick X: Rotation
- R2: Hold to enable movement
- L1: Toggle motor enable
- Triangle/X: Speed gear
- Square/Circle: Angular gear
- Share: Emergency stop

### 2. Advanced Mecanum Controller (`mecanum_teleop`)
Enhanced controller with explicit movement modes.

**Features:**
- 7 distinct movement modes
- D-pad mode selection
- Visual mode feedback
- Precision control for each movement type

**Launch:**
```bash
ros2 launch orbibot_teleop controller.launch.py
```

**Movement Modes:**

| Mode | D-Pad | Description | Controls |
|------|-------|-------------|----------|
| **NORMAL** | UP | Free control (all axes) | Left stick: move, Right stick: turn |
| **STRAFE** | RIGHT | Pure sideways only | Left stick X: strafe |
| **DIAGONAL** | DOWN | 45° diagonal movements | Left stick: diagonal, Right stick: turn |
| **ROTATE** | LEFT | Pure rotation in place | Right stick X: rotate |
| **CRAB** | R3 button | Strafe + rotate | Left stick X: strafe, Right stick: rotate |
| **CIRCLE** | L3 button | Drive in arcs | Left stick Y: forward, X: turn rate |

**Controls:**
```
Movement:
  Left Stick X/Y: Primary movement (varies by mode)
  Right Stick X: Rotation control (varies by mode)

Mode Selection:
  D-Pad UP: Normal mode
  D-Pad RIGHT: Strafe mode
  D-Pad DOWN: Diagonal mode
  D-Pad LEFT: Rotate mode
  R3 (Right Stick Press): Crab mode
  L3 (Left Stick Press): Circle mode

Safety:
  R2 (trigger): Hold to enable movement
  L1: Toggle motor enable/disable
  Share: Emergency stop

Gears:
  Triangle/X: Speed gear (33%, 66%, 100%)
  Square/Circle: Angular gear (25%, 50%, 75%, 100%)
```

### 3. Mecanum Demo (`mecanum_demo`)
Automated demonstration of all mecanum movements.

**Features:**
- Automated sequence of 14 movement patterns
- Educational demonstration
- Configurable speed and duration

**Launch:**
```bash
ros2 launch orbibot_teleop 
```

**Parameters:**
```bash
# Custom speed
ros2 launch orbibot_teleop  speed:=0.15

# Custom duration per movement
ros2 launch orbibot_teleop  duration:=4.0

# Don't auto-enable motors
ros2 launch orbibot_teleop  enable_motors:=false
```

**Demo Sequence:**
1. Forward movement
2. Backward movement
3. Strafe left (holonomic!)
4. Strafe right (holonomic!)
5. Rotate left (pivot)
6. Rotate right (pivot)
7. Diagonal forward-left (45°)
8. Diagonal forward-right (45°)
9. Diagonal backward-left (45°)
10. Diagonal backward-right (45°)
11. Crab walk (strafe + rotate)
12. Circle drive (forward arc)
13. Complex (all 3 DOF)
14. Sideways arc (strafe circle)

## Mecanum Kinematics

### Inverse Kinematics (Velocity → Wheel Speeds)

For a mecanum robot with:
- **r**: Wheel radius
- **w**: Track width / 2 (half distance between left/right wheels)
- **l**: Wheelbase / 2 (half distance between front/rear axles)

Given body velocities (vx, vy, wz), wheel speeds are:

```
ω_fl = 1/r * ((-l-w)*wz + vx - vy)
ω_fr = 1/r * ((l+w)*wz + vx + vy)
ω_rr = 1/r * ((l+w)*wz + vx - vy)
ω_rl = 1/r * ((-l-w)*wz + vx + vy)
```

**Matrix form:**
```
[ω_fl]   1/r  [  1  -1  -(l+w) ] [vx]
[ω_fr] = --- [  1   1   (l+w) ] [vy]
[ω_rr]       [  1  -1   (l+w) ] [wz]
[ω_rl]       [  1   1  -(l+w) ]
```

### Movement Examples

**1. Pure Strafe Left:**
```python
vx = 0.0, vy = 0.3, wz = 0.0
# Result: Robot moves sideways to the left
```

**2. Diagonal Forward-Right:**
```python
vx = 0.2, vy = -0.2, wz = 0.0
# Result: Robot moves at 45° angle
```

**3. Crab Walk (Strafe + Rotate):**
```python
vx = 0.0, vy = 0.3, wz = 0.5
# Result: Robot strafes left while rotating counterclockwise
```

**4. Circle Drive:**
```python
vx = 0.2, vy = 0.0, wz = 0.5
# Result: Robot drives in a curved path
```

## OrbiBot Implementation

OrbiBot uses the **Yahboom ROSMaster** expansion board which:
- Handles inverse kinematics in **hardware**
- Receives `cmd_vel` (vx, vy, wz) directly
- Controls four mecanum wheels independently
- Provides encoder feedback for odometry

**Software stack:**
```
Controller Node → /cmd_vel → ROSMaster Board → Mecanum Wheels
                   (Twist)   (Hardware IK)
```

## Safety Features

All teleop modes include:
- **Dead-man switch** (R2 trigger) - must be held for movement
- **Motor enable/disable** (L1 button) - software motor control
- **Emergency stop** (Share button) - immediate stop + disable motors
- **Command timeout** - automatic stop after 2 seconds without commands
- **Speed limiting** - configurable maximum speeds
- **Multi-gear control** - reduce speed for precision

## Testing Mecanum Movements

### Quick Test - Manual Control
```bash
# 1. Launch robot hardware
ros2 launch orbibot_bringup orbibot_basic.launch.py

# 2. Launch advanced mecanum controller
ros2 launch orbibot_teleop controller.launch.py

# 3. Enable motors (L1 button)
# 4. Select mode with D-pad
# 5. Hold R2 and use sticks to move
```

### Automated Demo
```bash
# 1. Launch robot hardware
ros2 launch orbibot_bringup orbibot_basic.launch.py

# 2. Launch demo (in separate terminal)
ros2 launch orbibot_teleop 

# Watch the robot perform all 14 movements!
```

### Manual Testing via Command Line
```bash
# Enable motors
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"

# Test strafe left
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.2, z: 0.0}}" --once

# Test diagonal
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2, y: 0.2, z: 0.0}}" --once

# Test crab walk
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.0, y: 0.2, z: 0.0}, angular: {z: 0.5}}" --once

# Stop
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{}" --once
```

## Troubleshooting

### Robot doesn't move
1. Check motors are enabled: `ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable "{enable: true}"`
2. Ensure R2 trigger is held (dead-man switch)
3. Check controller connection: `ros2 topic echo /joy`
4. Verify hardware node: `ros2 node list | grep hardware`

### Movement is jerky or unstable
1. Reduce speed: Lower `max_linear_speed` parameter
2. Increase deadzone: Higher `deadzone` parameter
3. Check battery voltage: `ros2 topic echo /orbibot/system_status`
4. Verify wheel condition and surface

### Controller not responding
1. Check device: `ls -l /dev/input/js0`
2. Test controller: `ros2 run joy joy_node`
3. Echo joy topic: `ros2 topic echo /joy`
4. Check D-pad axes: Should see axes[6] and axes[7]

## Further Reading

- [minimec_study.md](../../study/minimec_study.md) - Detailed mecanum kinematics
- [CLAUDE.md](../../CLAUDE.md) - Complete OrbiBot system documentation
- [OrbiBot Hardware Guide](../orbibot_hardware/README.md) - ROSMaster integration

## Summary

OrbiBot's mecanum wheels enable **full holonomic control** with:
- ✅ Omnidirectional movement (any direction)
- ✅ Independent rotation control
- ✅ 3 degrees of freedom (vx, vy, wz)
- ✅ Advanced patterns (diagonal, crab, circle)
- ✅ Hardware-accelerated kinematics
- ✅ Safe, multi-mode control

Experiment with the advanced controller to fully explore mecanum capabilities!