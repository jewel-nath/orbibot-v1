# orbibot_bringup

The launch files that start several packages together. Every other package
launches only its own nodes; this one puts them together. That rule keeps,
say, the SLAM launch from quietly starting a second hardware node that would
fight the first over the serial port.

**Status:** `robot.launch.py` is how the robot was started. The mapping and
exploration launches run on top of it.

## The robot base: `robot.launch.py`

Start this first, in its own terminal.

```bash
ros2 launch orbibot_bringup robot.launch.py
ros2 launch orbibot_bringup robot.launch.py use_camera:=true   # with the RealSense
```

| When | What starts | Package |
|---|---|---|
| At once | The robot model and its TF (`robot_state_publisher`) | `orbibot_description` |
| At once | `hardware_node` and `system_monitor`; 6 s later, a call that enables the motors | `orbibot_hardware` |
| After 3 s | Madgwick and the EKF | `orbibot_localization` |
| After 5 s | The RPLIDAR A1, as a separate `ros2 launch` process | `orbibot_sensors` |
| If `use_camera:=true` | The RealSense D435 | `orbibot_sensors` |

## Mapping: `mapping.launch.py`

slam_toolbox in mapping mode, plus the Nav2 navigation stack. No map server:
SLAM provides the map.

```bash
ros2 launch orbibot_bringup mapping.launch.py
```

| Argument | Default |
|---|---|
| `nav_params_file` | `orbibot_navigation/config/nav2_params.yaml` |

This default is the AMCL variant; `nav2_params_slam.yaml` is the one written
for live SLAM. See [known issues](known-issues.md).

## Exploration: `exploration.launch.py`

The same as mapping, plus the frontier explorer from `orbibot_exploration`.

```bash
ros2 launch orbibot_bringup exploration.launch.py
ros2 topic pub --once /orbibot/exploration/command std_msgs/String "data: start"
```

| Argument | Default |
|---|---|
| `nav_params_file` | `orbibot_navigation/config/nav2_params_slam.yaml` |

## How they stack

```
robot.launch.py (terminal 1)        then one of (terminal 2)
----------------------------        ------------------------
description                         mapping.launch.py
hardware + system monitor             SLAM + Nav2
Madgwick + EKF (after 3 s)          exploration.launch.py
LiDAR (after 5 s)                     SLAM + Nav2 + frontier explorer
camera (optional)
```

Neither mapping nor exploration starts the robot base itself.

## Dependencies

`orbibot_description`, `orbibot_hardware`, `orbibot_sensors`,
`orbibot_localization`, `orbibot_slam`, `orbibot_navigation` and
`orbibot_exploration`.
