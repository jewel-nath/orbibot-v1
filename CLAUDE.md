# OrbiBot — Comprehensive Project Guide

**OrbiBot**: Mecanum-wheeled mobile robot with ROS 2 Jazzy, Raspberry Pi 5, and Yahboom ROSMaster V3.0 expansion board.

> **Quick Start**: See [Quick Start Guide](#quick-start) below for common operations.

---

## Project Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              HARDWARE LAYER                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                      │
│  │ RPLidar A1  │    │ ICM-20948   │    │  Encoders   │                      │
│  │ (USB/Serial)│    │   (SPI2)    │    │ (Quadrature)│                      │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                      │
│         │                  │                  │                              │
│  ┌─────────────────────────────────────────────────────┐                     │
│  │  Yahboom ROSMaster V3.0 (STM32F103RCT6 @ 72MHz)     │                     │
│  │  • FreeRTOS with 4 tasks (100Hz control, 50Hz IMU)  │                     │
│  │  • Motor PID + Mecanum kinematics                   │                     │
│  │  • Serial protocol @ 115200 baud                    │                     │
│  └───────────────────────┬─────────────────────────────┘                     │
│                          │ USB Serial (/dev/motordriver)                     │
└──────────────────────────┼──────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ROS 2 LAYER (RPi 5)                           │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ orbibot_hardware │  │ orbibot_sensors │  │ orbibot_description│           │
│  │                 │  │                 │  │                    │           │
│  │ • Serial bridge │  │ • RPLidar A1    │  │ • URDF/Xacro       │           │
│  │ • /odom publish │  │ • RealSense D435│  │ • TF frames        │           │
│  │ • IMU publish   │  │ • obstacle_detector│ │ • RViz config    │           │
│  └────────┬────────┘  └────────┬────────┘  └─────────────────┘              │
│           │                    │                                            │
│           │         ┌──────────┴──────────┐                                 │
│           │         │                     │                                 │
│           │    ┌────┴────┐          ┌────┴────┐                           │
│           │    │ /scan   │          │/camera/*│                           │
│           │    │ 10Hz    │          │ 15Hz    │                           │
│           │    └────┬────┘          └─────────┘                           │
│           │         │                                                      │
│           └────┬────┴────────────────┬────────────────┐                    │
│                │                     │                │                    │
│           ┌────┴────┐          ┌────┴────┐      ┌────┴────┐               │
│           │/imu/*   │          │/joint_states│   │/tf      │               │
│           │ 50Hz    │          │ 50Hz        │   │ 100Hz   │               │
│           └────┬────┘          └─────────────┘   └─────────┘               │
│                │                                                            │
│                ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │              orbibot_localization (EKF Fusion)                      │   │
│  │                                                                     │   │
│  │   /imu/data_raw ──┐                                                 │   │
│  │   /imu/mag ───────┼──→ imu_filter_madgwick → /imu/data_filtered ─┐ │   │
│  │                    │                                              │ │   │
│  │   /odom (velocity) ├─────────────────────────────────────────────┼─┼──→│
│  │   (wheel odometry) │                                             │ │   │
│  │                    │                                             │ │   │
│  │                    └─────────────────────────────────────────────┘ │   │
│  │                                                                   ▼    │
│  │                      /odometry/filtered (20Hz) + odom→base_footprint TF│
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   orbibot_slam (slam_toolbox)                       │   │
│  │                                                                     │   │
│  │   • Subscribes: /scan, TF (odom→base_footprint)                    │   │
│  │   • Publishes: /map, map→odom TF                                   │   │
│  │   • Modes: mapping (async_slam_toolbox_node)                       │   │
│  │            localization (localization_slam_toolbox_node)           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 Nav2 Navigation Stack                               │   │
│  │   • Path planning (NavfnPlanner with A*)                             │   │
│  │   • MPPI controller (Model Predictive Path Integral)                │   │
│  │   • Costmaps (obstacle avoidance)                                   │   │
│  │   • Behavior trees (NavigateToPose, NavigateThroughPoses)           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                 orbibot_agent (AI Integration)                      │   │
│  │   • Multi-LLM support (Gemini, Claude, Kimi, Ollama)               │   │
│  │   • HTTP API for web GUI (chat_server)                             │   │
│  │   • MCP server for Claude Desktop (mcp_server)                     │   │
│  │   • Terminal CLI (chat_cli)                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Package Reference

| Package | Purpose | Key Files | Status |
|---------|---------|-----------|--------|
| **orbibot_rosmaster_firmware** | STM32 firmware | `src/main.c`, `include/orbibot_config.h` | ✅ Production |
| **orbibot_description** | Robot URDF/TF | `urdf/orbibot.urdf.xacro` | ✅ Production |
| **orbibot_hardware** | ROS 2 serial bridge | `hardware_node.py`, `rosmaster_driver.py` | ✅ Production |
| **orbibot_sensors** | LiDAR + Camera | `lidar.launch.py`, `camera.launch.py` | ✅ Production |
| **orbibot_localization** | EKF sensor fusion | `ekf_params.yaml` | ✅ Production |
| **orbibot_slam** | SLAM mapping | `slam_params.yaml` | ✅ Production |
| **orbibot_navigation** | Nav2 stack | `nav2_params.yaml` | ✅ Production |
| **orbibot_teleop** | Gamepad control | `controller.launch.py` | ✅ Production |
| **orbibot_bringup** | System launch | `robot.launch.py`, `mapping.launch.py` | ✅ Production |
| **orbibot_msgs** | Custom messages | `SystemStatus.msg`, `SafetyStatus.msg` | ✅ Production |
| **orbibot_agent** | AI Agent (multi-LLM) | `chat_server`, `mcp_server`, `chat_cli` | ✅ Production |

---

## ROS2 Package README Workflow

**Follow these rules every time when working with any ROS 2 package:**

- **Before** reading or editing any ROS 2 package → read `src/<package_name>/README.md` first (e.g. `src/orbibot_hardware/README.md`).
- **After** changing a package (functionality, API, launch/config, or dependencies) → update that package’s `README.md` if needed (features, parameters, usage, deps).

Detailed workflow: `.claude/rules/ros2_package_readme_workflow.md`.

---

## Quick Start

### 1. Build Firmware (First Time)
```bash
cd src/orbibot_rosmaster_firmware
~/.platformio/penv/bin/pio run                  # Build
# Set BOOT0=HIGH, press RESET, then:
~/.platformio/penv/bin/pio run --target upload  # Upload
~/.platformio/penv/bin/pio device monitor       # Verify (115200 baud)
```

### 2. Build ROS 2 Packages
```bash
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
```

### 3. Launch Robot Base
```bash
# Terminal 1: Robot base (description + hardware + LiDAR + EKF)
ros2 launch orbibot_bringup robot.launch.py

# Terminal 2: Teleop control
ros2 launch orbibot_teleop controller.launch.py
```

### 4. SLAM Mapping
```bash
# Terminal 3: SLAM
ros2 launch orbibot_bringup mapping.launch.py

# Drive around, then save map:
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
  "{name: {data: '/home/orbibot/maps/my_map'}}"
ros2 run nav2_map_server map_saver_cli -f /home/orbibot/maps/my_map
```

### 5. Autonomous Navigation
```bash
# Terminal 3: Navigation (with saved map)
ros2 launch orbibot_navigation navigation.launch.py map:=$HOME/maps/my_map.yaml

# Terminal 4: Send navigation goal
ros2 topic pub /goal_pose geometry_msgs/PoseStamped \
  "{header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: 1.0}}}"
```

### 6. AI Agent (Optional)
```bash
# Terminal CLI with multi-LLM support
ros2 run orbibot_agent chat_cli

# HTTP API for web GUI
ros2 launch orbibot_agent chat_server.launch.py

# MCP server for Claude Desktop
ros2 run orbibot_agent mcp_server
```

---

## Key Configuration Files

| File | Purpose | Key Parameters |
|------|---------|----------------|
| `orbibot_hardware/config/hardware_params.yaml` | Serial, safety, odometry | `serial_port`, `cmd_timeout`, `covariance_decay` |
| `orbibot_localization/config/ekf_params.yaml` | EKF fusion | `odom0_config`, `imu0_config`, `process_noise_covariance` |
| `orbibot_slam/config/slam_params.yaml` | SLAM mapping | `min_laser_range`, `loop_search_maximum_distance` |
| `orbibot_navigation/config/nav2_params.yaml` | Navigation | `controller_frequency`, `planner_plugin` |
| `orbibot_sensors/config/rplidar_params.yaml` | LiDAR | `scan_mode`, `serial_port` |
| `orbibot_teleop/config/controller.yaml` | Gamepad | `axis_linear`, `axis_angular` |
| `orbibot_agent/config/agent_params.yaml` | AI configuration | `llm_providers`, `safety` |

---

## Hardware Specifications

### Robot Geometry
| Parameter | Value | Notes |
|-----------|-------|-------|
| Wheel radius | 50mm | 100mm mecanum wheels |
| Track width | 360mm | Left-right wheel separation |
| Wheelbase | 260mm | Front-rear wheel separation |
| Encoder resolution | 1320 PPR | 11 PPR × 30:1 gear × 4 quadrature |
| Mecanum layout | ABBA | A=+45° rollers, B=-45° rollers |

### Motor/Encoder Mapping
| Motor | Position | PWM Timer | Encoder Timer | Pins |
|-------|----------|-----------|---------------|------|
| M1 | Front-Left | TIM8 CH1/CH2 | TIM2 | PA11/PA8, PA15/PB3 |
| M2 | Back-Left | TIM8 CH3/CH4 | TIM4 | PB0/PB1, PB6/PB7 |
| M3 | Front-Right | TIM1 CH4/CH1 | TIM5 | PC6/PC7, PA0/PA1 |
| M4 | Back-Right | TIM1 CH2/CH3 | TIM3 | PC8/PC9, PA6/PA7 |

### Battery (4S LiFePO4)
| State | Voltage | Action |
|-------|---------|--------|
| Full | 14.6V | — |
| Nominal | 12.8V | Normal operation |
| Low warning | 11.0V | Warning buzzer |
| Critical | 10.5V | Emergency motor stop |

### Sensors
| Sensor | Interface | Rate | Topics |
|--------|-----------|------|--------|
| RPLidar A1 | USB Serial (/dev/lidar) | 10Hz | `/scan` |
| RealSense D435 | USB 3.0 | 15Hz | `/camera/color/image_raw`, `/camera/depth/image_rect_raw` |
| ICM-20948 IMU | SPI2 (PB12-PB15) | 50Hz | `/imu/data_raw`, `/imu/mag` |

---

## Data Flow Reference

### Odometry Pipeline
```
Firmware encoders → mecanum_kinematics → /odom (velocity)
                                          ↓
Madgwick filter ← /imu/data_raw + /imu/mag → /imu/data_filtered
                                          ↓
                                    EKF fusion
                                          ↓
                              /odometry/filtered (fused)
                                          ↓
                                   SLAM / Nav2
```

### SLAM Pipeline
```
/scan (LiDAR) ──┐
                ├──→ slam_toolbox → /map + map→odom TF
/odometry/filtered ──┘
```

### Navigation Pipeline
```
/map (static or SLAM) ──┐
                        ├──→ Nav2 costmap → MPPI controller → /cmd_vel
/scan (LiDAR) ──────────┘
```

### AI Agent Pipeline
```
User Input → LLM Provider (Gemini/Claude/Kimi/Ollama)
                ↓
         Tool Decision (move, get_sensor, etc.)
                ↓
         ROS 2 Tool Execution
                ↓
         Robot Response
```

---

## Debugging Commands

### Firmware Level
```bash
# Test suite
cd src/orbibot_rosmaster_firmware/tests
python3 run_all_tests.py --port /dev/motordriver

# Individual tests
python3 test_encoder.py       # Verify encoder counting
python3 test_imu.py           # Check IMU data
python3 test_motor_speed.py   # Motor PWM test
python3 test_beep.py          # Buzzer test

# Serial monitor
screen /dev/motordriver 115200  # Ctrl+A K to quit
```

### ROS 2 Level
```bash
# Check topic rates
ros2 topic hz /scan              # Should be ~10Hz
ros2 topic hz /odom              # Should be ~20Hz
ros2 topic hz /imu/data_filtered # Should be ~50Hz
ros2 topic hz /odometry/filtered # Should be ~20Hz

# Inspect data
ros2 topic echo /odom --once
ros2 topic echo /orbibot/system_status

# TF tree
ros2 run tf2_tools view_frames   # Generates frames.pdf

# Node graph
ros2 run rqt_graph rqt_graph

# Service calls
ros2 service call /orbibot/set_motor_enable orbibot_msgs/srv/SetMotorEnable '{enable: true}'
ros2 service call /orbibot/reset_odometry orbibot_msgs/srv/ResetOdometry '{}'
```

### AI Agent Level
```bash
# Test chat CLI
ros2 run orbibot_agent chat_cli

# Test HTTP API
curl -X POST http://localhost:8082/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "what is your battery level?"}'

# Check available providers
curl http://localhost:8082/api/providers
```

### System Level
```bash
# Check device connections
ls -la /dev/motordriver /dev/lidar

# Monitor system resources
ros2 topic echo /orbibot/system_status_enriched  # CPU%, RAM%, temp

# Check logs
ros2 launch orbibot_bringup robot.launch.py 2>&1 | tee robot.log
```

---

## Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| **Motors don't spin** | BOOT0 not LOW after upload | Set BOOT0=LOW, press RESET |
| **No serial data** | Wrong port or permissions | Check `/dev/motordriver`, add udev rules |
| **Encoder wrong direction** | Wiring or config error | Verify M1-M4 mapping in `orbibot_config.h` |
| **IMU returns zeros** | SPI wiring or WHO_AM_I fail | Check PB12-PB15, verify returns 0xEA |
| **Odometry drift** | Wrong wheel radius/encoder CPR | Verify 50mm radius, 1320 CPR in config |
| **SLAM not building map** | No /scan or wrong TF | Check LiDAR publishing, verify odom→base_footprint TF |
| **Navigation fails** | No map or localization | Load map first, check AMCL particles |
| **High CPU usage** | Camera + SLAM + Nav2 | Disable camera pointcloud, lower SLAM rate |
| **AI agent not responding** | No API key set | Set GEMINI_API_KEY, ANTHROPIC_API_KEY, etc. |

---

## Design Decisions

### Why Velocity-Only Odometry Fusion?
The EKF is configured with `odom0_config` positions=false. This prevents wheel encoder position drift from accumulating in the EKF state. Only velocities are fused, with IMU providing absolute yaw correction.

### Why Madgwick + EKF (not direct IMU fusion)?
Madgwick filter runs at 50Hz on raw IMU data to produce drift-free orientation using magnetometer. EKF then fuses this with wheel odometry at 20Hz. This two-stage approach provides better yaw accuracy than EKF alone.

### Why slam_toolbox (not gmapping)?
slam_toolbox provides:
- Better loop closure for long sessions
- Serialization for localization mode
- Ceres solver for graph optimization
- Lower CPU usage on Raspberry Pi

### Why orbibot_agent (unified AI package)?
Instead of separate `orbibot_ai` and `orbibot_mcp_server` packages:
- Single codebase for all AI interfaces
- Multi-LLM support (Gemini, Claude, Kimi, Ollama)
- Same tools work for web GUI, MCP, and CLI
- Native ROS 2 (rclpy) without rosbridge overhead
- Easier maintenance and feature parity

---

## File Organization

```
OrbiBot/
├── src/
│   ├── orbibot_rosmaster_firmware/   # STM32 firmware (PlatformIO)
│   │   ├── src/                      # C source files
│   │   ├── include/                  # Headers (orbibot_config.h)
│   │   ├── tests/                    # Python test suite
│   │   └── README.md                 # Firmware documentation
│   ├── orbibot_description/          # URDF, meshes, RViz
│   ├── orbibot_hardware/             # ROS 2 serial bridge
│   ├── orbibot_sensors/              # LiDAR, camera, obstacle detector
│   ├── orbibot_localization/         # EKF sensor fusion
│   ├── orbibot_slam/                 # slam_toolbox wrapper
│   ├── orbibot_navigation/           # Nav2 configuration
│   ├── orbibot_teleop/               # Gamepad teleop
│   ├── orbibot_bringup/              # System launch files
│   ├── orbibot_msgs/                 # Custom messages
│   └── orbibot_agent/                # AI Agent (multi-LLM, unified)
│       ├── core/                     # Safety, ROS bridge
│       ├── llm_providers/            # Gemini, Claude, Kimi, Ollama
│       ├── tools/                    # Tool registry
│       ├── interfaces/               # Chat server, MCP, CLI
│       ├── launch/                   # Launch files
│       └── config/                   # Configuration
├── CLAUDE.md                         # This file
└── .claude/                          # Claude Code configuration
    ├── CLAUDE.md                     # Skills & conventions
    └── rules/                        # Coding standards
        ├── workflow.md
        └── coding_standards.md
```

---

## References

- **Yahboom ROSMaster V3.0**: https://github.com/YahboomTechnology/ROS-robot-expansion-board
- **ROS 2 Jazzy**: https://docs.ros.org/en/jazzy/
- **slam_toolbox**: https://github.com/SteveMacenski/slam_toolbox
- **Nav2**: https://navigation.ros.org/
- **PlatformIO**: https://platformio.org/

---

**Last Updated**: 2026-02-25  
**Version**: v2.1.0  
**Author**: Jewel Nath