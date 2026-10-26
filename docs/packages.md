---
title: "Package Index"
type: moc
tags:
  - moc
  - packages
---

# Package Index

Thirteen packages. Each one's `README.md` is the API reference — this page is
the map, and the hub notes are the orientation.

## Layers

```
orbibot_agent · orbibot_webgui              interfaces (AI, web)
orbibot_navigation · orbibot_exploration    autonomy
orbibot_slam · orbibot_localization         state estimation
orbibot_sensors · orbibot_description       perception & model
orbibot_hardware · orbibot_msgs             ROS 2 ↔ firmware bridge
orbibot_rosmaster_firmware                  STM32, bare metal
orbibot_bringup · orbibot_teleop            orchestration & manual control
```

## All packages

| Package | Build | Owns | Hub note |
|---|---|---|---|
| `orbibot_rosmaster_firmware` | PlatformIO | Motor PID, encoders, IMU, odometry, serial protocol | [[orbibot_rosmaster_firmware]] |
| `orbibot_hardware` | ament_python | Serial bridge → `/odom`, `/imu/*`, `/joint_states` | [[orbibot_hardware]] |
| `orbibot_msgs` | ament_cmake | Custom messages and services | [[orbibot_msgs]] |
| `orbibot_description` | ament_cmake | URDF/Xacro, meshes, RViz configs | [[orbibot_description]] |
| `orbibot_sensors` | ament_python | RPLidar A1, RealSense D435, obstacle detector | [[orbibot_sensors]] |
| `orbibot_localization` | ament_python | Madgwick + EKF → `odom → base_footprint` | [[orbibot_localization]] |
| `orbibot_slam` | ament_python | slam_toolbox mapping and localization | [[orbibot_slam]] |
| `orbibot_navigation` | ament_cmake | Nav2 params, launch, saved maps | [[orbibot_navigation]] |
| `orbibot_exploration` | ament_python | BFS frontier explorer | [[orbibot_exploration]] |
| `orbibot_teleop` | ament_python | Gamepad teleop — **dormant** | [[orbibot_teleop]] |
| `orbibot_bringup` | ament_python | Cross-package launch orchestration | [[orbibot_bringup]] |
| `orbibot_webgui` | ament_python | rosbridge + WebRTC backend, React frontend | [[orbibot_webgui]] |
| `orbibot_agent` | ament_python | Multi-LLM agent, MCP server, CLI, 62 tools | [[orbibot_agent]] |

## Gone, and staying gone

| Package | Removed | Why |
|---|---|---|
| `orbibot_gazebo` | 2026-08-03 | Claude Code runs on the Pi, which *is* the robot. Pulled 202 MB of `gz` onto a GPU-less machine. In history if it is ever needed on a laptop. |
| `orbibot_ai`, `orbibot_mcp_server` | earlier | Replaced by `orbibot_agent`. Do not recreate. |

## Rules that apply to every package

- Read the hub note **and** `src/<pkg>/README.md` before editing; update both
  **after** any change to functionality, API, launch, config or dependencies —
  including deletions. See `.claude/rules/docs-sync.md`.
- Each package launches only its own nodes. Cross-package composition belongs
  in [[orbibot_bringup]].
- Naming follows `.claude/rules/code-style.md`.

## Related

[[docs/README|Docs home]] · [[system-overview]] · [[backlog-moc]] · [[learn-moc]]
