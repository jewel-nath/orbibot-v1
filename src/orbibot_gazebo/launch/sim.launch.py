#!/usr/bin/env python3
"""
OrbiBot Gazebo Simulation Launch

Launches Gazebo Harmonic with the OrbiBot robot in a simulated indoor room.
Replaces the real hardware stack (orbibot_hardware, orbibot_sensors) with:
  - Gazebo DiffDrive plugin  → /cmd_vel, /odom, odom→base_footprint TF
  - Gazebo LiDAR sensor      → /scan
  - Gazebo IMU sensor        → /imu/data_raw
  - ros_gz_bridge            → bridges all gz topics to ROS 2

Usage:
    ros2 launch orbibot_gazebo sim.launch.py
    ros2 launch orbibot_gazebo sim.launch.py use_rviz:=false
    ros2 launch orbibot_gazebo sim.launch.py world:=/path/to/custom.sdf

Then add SLAM + Nav2:
    ros2 launch orbibot_bringup sim_mapping.launch.py
"""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_gazebo = get_package_share_directory('orbibot_gazebo')
    pkg_description = get_package_share_directory('orbibot_description')

    # -----------------------------------------------------------------
    # Launch arguments
    # -----------------------------------------------------------------
    declare_world_arg = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_gazebo, 'worlds', 'orbibot_room.sdf'),
        description='Path to Gazebo world SDF file',
    )
    declare_use_rviz_arg = DeclareLaunchArgument(
        'use_rviz',
        default_value='true',
        description='Launch RViz for robot visualization',
    )
    declare_gz_headless_arg = DeclareLaunchArgument(
        'headless',
        default_value='false',
        description='Run Gazebo without GUI (server only)',
    )

    world = LaunchConfiguration('world')
    use_rviz = LaunchConfiguration('use_rviz')
    headless = LaunchConfiguration('headless')

    # -----------------------------------------------------------------
    # Robot description (xacro → robot_description param)
    # use_sim_time=true so RSP timestamps align with /clock
    # -----------------------------------------------------------------
    urdf_file = os.path.join(pkg_description, 'urdf', 'orbibot.urdf.xacro')
    robot_description = ParameterValue(
        Command(['xacro ', urdf_file]),
        value_type=str,
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
    )

    # -----------------------------------------------------------------
    # Gazebo Harmonic (gz-sim)
    # -g flag: GUI  | -s flag: server only (headless)
    # -r: run simulation immediately
    # -----------------------------------------------------------------
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py',
            ])
        ]),
        launch_arguments={
            'gz_args': ['-r ', world],
        }.items(),
    )

    # -----------------------------------------------------------------
    # Spawn OrbiBot into the running Gazebo world
    # Delayed 2s to ensure Gazebo is ready before spawn
    # -----------------------------------------------------------------
    spawn_robot = TimerAction(
        period=2.0,
        actions=[
            LogInfo(msg='[Sim] Spawning OrbiBot into Gazebo...'),
            Node(
                package='ros_gz_sim',
                executable='create',
                name='spawn_orbibot',
                arguments=[
                    '-name', 'orbibot',
                    '-topic', 'robot_description',
                    '-x', '0.0',
                    '-y', '0.0',
                    '-z', '0.05',
                    '-R', '0.0',
                    '-P', '0.0',
                    '-Y', '0.0',
                ],
                output='screen',
            ),
        ],
    )

    # -----------------------------------------------------------------
    # ROS ↔ Gazebo bridge (cmd_vel, odom, scan, imu, tf, clock)
    # Delayed 3s — bridge must start after Gazebo topics are available
    # -----------------------------------------------------------------
    bridge = TimerAction(
        period=3.0,
        actions=[
            LogInfo(msg='[Sim] Starting ROS-Gazebo topic bridge...'),
            Node(
                package='ros_gz_bridge',
                executable='parameter_bridge',
                name='gz_bridge',
                parameters=[{
                    'config_file': os.path.join(pkg_gazebo, 'config', 'gz_bridge.yaml'),
                    'use_sim_time': True,
                }],
                output='screen',
            ),
        ],
    )

    # -----------------------------------------------------------------
    # RViz (optional)
    # -----------------------------------------------------------------
    rviz_config = os.path.join(pkg_description, 'rviz', 'orbibot.rviz')
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(use_rviz),
        output='screen',
    )

    return LaunchDescription([
        declare_world_arg,
        declare_use_rviz_arg,
        declare_gz_headless_arg,
        LogInfo(msg='[Sim] OrbiBot Gazebo Harmonic simulation starting...'),
        LogInfo(msg='[Sim] NOTE: Mecanum lateral strafe is approximated (DiffDrive)'),
        robot_state_publisher,
        gz_sim,
        spawn_robot,
        bridge,
        rviz,
    ])
