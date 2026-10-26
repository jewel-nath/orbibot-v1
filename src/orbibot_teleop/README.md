# orbibot_teleop

Gamepad driving for OrbiBot: a PlayStation controller on `/joy` becomes
`/cmd_vel`, with mecanum movement modes, a dead-man trigger and speed gears.

**Status:** written, and switched off. The robot was driven with a gamepad
in 2025; since the web dashboard arrived, driving goes through the dashboard
only (its on-screen controls and keyboard, sent over rosbridge). This package stays as a fallback that does not
depend on the network. Until it is needed:

- don't start `controller.launch.py`;
- `rosdep install` pulls in `joy`, because `package.xml` depends on it. That
  doesn't mean the package is in use.

It publishes straight to `/cmd_vel`, so before it comes back it needs its
own topic and a priority below the safety stop; see
[the command pipeline design](../../docs/architecture/command-pipeline.md).

## Launch

```bash
ros2 launch orbibot_teleop controller.launch.py                      # PS4 or PS5 controller
ros2 launch orbibot_teleop controller.launch.py device:=/dev/input/js1
ros2 launch orbibot_teleop controller.launch.py use_keyboard:=true   # keyboard instead
```

| Argument | Default |
|---|---|
| `device` | `/dev/input/js0` |
| `max_linear_speed` | `0.3` (m/s) |
| `max_angular_speed` | `1.0` (rad/s) |
| `use_keyboard` | `false` (uses `teleop_twist_keyboard` in an xterm) |

## Controls

| Control | What it does |
|---|---|
| Left stick | Forward and back, and sideways |
| Right stick, left and right | Turn |
| R2 (hold) | Dead-man switch: the robot moves only while it is held |
| L1 | Motors on or off (calls `/orbibot/set_motor_enable`) |
| Triangle / X | Speed gear up or down: 33 %, 66 %, 100 % |
| Square / Circle | Turning gear up or down: 25 %, 50 %, 75 %, 100 % |
| Share | Emergency stop |

### Movement modes

A mecanum robot has three independent motions: forward (vx), sideways (vy)
and turning (wz). The modes limit the sticks to one pattern at a time.

| Mode | Select with | Motion |
|---|---|---|
| Normal | D-pad up | All three motions freely |
| Strafe | D-pad right | Sideways only |
| Diagonal | D-pad down | 45° diagonals |
| Rotate | D-pad left | Turning on the spot only |
| Crab | R3 | Sideways while turning |
| Circle | L3 | Arcs: forward while turning |

## Topics

| Topic | Type | Direction |
|---|---|---|
| `/joy` | `sensor_msgs/Joy` | in |
| `/cmd_vel` | `geometry_msgs/Twist` | out |

## Configuration

`config/controller.yaml`:

```yaml
controller:
  ros__parameters:
    max_linear_speed: 0.3          # m/s
    max_angular_speed: 1.0         # rad/s
    deadzone: 0.08                 # stick dead zone
    enable_motors_on_start: false  # turn the motors on with L1
```

## If the robot doesn't move

1. Check that the controller is seen: `ls -l /dev/input/js*`, then
   `ros2 run joy joy_node` and `ros2 topic echo /joy`.
2. Turn the motors on with L1, and hold R2 while you move the sticks.
3. Check the battery voltage on `/orbibot/system_status`.
