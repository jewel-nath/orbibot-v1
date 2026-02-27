---
description: OrbiBot Robot-Specific Standards (URDF, TF2, Navigation, Mecanum)
---

# OrbiBot Robot-Specific Standards

## Physical Parameters

```yaml
# Robot dimensions and properties
wheel_radius: 0.05          # 50mm radius (100mm diameter)
wheel_separation_x: 0.26    # 260mm front-back
wheel_separation_y: 0.36    # 360mm left-right
footprint: 350mm x 250mm    # Robot body
robot_mass: 6 kg
encoder_cpr: 1320            # 11 PPR * 30 gear * 4 quadrature
gear_ratio: 30               # JGB37-520 motor
max_motor_rpm: 333
```

## URDF/Xacro Best Practices

```xml
<?xml version="1.0"?>
<robot xmlns:xacro="http://ros.org/wiki/xacro" name="orbibot">

  <!-- Properties — match hardware_params.yaml -->
  <xacro:property name="wheel_radius" value="0.05"/>
  <xacro:property name="wheel_width" value="0.04"/>
  <xacro:property name="wheel_separation_x" value="0.26"/>
  <xacro:property name="wheel_separation_y" value="0.36"/>

  <!-- Mecanum wheel macro — 4 wheels with position params -->
  <xacro:macro name="mecanum_wheel" params="prefix x_reflect y_reflect">
    <link name="${prefix}_wheel_link">
      <visual>
        <geometry>
          <cylinder radius="${wheel_radius}" length="${wheel_width}"/>
        </geometry>
      </visual>
      <collision>
        <geometry>
          <cylinder radius="${wheel_radius}" length="${wheel_width}"/>
        </geometry>
      </collision>
      <inertial>
        <mass value="0.3"/>
        <inertia ixx="0.001" ixy="0" ixz="0" iyy="0.001" iyz="0" izz="0.001"/>
      </inertial>
    </link>

    <joint name="${prefix}_wheel_joint" type="continuous">
      <parent link="base_link"/>
      <child link="${prefix}_wheel_link"/>
      <origin xyz="${x_reflect * wheel_separation_x / 2} ${y_reflect * wheel_separation_y / 2} 0"
              rpy="${-pi/2} 0 0"/>
      <axis xyz="0 0 1"/>
    </joint>
  </xacro:macro>

  <!-- base_footprint (ground contact) → base_link (robot body) -->
  <link name="base_footprint"/>
  <link name="base_link">
    <visual>
      <geometry><box size="0.35 0.25 0.12"/></geometry>
    </visual>
  </link>
  <joint name="base_joint" type="fixed">
    <parent link="base_footprint"/>
    <child link="base_link"/>
    <origin xyz="0 0 ${wheel_radius}"/>
  </joint>

  <!-- 4 mecanum wheels -->
  <xacro:mecanum_wheel prefix="front_left"  x_reflect="1"  y_reflect="1"/>
  <xacro:mecanum_wheel prefix="front_right" x_reflect="1"  y_reflect="-1"/>
  <xacro:mecanum_wheel prefix="back_left"   x_reflect="-1" y_reflect="1"/>
  <xacro:mecanum_wheel prefix="back_right"  x_reflect="-1" y_reflect="-1"/>

</robot>
```

## TF2 Frame Tree

```
map                              ← AMCL (navigation) or slam_toolbox (mapping)
 └── odom                        ← EKF (robot_localization)
      └── base_footprint         ← Robot base frame (ALWAYS use this, not base_link)
           └── base_link         ← URDF (robot_state_publisher)
                ├── lidar_link
                ├── camera_link
                │    ├── camera_color_frame
                │    │    └── camera_color_optical_frame
                │    └── camera_depth_frame
                │         └── camera_depth_optical_frame
                ├── imu_link
                ├── front_left_wheel_link
                ├── front_right_wheel_link
                ├── back_left_wheel_link
                └── back_right_wheel_link
```

