#!/usr/bin/env python3
"""
OrbiBot Localization Launch

Pipeline:
  /imu/data_raw + /imu/mag → imu_filter_madgwick → /imu/data_filtered → EKF
  /odom (wheel odometry) ──────────────────────────────────────────────→ EKF
  EKF → /odometry/filtered + odom→base_footprint TF

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

    ekf_config_arg = DeclareLaunchArgument(
        'ekf_config',
        default_value=ekf_config_file,
        description='Path to EKF configuration file'
    )

    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Logging level'
    )

    ekf_config = LaunchConfiguration('ekf_config')
    log_level = LaunchConfiguration('log_level')

    log_startup = LogInfo(
        msg=['[Localization] Madgwick + EKF — /imu/data_raw + /imu/mag → absolute yaw → /odometry/filtered']
    )

    # Madgwick IMU filter: fuses raw accel/gyro + magnetometer → orientation quaternion
    # Output feeds EKF as /imu/data_filtered with absolute yaw from magnetometer
    imu_filter_madgwick = Node(
        package='imu_filter_madgwick',
        executable='imu_filter_madgwick_node',
        name='imu_filter_madgwick',
        output='screen',
        parameters=[{
            'use_mag': True,
            'publish_tf': False,
            'world_frame': 'enu',
            'fixed_frame': 'odom',
            'gain': 0.1,
            'zeta': 0.001,              # Gyro bias drift correction (mag-assisted, slow)
            'orientation_stddev': 0.05, # ~3° std dev — EKF needs non-zero to weight IMU correctly
            'mag_bias_x': -0.00005452,  # Hard-iron calibrated 2026-03-15 (3 × 360°)
            'mag_bias_y': -0.00000832,
            'mag_bias_z': 0.00007170,
            'frequency': 50.0,
            'constant_dt': 0.0,
            'stateless': False,
            'remove_gravity_vector': False,
        }],
        remappings=[
            ('imu/data_raw', '/imu/data_raw'),
            ('imu/mag', '/imu/mag'),
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
        log_level_arg,
        log_startup,
        imu_filter_madgwick,
        robot_localization_ekf,
    ])
