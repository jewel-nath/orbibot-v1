# orbibot_bringup

System-level launch orchestration for OrbiBot. Provides three launch files that compose the robot's full software stack in a layered architecture.

## Launch Files

### 1. Robot Base — `robot.launch.py`

Launches all core hardware and sensing components. **Must be started first.**

```bash
ros2 launch orbibot_bringup robot.launch.py
ros2 launch orbibot_bringup robot.launch.py use_camera:=true
```

| Order | Component | Package | Notes |
|-------|-----------|---------|-------|
| 1 | Robot Description (URDF + TF) | orbibot_description | Immediate |
| 2 | Hardware Interface + System Monitor | orbibot_hardware | Immediate |
| 3 | Control Manager (odometry + TF) | orbibot_control | Delayed 3s (hardware init) |
| 4 | EKF Localization (sensor fusion) | orbibot_localization | Delayed 4s (wait for /odom) |
| 5 | LiDAR | orbibot_sensors | Delayed 5s, subprocess isolation |
| 6 | RealSense Camera (optional) | orbibot_sensors | Only if `use_camera:=true` |

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `use_camera` | `false` | Launch RealSense camera node |

### 2. Mapping — `mapping.launch.py`

SLAM mapping + Nav2 navigation for building a new map.

```bash
# Prerequisite: robot base must be running
ros2 launch orbibot_bringup robot.launch.py

# Then start mapping
ros2 launch orbibot_bringup mapping.launch.py
```

| Component | Package | Notes |
|-----------|---------|-------|
| SLAM Toolbox (mapping mode) | orbibot_slam | Builds occupancy grid |
| Nav2 Navigation Stack | nav2_bringup | No map server — SLAM provides the map |

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `nav_params_file` | `orbibot_navigation/config/nav2_params.yaml` | Nav2 parameters file |

### 3. Exploration — `exploration.launch.py`

SLAM + Nav2 + autonomous frontier exploration for hands-free map building.

```bash
# Prerequisite: robot base must be running
ros2 launch orbibot_bringup robot.launch.py

# Then start exploration
ros2 launch orbibot_bringup exploration.launch.py
```

| Component | Package | Notes |
|-----------|---------|-------|
| SLAM Toolbox (mapping mode) | orbibot_slam | Builds occupancy grid |
| Nav2 Navigation Stack | nav2_bringup | No map server — SLAM provides the map |
| Frontier Explorer | orbibot_exploration | Custom BFS frontier detection |

**Arguments:**

| Argument | Default | Description |
|----------|---------|-------------|
| `nav_params_file` | `orbibot_navigation/config/nav2_params.yaml` | Nav2 parameters file |

## Architecture

```
Tier 1 (robot.launch.py)        Tier 2 (pick one)
─────────────────────────       ─────────────────────
description                     mapping.launch.py
hardware                          └─ SLAM + Nav2
control (3s delay)
lidar (5s delay, subprocess)    exploration.launch.py
EKF localization                  └─ SLAM + Nav2 + Frontier Explorer
system monitor
camera (optional)
```

## Dependencies

`orbibot_description`, `orbibot_hardware`, `orbibot_control`, `orbibot_sensors`, `orbibot_localization`, `orbibot_slam`, `orbibot_navigation`, `orbibot_exploration`
