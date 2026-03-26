#!/usr/bin/env python3
"""
OrbiBot SLAM Launch — Mapping Mode
Uses slam_toolbox async_slam_toolbox_node with LifecycleNode management.
"""
import os
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    LogInfo,
    EmitEvent,
    RegisterEventHandler,
)
from launch.conditions import IfCondition
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from launch.substitutions import (
    LaunchConfiguration,
    AndSubstitution,
    NotSubstitution,
)
from launch_ros.actions import LifecycleNode
from launch_ros.events.lifecycle import matches_node_name
from lifecycle_msgs.msg import Transition
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    slam_pkg_dir = get_package_share_directory('orbibot_slam')

    use_sim_time_arg = DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation clock (set true when running with Gazebo)',
    )

    autostart_arg = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically configure and activate SLAM node'
    )

    use_lifecycle_manager_arg = DeclareLaunchArgument(
        'use_lifecycle_manager',
        default_value='false',
        description='Use external lifecycle manager (e.g., Nav2 lifecycle manager)'
    )

    slam_params_file_arg = DeclareLaunchArgument(
        'slam_params_file',
        default_value=os.path.join(slam_pkg_dir, 'config', 'slam_params.yaml'),
        description='Path to SLAM parameters file'
    )

    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Log level for SLAM node'
    )

    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    use_lifecycle_manager = LaunchConfiguration('use_lifecycle_manager')
    slam_params_file = LaunchConfiguration('slam_params_file')
    log_level = LaunchConfiguration('log_level')

    should_autostart = AndSubstitution(autostart, NotSubstitution(use_lifecycle_manager))

    slam_toolbox_node = LifecycleNode(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        namespace='',
        output='screen',
        parameters=[slam_params_file, {'use_sim_time': use_sim_time}],
        arguments=['--ros-args', '--log-level', log_level],
    )

    configure_event = EmitEvent(
        event=ChangeState(
            lifecycle_node_matcher=matches_node_name(node_name='slam_toolbox'),
            transition_id=Transition.TRANSITION_CONFIGURE,
        ),
        condition=IfCondition(should_autostart),
    )

    activate_event_handler = RegisterEventHandler(
        OnStateTransition(
            target_lifecycle_node=slam_toolbox_node,
            start_state='configuring',
            goal_state='inactive',
            entities=[
                LogInfo(msg='[SLAM] Configured, activating...'),
                EmitEvent(
                    event=ChangeState(
                        lifecycle_node_matcher=matches_node_name(node_name='slam_toolbox'),
                        transition_id=Transition.TRANSITION_ACTIVATE,
                    )
                ),
            ],
        ),
        condition=IfCondition(should_autostart),
    )

    log_startup = LogInfo(
        msg=[
            '[SLAM] Mapping mode started — scan: /scan, frames: odom → base_footprint → lidar_link',
            '\n       params: ', slam_params_file,
        ]
    )

    return LaunchDescription([
        use_sim_time_arg,
        autostart_arg,
        use_lifecycle_manager_arg,
        slam_params_file_arg,
        log_level_arg,
        log_startup,
        slam_toolbox_node,
        configure_event,
        activate_event_handler,
    ])
