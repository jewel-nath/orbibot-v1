"""
OrbiBot Exploration Launch — Frontier-based autonomous exploration.

Prerequisites:
    - SLAM running (orbibot_slam slam.launch.py)
    - Navigation running (orbibot_navigation navigation.launch.py)

Usage:
    ros2 launch orbibot_exploration exploration.launch.py
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_exploration = get_package_share_directory('orbibot_exploration')
    config_file = os.path.join(pkg_exploration, 'config', 'exploration_params.yaml')

    auto_start_arg = DeclareLaunchArgument(
        'auto_start',
        default_value='false',
        description='Automatically start exploration on launch'
    )

    log_startup = LogInfo(
        msg=['[Exploration] Frontier explorer node started']
    )

    frontier_explorer_node = Node(
        package='orbibot_exploration',
        executable='frontier_explorer',
        name='frontier_explorer',
        output='screen',
        parameters=[
            config_file,
            {'auto_start': LaunchConfiguration('auto_start')},
        ],
    )

    return LaunchDescription([
        auto_start_arg,
        log_startup,
        frontier_explorer_node,
    ])
