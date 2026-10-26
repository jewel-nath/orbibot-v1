# Packages

The workspace has 13 packages in `src/`: 12 ROS 2 packages built by colcon,
and the STM32 firmware, which is a PlatformIO project (it carries a
`COLCON_IGNORE`). Each package's `README.md` is its reference: topics,
services, parameters and launch files.

## Layers

```
orbibot_agent · orbibot_webgui              interfaces: AI and web
orbibot_navigation · orbibot_exploration    autonomy
orbibot_slam · orbibot_localization         state estimation
orbibot_sensors · orbibot_description       sensors and the robot model
orbibot_hardware · orbibot_msgs             the bridge between ROS 2 and the firmware
orbibot_rosmaster_firmware                  the STM32
orbibot_bringup · orbibot_teleop            starting it all, and manual driving
```

## All packages

| Package | Build | What it does | Status |
|---|---|---|---|
| [orbibot_rosmaster_firmware](../src/orbibot_rosmaster_firmware/README.md) | PlatformIO | Motor PID, encoders, IMU, odometry, the serial protocol, the safety timeout | Runs on the robot; bench-tested |
| [orbibot_hardware](../src/orbibot_hardware/README.md) | ament_python | Serial bridge: `/odom`, `/imu/*`, `/joint_states`, motor services | Used on the robot |
| [orbibot_msgs](../src/orbibot_msgs/README.md) | ament_cmake | Custom messages and services | Used on the robot |
| [orbibot_description](../src/orbibot_description/README.md) | ament_cmake | URDF/Xacro model, meshes, RViz setups | Used on the robot |
| [orbibot_sensors](../src/orbibot_sensors/README.md) | ament_python | RPLIDAR A1, RealSense D435, obstacle detector | LiDAR used; camera off by default; detector untested |
| [orbibot_localization](../src/orbibot_localization/README.md) | ament_python | Madgwick and the EKF: `odom → base_footprint` | Used on the robot; not tuned |
| [orbibot_slam](../src/orbibot_slam/README.md) | ament_python | slam_toolbox mapping and localisation | Used on the robot |
| [orbibot_navigation](../src/orbibot_navigation/README.md) | ament_cmake | Nav2 parameters, launch file, saved maps | Set up and run on the robot; not measured |
| [orbibot_exploration](../src/orbibot_exploration/README.md) | ament_python | Frontier exploration on top of Nav2 | Written, untested |
| [orbibot_bringup](../src/orbibot_bringup/README.md) | ament_python | The launch files that start several packages | Used on the robot |
| [orbibot_webgui](../src/orbibot_webgui/README.md) | ament_python | rosbridge and WebRTC back end, React dashboard | Used on the robot |
| [orbibot_agent](../src/orbibot_agent/README.md) | ament_python | LLM agent with 58 robot tools: HTTP chat, terminal CLI, MCP server | Runs on the robot |
| [orbibot_teleop](../src/orbibot_teleop/README.md) | ament_python | Gamepad driving | Switched off |

## Removed packages

| Package | Removed | Why |
|---|---|---|
| `orbibot_gazebo` | 2026-08-03 | V1 runs on the Raspberry Pi, which has no GPU for simulation; it pulled 202 MB of Gazebo onto it. It is in the git history. |
| `orbibot_ai`, `orbibot_mcp_server` | before this repository | Replaced by `orbibot_agent`. |

## Rules for every package

- Each package launches only its own nodes. Launch files that start several
  packages belong in `orbibot_bringup`.
- When you change a package's behaviour, its API, launch files, config or
  dependencies, update its `README.md` in the same change, and its
  `CHANGELOG.md` and `known-issues.md` where they apply. See
  [CONTRIBUTING.md](../CONTRIBUTING.md).
