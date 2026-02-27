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
| `orbibot_navigation` | ament_cmake | Planned | Nav2 params, launch, maps |
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
- **Odom topic**: `/odometry/filtered` (EKF output) for Nav2, raw `/odom` from control_manager
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

| Skill | Description |
|-------|-------------|
| `ros2_node_creation` | Node templates with QoS profiles (Python & C++) |
| `ros2_launch_config` | Launch file composition, parameter management |
| `ros2_service_action` | Service/Action server-client patterns |
| `ros2_messaging` | Pub/Sub patterns, thread-safe buffers |
| `ros2_testing` | Unit, Integration, E2E test strategies |
| `ros2_lifecycle` | Managed (Lifecycle) Node templates |
| `ros2_transforms` | TF2 management patterns |
| `ros2_diagnostics` | Health monitoring with diagnostic_updater |
| `ros2_bag` | Bag recording and replay utilities |
| `ai_integration` | LLM provider patterns, tool calling, MCP |

## Deprecated Packages

The following packages have been replaced by `orbibot_agent` and will be removed:
- `orbibot_ai` → Use `orbibot_agent` (unified AI package)
- `orbibot_mcp_server` → Use `orbibot_agent` (MCP server included)