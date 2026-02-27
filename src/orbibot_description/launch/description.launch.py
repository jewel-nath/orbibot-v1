#!/usr/bin/env python3

"""Launch robot_state_publisher with OrbiBot URDF model."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command, LaunchConfiguration
from launch.conditions import IfCondition
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    """Generate robot state publisher launch description."""

    pkg_dir = get_package_share_directory('orbibot_description')
    urdf_file = os.path.join(pkg_dir, 'urdf', 'orbibot.urdf.xacro')

    declare_use_jsp_cmd = DeclareLaunchArgument(
        'use_jsp',
        default_value='false',
        description='Whether to start joint_state_publisher_gui'
    )

    use_jsp = LaunchConfiguration('use_jsp')

    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]),
        value_type=str
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        respawn=True,
        respawn_delay=2.0,
        parameters=[{
            'robot_description': robot_description,
        }]
    )

    joint_state_publisher_gui = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        condition=IfCondition(use_jsp)
    )

    # Joint states are published by hardware_node by default
    # Use use_jsp:=true for standalone visualization
    return LaunchDescription([
        declare_use_jsp_cmd,
        robot_state_publisher,
        joint_state_publisher_gui
    ])
