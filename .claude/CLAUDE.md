# OrbiBot — Development Context

This file complements the root `CLAUDE.md` (workflow rules, coding standards, build commands, hardware reference). This file provides development context, package status, and conventions.

## Package Structure & Status

| Package | Type | Status | Description |
|---------|------|--------|-------------|
| `orbibot_rosmaster_firmware` | PlatformIO | Working | STM32 motor driver firmware |
| `orbibot_description` | ament_cmake | Working | URDF/xacro, meshes, robot_state_publisher |
| `orbibot_hardware` | ament_python | Working | Motor driver, IMU, firmware odometry (/odom), encoder reading |
| `orbibot_msgs` | ament_cmake | Working | Custom messages and services |
| `orbibot_sensors` | ament_python | Working | RPLidar A1, RealSense D435 launch/config |
| `orbibot_teleop` | ament_python | Working | Joystick/controller teleop |
| `orbibot_localization` | ament_python | Working | robot_localization EKF (odom + IMU fusion) |
| `orbibot_slam` | ament_python | Working | slam_toolbox mapping + localization |
| `orbibot_bringup` | ament_python | Working | System-level launch orchestration |
| `orbibot_webgui` | ament_python | Active | Web-based GUI (in development) |
| `orbibot_navigation` | ament_cmake | Working | Nav2 params, launch, maps |
| `orbibot_exploration` | ament_python | Planned | Custom BFS frontier explorer |
| `orbibot_agent` | ament_python | Working | Unified AI Agent (multi-LLM, MCP, CLI) |

## Project Roadmap

1. **Current**: `orbibot_webgui` — improvements and new features
2. **Next**: `orbibot_navigation` + `orbibot_exploration` — full autonomous operation
3. **Then**: Refactor all packages — clean codebase, resolve odom drift
4. **Future**: Enhanced AI features — navigation tools, vision integration

## Known Issues

- Occasional odometry drift — encoder CPR/wheel radius calibration may need tuning

## Key Conventions

- **Base frame**: Always use `base_footprint` (not `base_link`) in all configs
- **TF chain**: `map → odom → base_footprint → base_link → sensor_links`
- **Odom topic**: `/odometry/filtered` (EKF output) for Nav2, raw `/odom` from hardware_node
- **Launch messages**: `[PackageName] Description — key: value` format
- **Single-package launches**: Each package only launches its own nodes. Cross-package orchestration lives in `orbibot_bringup`
- **Maintainer**: Jewel Nath <jewel.nath@orbitax.com>

## Navigation Architecture

- **Controller**: MPPI with `Omni` motion model (mecanum)
- **Planner**: NavfnPlanner with A*
- **Localization**: AMCL with `nav2_amcl::OmniMotionModel`
- **Velocity chain**: controller (`cmd_vel_nav`) → velocity_smoother (`cmd_vel_smoothed`) → collision_monitor → `cmd_vel`
- **Footprint**: 350mm x 250mm, inflation_radius: 0.55m

## AI Agent Architecture

- **Multi-LLM Support**: Gemini, Claude (Anthropic), Kimi (Moonshot), Ollama (local)
- **Interfaces**: HTTP API (web GUI), MCP server (Claude Desktop), Terminal CLI
- **Tools**: 8 core tools (move, sensors, diagnostics) + extensible registry
- **Safety**: Velocity limits, duration caps, emergency stop
- **Native ROS 2**: Direct rclpy (no rosbridge overhead)

### AI Agent Quick Start

```bash
# Set API key for your preferred provider
export GEMINI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export MOONSHOT_API_KEY="your-key"

# Terminal CLI
ros2 run orbibot_agent chat_cli

# HTTP server for web GUI
ros2 launch orbibot_agent chat_server.launch.py

# MCP server for Claude Desktop
ros2 run orbibot_agent mcp_server
```

### Claude Desktop Configuration