**TF publishers:**
| Transform | Publisher |
|-----------|----------|
| `map → odom` | AMCL (nav) or slam_toolbox (mapping) |
| `odom → base_footprint` | EKF (`robot_localization`) |
| `base_footprint → base_link → *` | `robot_state_publisher` (from URDF) |

## Navigation Stack Configuration

```yaml
# OrbiBot uses MPPI controller with Omni motion model (NOT DWB)
bt_navigator:
  ros__parameters:
    global_frame: map
    robot_base_frame: base_footprint    # NEVER base_link
    odom_topic: /odometry/filtered      # EKF output, NOT raw /odom

controller_server:
  ros__parameters:
    controller_frequency: 10.0          # Reduced for Raspberry Pi
    cmd_vel_topic: "cmd_vel_nav"        # Start of velocity chain
    FollowPath:
      plugin: "nav2_mppi_controller::MPPIController"
      motion_model: "Omni"             # Mecanum wheels = omnidirectional
      batch_size: 1000                 # Reduced for RPi CPU
      vx_max: 0.5
      vy_max: 0.5                      # Lateral motion (mecanum)
      wz_max: 1.9

planner_server:
  ros__parameters:
    GridBased:
      plugin: "nav2_navfn_planner::NavfnPlanner"
      tolerance: 0.15
      use_astar: true

amcl:
  ros__parameters:
    robot_model_type: "nav2_amcl::OmniMotionModel"  # Mecanum
    base_frame_id: "base_footprint"
```

## Velocity Chain

```
controller_server    →  velocity_smoother  →  collision_monitor  →  motors
  (cmd_vel_nav)          (cmd_vel_smoothed)     (cmd_vel)
```

## Sensor Integration

### OrbiBot Sensors

```python
# OrbiBot uses external nodes for sensors, not custom publishers:
# - RPLidar A1: rplidar_ros node → /scan (Express scan mode)
# - RealSense D435: realsense2_camera node → /camera/* topics
# - IMU: orbibot_hardware_node → /imu/data (attitude from motor driver board)

# QoS for subscribing to OrbiBot sensor data:
from rclpy.qos import qos_profile_sensor_data, QoSProfile, ReliabilityPolicy

# LiDAR scan — best effort (high frequency)
scan_sub = node.create_subscription(
    LaserScan, '/scan', callback, qos_profile_sensor_data
)

# IMU data — best effort
imu_sub = node.create_subscription(
    Imu, '/imu/data', callback, qos_profile_sensor_data
)

# EKF filtered odometry — reliable
odom_sub = node.create_subscription(
    Odometry, '/odometry/filtered', callback, 10
)
```

## Motor Control Pattern — Mecanum Kinematics

```python
# OrbiBot mecanum inverse kinematics (firmware)
# cmd_vel (Twist) → individual wheel speeds

def mecanum_inverse_kinematics(vx, vy, wz):
    """Convert body velocities to individual wheel speeds.

    Args:
        vx: forward velocity (m/s)
        vy: lateral velocity (m/s) — mecanum specific
        wz: angular velocity (rad/s)

    Returns:
        (fl, fr, bl, br) wheel velocities in m/s
    """
    lx = wheel_separation_x / 2  # 0.13m
    ly = wheel_separation_y / 2  # 0.18m

    fl = vx - vy - (lx + ly) * wz
    fr = vx + vy + (lx + ly) * wz
    bl = vx + vy - (lx + ly) * wz
    br = vx - vy + (lx + ly) * wz

    return fl, fr, bl, br
```

## EKF Sensor Fusion

```yaml
# robot_localization EKF fuses:
# 1. Wheel odometry (/odom) — velocities only (vx, vy, vyaw)
# 2. IMU (/imu/data) — absolute yaw + yaw rate (differential mode)
#
# Output: /odometry/filtered + odom → base_footprint TF
```

## Exploration

```yaml
# Custom BFS frontier explorer (NOT explore_lite)
# Command interface: /orbibot/exploration/command (start/stop/pause/resume)
# Status: /orbibot/exploration/status
# Uses nav2 navigate_to_pose action for goal execution
```
