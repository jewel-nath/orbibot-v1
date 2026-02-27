#!/usr/bin/env python3
"""
OrbiBot Robot Base Launch
Launches all core components: description, hardware, lidar, EKF.
Optionally launches camera.

Usage:
    ros2 launch orbibot_bringup robot.launch.py
    ros2 launch orbibot_bringup robot.launch.py use_camera:=true
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    LogInfo,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    declare_use_camera_arg = DeclareLaunchArgument(
        'use_camera',
        default_value='false',
        description='Launch RealSense camera'
    )

    use_camera = LaunchConfiguration('use_camera')

    log_startup = LogInfo(
        msg=['[Bringup] Robot base started — camera: ', use_camera]
    )

    # Robot Description (URDF + robot_state_publisher)
    description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_description'),
                'launch',
                'description.launch.py'
            ])
        ])
    )

    # Hardware Interface (serial bridge to firmware + system monitor)
    hardware_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_hardware'),
                'launch',
                'hardware.launch.py'
            ])
        ])
    )

    # Lidar (delayed, launched as separate subprocess for isolation)
    # Using ExecuteProcess instead of IncludeLaunchDescription to avoid
    # USB serial conflict between /dev/motordriver and /dev/lidar
    lidar_launch = TimerAction(
        period=5.0,
        actions=[
            LogInfo(msg='[Bringup] Starting LiDAR as subprocess...'),
            ExecuteProcess(
                cmd=['ros2', 'launch', 'orbibot_sensors', 'lidar.launch.py'],
                name='lidar_launch',
                output='screen',
            )
        ]
    )

    # EKF Localization (delayed — wait for hardware_node to publish /odom)
    localization_launch = TimerAction(
        period=3.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([
                    PathJoinSubstitution([
                        FindPackageShare('orbibot_localization'),
                        'launch',
                        'localization.launch.py'
                    ])
                ])
            )
        ]
    )

    # Camera (optional)
    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_sensors'),
                'launch',
                'camera.launch.py'
            ])
        ]),
        condition=IfCondition(use_camera)
    )

    return LaunchDescription([
        declare_use_camera_arg,
        log_startup,
        description_launch,
        hardware_launch,
        lidar_launch,
        localization_launch,
        camera_launch,
    ])
