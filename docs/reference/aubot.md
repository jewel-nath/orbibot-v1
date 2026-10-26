# Autonomous-Mobile-Robot (AuBot) — Reference Notes

## Robot Overview

**Autonomous-Mobile-Robot** is an open-source mecanum-wheel robot project with a React web
dashboard, Nav2 autonomous navigation, and an AI/YOLOv8 camera server. It uses an STM32F411
(different MCU from OrbiBot's STM32F103) communicating over USB CDC, with ROS 2 and a rosbridge
WebSocket for the web interface.

**Why it's useful:** Mecanum-wheel Nav2 config, frontier exploration setup, and the React web
dashboard architecture are all directly comparable to OrbiBot's goals.

---

## Hardware

| Component | AuBot | OrbiBot |
|---|---|---|
| Drive type | Mecanum (4-wheel) | Mecanum (4-wheel) — same |
| MCU | STM32F411CEUX | STM32F103RCT6 |
| MCU firmware | STM32CubeIDE HAL | Keil / PlatformIO |
| Communication | USB CDC (virtual serial) | UART serial |
| SBC | (not specified, Linux) | Raspberry Pi 5 |
| LiDAR | (RPLIDAR, sllidar_ros2) | RPLidar A1 |
| Camera | USB webcam + YOLOv8 | Intel RealSense D435 |

---

## Repository Structure (after cleanup)

```
Autonomous-Mobile-Robot/
├── README.md
├── ros2_ws/src/
│   ├── mecanum_control/       C++ odometry publisher
│   ├── my_custom_launch/      Bridge + orchestration launch
│   ├── my_robot_description/  URDF, Nav2/SLAM config, maps, launch files
│   ├── perception/            LiDAR obstacle detection node
│   └── stm32_bridge/          USB serial bridge node (STM32 ↔ ROS 2)
├── stm32/                     STM32F411 CubeIDE firmware project
└── web_interface/             React/Vite web dashboard + Python AI server
```

---

## STM32 Firmware (`stm32/`)

**Toolchain:** STM32CubeIDE, HAL library, STM32F411CEUX
**Communication:** USB CDC (virtual COM port)

### Key source files

| File | Purpose |
|---|---|
| `Core/Src/main.c` | Main loop, peripheral init |
| `Core/Src/motor_control.c` | Motor PWM control for mecanum wheels |
| `Core/Src/pid.c` | PID controller implementation |
| `Core/Inc/motor_control.h` | Motor control interface |
| `Core/Inc/pid.h` | PID interface |
| `Core/Src/cJSON.c` / `Core/Inc/cJSON.h` | JSON serialization for USB data packets |

**Protocol:** Uses **JSON over USB CDC** — contrast with OrbiBot's binary serial protocol.
Packets are JSON objects serialized with cJSON, sent over USB virtual serial port.

**OrbiBot relevance:** The `pid.c` and `motor_control.c` are clean reference implementations.
The JSON protocol approach is simpler to debug than binary but has more overhead.

---

## ROS 2 Packages (`ros2_ws/src/`)

### `stm32_bridge/` — USB Serial Bridge
**File:** `stm32_bridge/stm32_bridge_node.py`

Reads JSON packets from the STM32 over USB serial and republishes as ROS 2 topics. This is
the equivalent of OrbiBot's `hardware_node.py`. Key pattern: serial read in a thread, publish
to ROS 2 topics.

Also includes `udp_to_ros2.py` — a UDP socket bridge variant (alternative transport).

### `mecanum_control/` — Odometry Publisher
**File:** `src/odom_publisher.cpp`

C++ node that computes and publishes `/odom` from mecanum wheel encoder data. Uses mecanum
forward kinematics directly in ROS 2. Good reference for the C++ odometry implementation pattern.

### `my_robot_description/` — Most Valuable Package

Contains URDF, all Nav2/SLAM configuration, launch files, and a saved map.

**URDF files (`urdf/`):**
- `robot.urdf.xacro` — main robot description with 4 mecanum wheels
- `macros.xacro` — reusable wheel and joint macros
- `gazebo_plugins.xacro` — Gazebo diff drive plugin (ignore for real robot)
- `materials.xacro` — visual material definitions
- `meshes/` — STL files for base, wheels, lidar, camera

**Config files (`config/`):**

| File | Purpose |
|---|---|
| `my_slam_config.yaml` | slam_toolbox parameters |
| `my_mapper_params.yaml` | slam_toolbox mapper params |
| `nav2_navigation_params.yaml` | Nav2 full stack params (MPPI + mecanum) |
| `nav2_exploration_params.yaml` | Nav2 params tuned for exploration |

**Nav2 config highlights (`nav2_navigation_params.yaml`):**
Uses mecanum-appropriate settings:
```yaml
# Mecanum omni motion model
controller:
  FollowPath:
    plugin: "nav2_mppi_controller::MPPIController"
    motion_model: "Omni"   # Same as OrbiBot
    vy_max: 0.3            # Lateral velocity enabled
```
This is one of the few reference Nav2 configs with `motion_model: "Omni"` — directly comparable
to OrbiBot's MPPI setup.

**Launch files (`launch/`):**
- `robotdes_launch.py` — robot description + state publisher
- `odom_launch.py` — odometry node
- `map_launch.py` — SLAM mapping
- `navigation_launch.py` — Nav2 full stack
- `exploration_launch.py` — autonomous frontier exploration

**Maps (`maps/`):**
- `my_saved_map.pgm` + `.yaml` — sample map from real robot run

### `perception/` — LiDAR Obstacle Detection
**File:** `perception/lidar_obstacle_node.py`

Subscribes to `/scan`, detects obstacles, publishes warnings. Simple single-file implementation —
useful as a reference for OrbiBot's obstacle avoidance behavior.

### `my_custom_launch/` — Bridge Launch
**File:** `launch/my_bridge_launch.py`

Launches the rosbridge WebSocket server alongside the robot nodes. Shows how to integrate
rosbridge into a custom launch file — relevant for `orbibot_webgui`.

---

## Web Interface (`web_interface/`)

A React/Vite single-page app that connects to the robot via rosbridge WebSocket.

### Architecture

```
Browser (React SPA)
  └── roslib.js (WebSocket to rosbridge :9090)
       ├── /map topic → MapViewer component (ros2d.js canvas)
       ├── /cmd_vel publisher → TeleopControls component
       ├── Waypoint management → WaypointManager component
       └── Connection status → ConnectionStatus component

Python AI server (ai_server.py)
  └── FastAPI + WebSocket
       └── YOLOv8 inference on camera frames → AICamera component
```

### Key files

| File | Purpose |
|---|---|
| `src/App.jsx` | Root component, layout |
| `src/contexts/RosContext.jsx` | ROSLIB connection context (shared state) |
| `src/components/MapViewer.jsx` | 2D map display using ros2d.js |
| `src/components/TeleopControls.jsx` | Velocity command buttons |
| `src/components/WaypointManager.jsx` | Save/navigate to waypoints |
| `src/components/ConnectionStatus.jsx` | ROS connection indicator |
| `ai_server.py` | FastAPI server, YOLOv8 object detection |

**RosContext pattern:** Single context provides the ROSLIB `ros` connection object to all
components. This is the same pattern OrbiBot's webgui uses.

**OrbiBot webgui comparison:**
- AuBot uses `ros2d.js` for map rendering; OrbiBot webgui should evaluate this for map display
- AuBot's `WaypointManager` is a reference for adding waypoint navigation to OrbiBot webgui
- AuBot separates AI inference into a standalone Python server — good pattern for OrbiBot AI integration

---

## Nav2 Configuration Highlights

### MPPI with Omni motion model (`nav2_navigation_params.yaml`)
This is the most directly comparable Nav2 config to OrbiBot since both use mecanum wheels:

Key params to compare with `orbibot_navigation/config/nav2_params.yaml`:
- `motion_model: "Omni"` — confirmed working on mecanum
- `vy_max`, `vy_min` — lateral velocity limits
- Costmap resolution and inflation radius
- `robot_radius` vs OrbiBot's footprint polygon

### Exploration config (`nav2_exploration_params.yaml`)
Separate Nav2 params for exploration mode (looser obstacle tolerance, higher speed).
OrbiBot should adopt this pattern — different nav params for mapping vs navigation vs exploration.

---

## What to Use From This Reference

| Need | File to consult |
|---|---|
| Mecanum MPPI Nav2 config | `my_robot_description/config/nav2_navigation_params.yaml` |
| Exploration Nav2 config | `my_robot_description/config/nav2_exploration_params.yaml` |
| SLAM config | `my_robot_description/config/my_slam_config.yaml` |
| Mecanum URDF with macros | `my_robot_description/urdf/robot.urdf.xacro` + `macros.xacro` |
| Web dashboard RosContext pattern | `web_interface/src/contexts/RosContext.jsx` |
| Map viewer component | `web_interface/src/components/MapViewer.jsx` |
| Waypoint manager component | `web_interface/src/components/WaypointManager.jsx` |
| LiDAR obstacle detection | `ros2_ws/src/perception/perception/lidar_obstacle_node.py` |
| C++ odometry publisher | `ros2_ws/src/mecanum_control/src/odom_publisher.cpp` |
| USB serial bridge node | `ros2_ws/src/stm32_bridge/stm32_bridge/stm32_bridge_node.py` |
| rosbridge in custom launch | `ros2_ws/src/my_custom_launch/launch/my_bridge_launch.py` |
