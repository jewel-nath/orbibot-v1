#!/usr/bin/env python3
"""
OrbiBot Simulation — SLAM Mapping
SLAM mapping + Nav2 on top of the running Gazebo simulation.

Prerequisites (run first):
    ros2 launch orbibot_gazebo sim.launch.py

Usage:
    ros2 launch orbibot_gazebo sim_mapping.launch.py

Then drive with teleop:
    ros2 launch orbibot_teleop controller.launch.py use_sim_time:=true

Save map when done:
    ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
      "{name: {data: '/home/jewel/maps/sim_map'}}"
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_gazebo = get_package_share_directory('orbibot_gazebo')
    pkg_navigation = get_package_share_directory('orbibot_navigation')

    slam_params_sim = os.path.join(pkg_gazebo, 'config', 'slam_params_sim.yaml')

    declare_nav_params_arg = DeclareLaunchArgument(
        'nav_params_file',
        default_value=os.path.join(pkg_navigation, 'config', 'nav2_params.yaml'),
        description='Nav2 parameters file',
    )

    slam_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_slam'),
                'launch',
                'slam.launch.py',
            ])
        ]),
        launch_arguments={
            'slam_params_file': slam_params_sim,
        }.items(),
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('nav2_bringup'),
                'launch',
                'navigation_launch.py',
            ])
        ]),
        launch_arguments={
            'params_file': LaunchConfiguration('nav_params_file'),
            'use_sim_time': 'true',
        }.items(),
    )

    return LaunchDescription([
        declare_nav_params_arg,
        LogInfo(msg='[Sim] SLAM mapping + Nav2 started (use_sim_time=true)'),
        slam_launch,
        nav2_launch,
    ])
