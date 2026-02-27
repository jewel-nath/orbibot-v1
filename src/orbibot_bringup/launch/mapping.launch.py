#!/usr/bin/env python3
"""
OrbiBot Mapping Launch
SLAM mapping + Nav2 navigation for building a new map.

Prerequisites:
    ros2 launch orbibot_bringup robot.launch.py

Usage:
    ros2 launch orbibot_bringup mapping.launch.py
"""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    nav_pkg_dir = get_package_share_directory('orbibot_navigation')

    declare_nav_params_arg = DeclareLaunchArgument(
        'nav_params_file',
        default_value=os.path.join(nav_pkg_dir, 'config', 'nav2_params.yaml'),
        description='Nav2 parameters file'
    )

    nav_params_file = LaunchConfiguration('nav_params_file')

    log_startup = LogInfo(
        msg=['[Bringup] Mapping started — SLAM + Nav2']
    )

    # SLAM mapping
    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_slam'),
                'launch',
                'slam.launch.py'
            ])
        ]),
    )

    # Nav2 navigation stack (without map server — SLAM provides the map)
    nav2_navigation_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('nav2_bringup'),
                'launch',
                'navigation_launch.py'
            ])
        ]),
        launch_arguments={
            'params_file': nav_params_file,
        }.items()
    )

    return LaunchDescription([
        declare_nav_params_arg,
        log_startup,
        slam_launch,
        nav2_navigation_launch,
    ])
