# orbibot_description

URDF/Xacro robot model for OrbiBot — a mecanum-wheeled mobile robot using Yahboom ROSMaster V3.0 expansion board.

## Overview

This package defines the robot's physical structure, coordinate frames, and visual representation for RViz, Gazebo (future), and the TF tree used throughout the navigation stack.

---

## Robot Geometry

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Wheel radius** | 50 mm | 100mm diameter mecanum wheels |
| **Track width** | 360 mm | Left-to-right wheel center distance |
| **Wheelbase** | 260 mm | Front-to-rear wheel center distance |
| **Base dimensions** | 350 × 250 × 100 mm | Chassis footprint (L×W×H) |
| **Mecanum pattern** | ABBA | A-type (+45°), B-type (-45°) rollers |

### Mecanum Wheel Layout (ABBA)
```
          Front
    FL (A)     FR (B)
       ╲     ╱
        ╲   ╱
         ╲ ╱
         ╱ ╲
        ╱   ╲
    BL (B)     BR (A)
          
    A-type: rollers at +45° (top-left to bottom-right)
    B-type: rollers at -45° (top-right to bottom-left)
```

---

## TF Frame Tree

```
map (world frame)
└── odom (odometry origin)
    └── base_footprint (robot footprint on ground)
        └── base_link (robot center, 100mm above ground)
            ├── wheel_front_left_link
            ├── wheel_back_left_link
            ├── wheel_front_right_link
            ├── wheel_back_right_link
            ├── lidar_link (RPLidar A1, 200mm above base)
            ├── imu_link (ICM-20948, at base_link)
            └── camera_link (RealSense D435, 150mm above base)
                ├── camera_color_frame → camera_color_optical_frame
                └── camera_depth_frame → camera_depth_optical_frame
```

### Key Frame Definitions

| Frame | Origin | Purpose |
|-------|--------|---------|
| `base_footprint` | Ground projection of robot center | Navigation reference frame |
| `base_link` | Robot geometric center | Main robot body frame |
| `lidar_link` | LiDAR sensor origin | Scan data frame_id |
| `imu_link` | IMU chip location | IMU data frame_id |
| `camera_link` | Camera mounting point | Camera data frame_id |

---

## File Structure

```
orbibot_description/
├── urdf/
│   ├── orbibot.urdf.xacro          # Main robot model (includes all components)
│   ├── orbibot_base.xacro          # Chassis and base geometry
│   ├── orbibot_wheels.xacro        # 4 mecanum wheels with transmissions
│   ├── orbibot_sensors.xacro       # LiDAR, IMU, Camera mounts
│   └── materials.xacro             # Color/material definitions
├── meshes/
│   ├── wheel_mecanum_a.stl         # A-type wheel mesh (+45° rollers)
│   ├── wheel_mecanum_b.stl         # B-type wheel mesh (-45° rollers)
│   └── rplidar_a1.stl              # RPLidar A1 housing mesh
├── launch/
│   ├── description.launch.py       # Publish robot description + TF tree
│   └── rviz.launch.py              # Launch RViz with saved config
└── rviz/
    └── orbibot.rviz                # Pre-configured RViz display
```

---

## Launch Usage

### Publish Robot Description
```bash
# Standard launch (used by robot.launch.py)
ros2 launch orbibot_description description.launch.py

# Verify TF tree
ros2 run tf2_tools view_frames  # Generates frames.pdf
```

### Visualize in RViz
```bash
# From robot (requires hardware running for joint states)
ros2 launch orbibot_description rviz.launch.py

# From fixed frame (no hardware needed)
ros2 launch orbibot_description rviz.launch.py fixed_frame:=true
```

### Check URDF
```bash
# Validate URDF syntax
check_urdf src/orbibot_description/urdf/orbibot.urdf.xacro

# View URDF structure
urdf_to_graphviz src/orbibot_description/urdf/orbibot.urdf.xacro
```

---

## Xacro Macros

### Main Robot
```xml
<xacro:orbibot_base name="base" 
                    wheel_radius="0.05"
                    wheel_separation_x="0.26"
                    wheel_separation_y="0.36"/>
```

### Mecanum Wheels
```xml
<xacro:wheel name="wheel_front_left" 
             type="a" 
             radius="0.05"
             width="0.04"/>
```

### Sensors
```xml
<xacro:rplidar_a1 parent="base_link" 
                  xyz="0.15 0 0.20" 
                  rpy="0 0 0"/>

<xacro:realsense_d435 parent="base_link"
                      xyz="0.10 0 0.15"
                      rpy="0 0 0"/>

<xacro:imu_icm20948 parent="base_link"
                    xyz="0 0 0.10"
                    rpy="0 0 0"/>
```

---

## Joint Configuration

| Joint | Type | Parent → Child | Axis | Limits |
|-------|------|----------------|------|--------|
| `wheel_front_left_joint` | continuous | base_link → wheel_front_left_link | Y axis | ±inf rad |
| `wheel_back_left_joint` | continuous | base_link → wheel_back_left_link | Y axis | ±inf rad |
| `wheel_front_right_joint` | continuous | base_link → wheel_front_right_link | Y axis | ±inf rad |
| `wheel_back_right_joint` | continuous | base_link → wheel_back_right_link | Y axis | ±inf rad |

**Note**: Joint states are published by `orbibot_hardware` at 50Hz. No `joint_state_publisher` is needed when hardware is running.

---

## Sensor Mounting Positions

### RPLidar A1
- **Position**: Forward of center, 200mm above ground
- **Orientation**: Z-up (standard)
- **Topic**: `/scan` (frame_id: `lidar_link`)
- **Parameters**: 360°, 10Hz, 0.15-8.0m range

### ICM-20948 IMU
- **Position**: Robot center, 100mm above ground
- **Orientation**: X-forward, Y-left, Z-up (ENU convention)
- **Topics**: `/imu/data_raw`, `/imu/mag` (frame_id: `imu_link`)

### RealSense D435 (Optional)
- **Position**: Forward of center, 150mm above ground
- **Orientation**: X-forward (optical frame has Z-forward)
- **Topics**: 
  - `/camera/color/image_raw` (frame_id: `camera_color_optical_frame`)
  - `/camera/depth/image_rect_raw` (frame_id: `camera_depth_optical_frame`)

---

## Debugging

### Verify TF Tree
```bash
# Echo a specific transform
ros2 run tf2_ros tf2_echo odom base_footprint

# Check all frames
ros2 run tf2_tools view_frames

# Monitor TF rate
ros2 topic hz /tf  # Should be ~100Hz
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `lidar_link` not in TF tree | Description not published | Launch `description.launch.py` |
| Wheels not visible in RViz | No joint states | Hardware must be running, or use `fixed_frame:=true` |
| Robot appears offset | Wrong fixed frame | Set RViz fixed frame to `odom` or `map` |
| Camera image misaligned | Wrong optical frame | Use `camera_color_optical_frame` for image display |

---

## Dependencies

```bash
# Required packages
sudo apt install ros-jazzy-robot-state-publisher
sudo apt install ros-jazzy-joint-state-publisher  # Optional, for testing without hardware
sudo apt install ros-jazzy-tf2-tools
```

---

## References

- **URDF Tutorial**: http://wiki.ros.org/urdf/Tutorials
- **Xacro Documentation**: http://wiki.ros.org/xacro
- **TF2 Overview**: https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Introduction-To-Tf2.html
- **Yahboom ROSMaster V3.0**: Robot dimensions and mounting points

---

**Last Updated**: 2026-02-24  
**Maintainer**: Jewel Nath