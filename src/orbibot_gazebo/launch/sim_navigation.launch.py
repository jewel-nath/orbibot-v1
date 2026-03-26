#!/usr/bin/env python3
"""
OrbiBot Simulation — Navigation with Saved Map
Nav2 full stack (AMCL + planners) using a previously saved map.

Prerequisites (run first):
    ros2 launch orbibot_gazebo sim.launch.py

Usage:
    ros2 launch orbibot_gazebo sim_navigation.launch.py
    ros2 launch orbibot_gazebo sim_navigation.launch.py map:=/home/jewel/maps/sim_map.yaml

Send a navigation goal:
    ros2 topic pub /goal_pose geometry_msgs/PoseStamped \
      "{header: {frame_id: 'map'}, pose: {position: {x: 2.0, y: 1.0}}}"
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_navigation = get_package_share_directory('orbibot_navigation')

    declare_map_arg = DeclareLaunchArgument(
        'map',
        default_value=os.path.join(pkg_navigation, 'maps', 'map.yaml'),
        description='Path to saved map YAML file',
    )

    declare_params_arg = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(pkg_navigation, 'config', 'nav2_params.yaml'),
        description='Nav2 parameters file',
    )

    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('nav2_bringup'),
                'launch',
                'bringup_launch.py',
            ])
        ]),
        launch_arguments={
            'map': LaunchConfiguration('map'),
            'params_file': LaunchConfiguration('params_file'),
            'use_sim_time': 'true',
        }.items(),
    )

    return LaunchDescription([
        declare_map_arg,
        declare_params_arg,
        LogInfo(msg='[Sim] Nav2 navigation started with saved map (use_sim_time=true)'),
        nav2_launch,
    ])