Add to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "orbibot": {
      "command": "bash",
      "args": [
        "-lc",
        "source /opt/ros/jazzy/setup.bash && source ~/orbibot_ws/install/setup.bash && ros2 run orbibot_agent mcp_server"
      ]
    }
  }
}
```

## Available Skills

Skills in `.claude/skills/` are auto-discovered. All names use **snake_case**. See `.claude/skills/README.md` for the full index and cross-references.

| Skill | Description |
|-------|-------------|
| **ROS 2 core** | |
| `ros2_node_creation` | Node templates with QoS profiles (Python & C++) |
| `ros2_launch_config` | Launch file composition, parameter management |
| `ros2_service_action` | Service/Action server-client patterns |
| `ros2_messaging` | Pub/Sub patterns, thread-safe buffers |
| `ros2_testing` | Unit, Integration, E2E test strategies (Clean Arch) |
| `ros2_lifecycle` | Managed (Lifecycle) Node templates |
| `ros2_transforms` | TF2 management patterns |
| `ros2_diagnostics` | Health monitoring with diagnostic_updater |
| `ros2_bag` | Bag recording and replay utilities |
| **Bringup & architecture** | |
| `robot_bringup` | systemd, launch layering, udev, watchdog, graceful shutdown |
| `robot_architecture` | Design patterns, BT/FSM, state estimation |
| `robotics_design_patterns` | Behavior trees, HAL, safety, sim-to-real |
| `robotics_software_principles` | SOLID, clean architecture, DI for robotics |
| **Perception & sensors** | |
| `robot_perception` | Cameras, LiDAR, depth, calibration, detection, fusion |
| `camera_vision` | Calibration, OpenCV, detection, depth pipelines |
| `lidar_pointcloud` | PCL, Open3D, filtering, ICP, segmentation |
| `sensor_fusion_slam` | EKF/UKF, slam_toolbox, Cartographer, RTAB-Map |
| **Navigation & control** | |
| `nav2` | Nav2 stack, costmaps, planners, controllers, recovery |
| `path_planning` | A*, RRT, costmaps, waypoint following |
| `control_systems` | PID, LQR, MPC, trajectories |
| `realtime_motor_control` | Motor drivers, PID tuning, PREEMPT_RT |
| **Hardware, safety & security** | |
| `microcontrollers` | STM32, firmware, HAL (e.g. Yahboom ROSMaster) |
| `serial_can_protocols` | UART, CAN, EtherCAT — serial to firmware |
| `safety_systems` | Watchdogs, functional safety |
| `robotics_security` | SROS2, DDS security, hardening, network segmentation |
| **Modeling, web & tooling** | |
| `robot_modeling` | URDF, Xacro, TF2, robot_state_publisher |
| `ros2_web_integration` | FastAPI/Flask bridges, WebSocket, MJPEG, REST APIs |
| `robotics_testing` | Test pyramid, launch_testing, mock hardware, CI/CD |
| `docker_ros2_development` | Docker, docker-compose, DDS in containers, GPU passthrough |
| **Simulation & AI** | |
| `gazebo` | Gazebo Classic/Sim, SDF worlds, physics, sensor models, ROS2 integration |
| `sim_to_real` | Domain transfer, reality gap, domain adaptation, system identification |
| `ros2_control` | ros2_control hardware abstraction, controllers, transmissions, joint limits |
| `edge_ml_deployment` | TensorRT, ONNX, quantization, edge inference on RPi/Jetson |
| `learning_robotics` | Imitation learning, behavior cloning, DAgger, RL, VLA models |

## Workflow Guides

Multi-skill workflow guides are in `.claude/guides/`:

| Guide | Description |
|-------|-------------|
| `hardware-integration.md` | End-to-end: wiring → first ROS2 topic (4-8h checklist) |
| `robot-bringup.md` | First power-on checklist for a new robot platform |
| `sensor-calibration.md` | Complete calibration workflow (camera, LiDAR, IMU) |
| `sim-to-real-pipeline.md` | Full simulation → physical robot transfer workflow |

## Deprecated Packages

The following packages have been replaced by `orbibot_agent` and will be removed:
- `orbibot_ai` → Use `orbibot_agent` (unified AI package)
- `orbibot_mcp_server` → Use `orbibot_agent` (MCP server included)