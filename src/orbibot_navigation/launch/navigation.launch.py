#!/usr/bin/env python3
"""
OrbiBot Navigation Launch — Nav2 Stack
Launches the full Nav2 navigation stack with AMCL, planners, and controllers.
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

    declare_params_file_arg = DeclareLaunchArgument(
        'params_file',
        default_value=os.path.join(nav_pkg_dir, 'config', 'nav2_params.yaml'),
        description='Full path to the Nav2 parameters file'
    )

    declare_map_file_arg = DeclareLaunchArgument(
        'map_file',
        default_value=os.path.join(nav_pkg_dir, 'maps', 'map.yaml'),
        description='Full path to map file'
    )

    declare_autostart_arg = DeclareLaunchArgument(
        'autostart',
        default_value='true',
        description='Automatically startup the Nav2 stack'
    )

    declare_use_composition_arg = DeclareLaunchArgument(
        'use_composition',
        default_value='False',
        description='Use composed bringup if True'
    )

    declare_use_respawn_arg = DeclareLaunchArgument(
        'use_respawn',
        default_value='False',
        description='Whether to respawn if a node crashes'
    )

    params_file = LaunchConfiguration('params_file')
    map_file = LaunchConfiguration('map_file')
    autostart = LaunchConfiguration('autostart')
    use_composition = LaunchConfiguration('use_composition')
    use_respawn = LaunchConfiguration('use_respawn')

    log_startup = LogInfo(
        msg=['[Navigation] Nav2 stack started — params: ', params_file, ', map: ', map_file]
    )

    nav2_bringup_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('nav2_bringup'),
                'launch',
                'bringup_launch.py'
            ])
        ]),
        launch_arguments={
            'map': map_file,
            'params_file': params_file,
            'autostart': autostart,
            'use_composition': use_composition,
            'use_respawn': use_respawn,
        }.items()
    )

    return LaunchDescription([
        declare_params_file_arg,
        declare_map_file_arg,
        declare_autostart_arg,
        declare_use_composition_arg,
        declare_use_respawn_arg,
        log_startup,
        nav2_bringup_launch,
    ])
