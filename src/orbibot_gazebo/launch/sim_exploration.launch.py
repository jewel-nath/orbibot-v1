#!/usr/bin/env python3
"""
OrbiBot Simulation — Autonomous Exploration
SLAM + Nav2 + frontier explorer for autonomous mapping in simulation.

Prerequisites (run first):
    ros2 launch orbibot_gazebo sim.launch.py

Usage:
    ros2 launch orbibot_gazebo sim_exploration.launch.py

Start exploration:
    ros2 topic pub /orbibot/exploration/command std_msgs/String "{data: 'start'}" --once

Stop exploration:
    ros2 topic pub /orbibot/exploration/command std_msgs/String "{data: 'stop'}" --once

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
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_gazebo = get_package_share_directory('orbibot_gazebo')
    pkg_navigation = get_package_share_directory('orbibot_navigation')
    pkg_exploration = get_package_share_directory('orbibot_exploration')

    slam_params_sim = os.path.join(pkg_gazebo, 'config', 'slam_params_sim.yaml')

    declare_nav_params_arg = DeclareLaunchArgument(
        'nav_params_file',
        default_value=os.path.join(pkg_navigation, 'config', 'nav2_params_slam.yaml'),
        description='Nav2 parameters file (SLAM mode — no map server)',
    )

    declare_auto_start_arg = DeclareLaunchArgument(
        'auto_start',
        default_value='false',
        description='Automatically start exploration on launch',
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

    frontier_explorer_node = Node(
        package='orbibot_exploration',
        executable='frontier_explorer',
        name='frontier_explorer',
        output='screen',
        parameters=[
            os.path.join(pkg_exploration, 'config', 'exploration_params.yaml'),
            {
                'auto_start': LaunchConfiguration('auto_start'),
                'use_sim_time': True,
            },
        ],
    )

    return LaunchDescription([
        declare_nav_params_arg,
        declare_auto_start_arg,
        LogInfo(msg='[Sim] SLAM + Nav2 + Frontier Explorer started (use_sim_time=true)'),
        slam_launch,
        nav2_launch,
        frontier_explorer_node,
    ])
