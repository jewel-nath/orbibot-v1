#!/usr/bin/env python3
"""
OrbiBot Localization Launch

Pipeline:
  /imu/data_raw → imu_filter_madgwick (use_mag=false) → /imu/data_filtered → EKF
  /odom (wheel odometry) ────────────────────────────────────────────────→ EKF
  EKF → /odometry/filtered + odom→base_footprint TF

Magnetometer was removed 2026-04-28; Madgwick now runs in 6-DoF mode.

Requires: sudo apt install ros-jazzy-imu-filter-madgwick
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_dir = get_package_share_directory('orbibot_localization')
    ekf_config_file = os.path.join(pkg_dir, 'config', 'ekf_params.yaml')
    madgwick_config_file = os.path.join(pkg_dir, 'config', 'madgwick_params.yaml')

    ekf_config_arg = DeclareLaunchArgument(
        'ekf_config',
        default_value=ekf_config_file,
        description='Path to EKF configuration file'
    )

    madgwick_config_arg = DeclareLaunchArgument(
        'madgwick_config',
        default_value=madgwick_config_file,
        description='Path to Madgwick IMU filter configuration file'
    )

    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Logging level'
    )

    ekf_config = LaunchConfiguration('ekf_config')
    madgwick_config = LaunchConfiguration('madgwick_config')
    log_level = LaunchConfiguration('log_level')

    log_startup = LogInfo(
        msg=['[Localization] Madgwick (6-DoF) + EKF — /imu/data_raw → relative yaw → /odometry/filtered']
    )

    # Madgwick IMU filter: fuses raw accel + gyro → orientation quaternion.
    # use_mag=false (mag was removed 2026-04-28) — see config/madgwick_params.yaml.
    imu_filter_madgwick = Node(
        package='imu_filter_madgwick',
        executable='imu_filter_madgwick_node',
        name='imu_filter_madgwick',
        output='screen',
        parameters=[madgwick_config],
        remappings=[
            ('imu/data_raw', '/imu/data_raw'),
            ('imu/data', '/imu/data_filtered'),
        ],
        respawn=True,
        respawn_delay=2.0,
    )

    robot_localization_ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='robot_localization_ekf',
        output='screen',
        parameters=[ekf_config],
        arguments=['--ros-args', '--log-level', log_level],
        respawn=True,
        respawn_delay=2.0,
    )

    return LaunchDescription([
        ekf_config_arg,
        madgwick_config_arg,
        log_level_arg,
        log_startup,
        imu_filter_madgwick,
        robot_localization_ekf,
    ])
