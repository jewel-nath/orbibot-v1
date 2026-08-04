#!/usr/bin/env python3
"""
OrbiBot command arbitration.

Starts twist_mux as the single writer of /cmd_vel. Every other source publishes
to its own topic — see config/twist_mux.yaml for the priorities and timeouts,
and docs/architecture/command-pipeline.md for why.

This lives in orbibot_bringup rather than in any one package because it
arbitrates between four of them: orbibot_webgui, orbibot_agent,
orbibot_navigation and (reserved) orbibot_teleop.

Usage:
    ros2 launch orbibot_bringup twist_mux.launch.py
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    default_config = PathJoinSubstitution([
        FindPackageShare('orbibot_bringup'), 'config', 'twist_mux.yaml'
    ])

    declare_config_arg = DeclareLaunchArgument(
        'twist_mux_config',
        default_value=default_config,
        description='Priorities and timeouts for every cmd_vel source'
    )

    config = LaunchConfiguration('twist_mux_config')

    # twist_mux publishes its result on cmd_vel_out; the driver listens on
    # /cmd_vel. Remap rather than rename so the node keeps its stock topic and
    # anyone reading twist_mux's own documentation still recognises it.
    twist_mux_node = Node(
        package='twist_mux',
        executable='twist_mux',
        name='twist_mux',
        output='screen',
        parameters=[config],
        remappings=[('cmd_vel_out', 'cmd_vel')],
        respawn=True,
        respawn_delay=2.0,
    )

    # Without this, "silence means stop" is not true: twist_mux is event driven
    # and publishes nothing at all when every input goes quiet. See
    # orbibot_bringup/cmd_vel_idle.py and the `idle` block in the config.
    cmd_vel_idle_node = Node(
        package='orbibot_bringup',
        executable='cmd_vel_idle',
        name='cmd_vel_idle',
        output='screen',
        respawn=True,
        respawn_delay=2.0,
    )

    # Roadmap 2.5 — the operator should never have to guess who has control.
    cmd_vel_source_node = Node(
        package='orbibot_bringup',
        executable='cmd_vel_source',
        name='cmd_vel_source',
        output='screen',
        respawn=True,
        respawn_delay=2.0,
    )

    return LaunchDescription([
        declare_config_arg,
        LogInfo(msg='[Bringup] Command arbitration — twist_mux owns /cmd_vel; '
                    'sources: estop > joy > web > agent > nav > idle'),
        twist_mux_node,
        cmd_vel_idle_node,
        cmd_vel_source_node,
    ])
