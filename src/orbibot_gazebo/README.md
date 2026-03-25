# orbibot_gazebo

Gazebo Harmonic simulation for OrbiBot. Replaces the physical hardware stack when the robot is not available.

**Robot not required** — this package lets you test Nav2, SLAM, AI agent, and teleop entirely in simulation.

---

## What This Package Provides

| Component | Real robot | Simulation |
|-----------|-----------|------------|
| Motor drive | `orbibot_hardware_node` + firmware | Gazebo DiffDrive plugin |
| `/odom` + `odom→base_footprint` TF | `orbibot_hardware_node` | DiffDrive plugin (bridged) |
| `/scan` | `rplidar_ros` node | Gazebo GPU LiDAR sensor (bridged) |
| `/imu/data_raw` | `orbibot_hardware_node` | Gazebo IMU sensor (bridged) |
| `/clock` | System time | Gazebo sim clock (bridged) |
| Environment | Physical room | `worlds/orbibot_room.sdf` (10×10m, 4 obstacles) |

> **Mecanum note**: Lateral strafing (vy) is approximated with DiffDrive — the robot cannot strafe in sim. Forward/backward and rotation work correctly. This is sufficient for Nav2, SLAM, and AI agent testing.

---

## Quick Start

### 1. Install Gazebo Harmonic (one-time)

```bash
sudo apt-get install -y \
  ros-jazzy-ros-gz-sim \
  ros-jazzy-ros-gz-bridge \
  ros-jazzy-ros-gz-interfaces \
  ros-jazzy-gz-sim-vendor
```

### 2. Build

```bash
cd ~/orbibot_ws
colcon build --packages-select orbibot_gazebo orbibot_description
source install/setup.bash
```

### 3. Launch simulation

```bash
# Terminal 1: Start Gazebo + robot + bridge + RViz
ros2 launch orbibot_gazebo sim.launch.py
```

### 4. Add SLAM + Nav2

```bash
# Terminal 2: SLAM mapping with Nav2 (sim mode)
ros2 launch orbibot_bringup sim_mapping.launch.py
```

### 5. Drive with teleop

```bash
# Terminal 3: Keyboard teleop
ros2 launch orbibot_teleop controller.launch.py use_sim_time:=true
```

### 6. Test AI Agent

```bash
# Terminal 4: Chat CLI (same as real robot)
ros2 run orbibot_agent chat_cli
```

### 7. Save map

```bash
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
  "{name: {data: '/home/jewel/maps/sim_map'}}"
```

---

## Launch Arguments

### `sim.launch.py`

| Argument | Default | Description |
|----------|---------|-------------|
| `world` | `worlds/orbibot_room.sdf` | Path to Gazebo world SDF |
| `use_rviz` | `true` | Launch RViz for visualization |
| `headless` | `false` | Run Gazebo without GUI (server only) |

```bash
# Headless (no GUI, saves resources)
ros2 launch orbibot_gazebo sim.launch.py headless:=true use_rviz:=false

# Custom world
ros2 launch orbibot_gazebo sim.launch.py world:=/path/to/my_world.sdf
```

---

## What Can Be Tested in Simulation

| Feature | Works in sim? |
|---------|--------------|
| Nav2 navigation (goal sending, path planning) | ✅ |
| SLAM mapping (slam_toolbox) | ✅ |
| Teleop (keyboard / gamepad) | ✅ |
| AI Agent (LLM → move commands) | ✅ |
| TF tree validation | ✅ |
| RViz visualization | ✅ |
| orbibot_webgui dashboard | ✅ |
| Mecanum strafing physics | ⚠️ Approximated |
| PID tuning | ❌ Real hardware only |
| Battery monitoring | ❌ Real hardware only |
| Firmware serial protocol | ❌ Real hardware only |

---

## Package Structure

```
orbibot_gazebo/
├── launch/
│   └── sim.launch.py          # Main sim launch (Gazebo + robot + bridge + RViz)
├── worlds/
│   └── orbibot_room.sdf       # 10×10m indoor room with 4 obstacles
└── config/
    ├── gz_bridge.yaml          # ROS ↔ Gazebo topic bridge config
    └── slam_params_sim.yaml    # SLAM params with use_sim_time: true
```

---

## ROS Topics (after bridge)

| Topic | Type | Direction | Description |
|-------|------|-----------|-------------|
| `/clock` | `rosgraph_msgs/Clock` | gz→ROS | Simulation time |
| `/cmd_vel` | `geometry_msgs/Twist` | ROS→gz | Velocity commands |
| `/odom` | `nav_msgs/Odometry` | gz→ROS | Wheel odometry |
| `/tf` | `tf2_msgs/TFMessage` | gz→ROS | odom→base_footprint TF |
| `/scan` | `sensor_msgs/LaserScan` | gz→ROS | LiDAR scan (360°, 10Hz) |
| `/imu/data_raw` | `sensor_msgs/Imu` | gz→ROS | IMU data (50Hz) |
| `/joint_states` | `sensor_msgs/JointState` | gz→ROS | Wheel positions |

---

## Version

- **Version**: v1.0.0
- **Simulator**: Gazebo Harmonic (gz-sim 8)
- **ROS 2**: Jazzy
- **Author**: Jewel Nath
