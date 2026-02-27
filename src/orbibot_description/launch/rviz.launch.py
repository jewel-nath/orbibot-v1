#!/usr/bin/env python3

"""Launch RViz for remote robot visualization."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Generate RViz launch description."""

    description_dir = get_package_share_directory('orbibot_description')

    return LaunchDescription([
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', os.path.join(description_dir, 'rviz', 'orbibot.rviz')]
        )
    ])
