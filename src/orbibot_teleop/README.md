# orbibot_teleop

Advanced teleoperation package for OrbiBot with full mecanum wheel control support.

## Quick Start

```bash
# Gamepad control (PS4/PS5 DualSense)
ros2 launch orbibot_teleop controller.launch.py

# Keyboard control (alternative)
ros2 launch orbibot_teleop controller.launch.py use_keyboard:=true

# Custom device
ros2 launch orbibot_teleop controller.launch.py device:=/dev/input/js1
```

## Features

- Full mecanum control: forward/backward, strafe, rotation, diagonal, crab walk
- 7 movement modes covering all holonomic capabilities
- Safety: dead-man switch (R2), emergency stop, motor enable/disable
- Multi-gear: speed (33%/66%/100%) and angular (25%/50%/75%/100%) gears
- PS4/PS5 DualSense and keyboard support

## Controller Mapping

**Sticks:**
- Left Stick: Forward/back + strafe left/right (in NORMAL mode)
- Right Stick X: Rotation

**Buttons:**
- R2: Hold to enable movement (dead-man switch)
- L1: Toggle motor enable/disable
- Triangle/X: Speed gear up/down
- Square/Circle: Angular gear up/down
- Share: Emergency stop

**Movement Modes:**

| Mode | Activation | Description |
|------|------------|-------------|
| NORMAL | D-pad UP | Full 3-DOF control |
| STRAFE | D-pad RIGHT | Sideways movement only |
| DIAGONAL | D-pad DOWN | 45-degree diagonal movements |
| ROTATE | D-pad LEFT | Rotation in place only |
| CRAB | R3 button | Rotate while strafing |
| CIRCLE | L3 button | Drive in arcs (forward + turn) |
| PIVOT_STRAFE | — | Strafe + rotate combined |

## Topics

**Published:**
- `/cmd_vel` (Twist) — Velocity commands

**Subscribed:**
- `/joy` (Joy) — Joystick input

**Services Called:**
- `/orbibot/set_motor_enable` (SetMotorEnable) — Motor control

## Configuration

Edit `config/controller.yaml`:

```yaml
controller:
  ros__parameters:
    max_linear_speed: 0.3      # m/s
    max_angular_speed: 1.0     # rad/s
    deadzone: 0.08             # Joystick deadzone
    enable_motors_on_start: false
```

## Troubleshooting

### Controller not detected
```bash
ls -l /dev/input/js*
ros2 run joy joy_node
```

### Robot doesn't move
1. Check motors are enabled (L1 button or service call)
2. Hold R2 trigger (dead-man switch)
3. Check battery voltage
