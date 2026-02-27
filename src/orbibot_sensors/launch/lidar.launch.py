#!/usr/bin/env python3

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # Get package directory
    pkg_orbibot_sensors = get_package_share_directory('orbibot_sensors')
    
    # Declare launch arguments
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/lidar',
        description='Serial port for RPLIDAR'
    )
    
    frame_id_arg = DeclareLaunchArgument(
        'frame_id',
        default_value='lidar_link',
        description='Frame ID for laser scan'
    )
    
    scan_mode_arg = DeclareLaunchArgument(
        'scan_mode',
        default_value='Express',
        description='Scan mode for RPLIDAR (Express for better angular resolution)'
    )

    
    # Parameter file path
    rplidar_params_file = os.path.join(
        pkg_orbibot_sensors,
        'config',
        'rplidar_params.yaml'
    )
    
    # RPLIDAR node
    rplidar_node = Node(
        package='rplidar_ros',
        executable='rplidar_composition',
        name='rplidar_node',
        parameters=[
            rplidar_params_file,
            {
                'serial_port': LaunchConfiguration('serial_port'),
                'frame_id': LaunchConfiguration('frame_id'),
                'scan_mode': LaunchConfiguration('scan_mode'),
            }
        ],
        output='screen',
        respawn=True,
        respawn_delay=2.0,
    )

    # Log info
    log_info = LogInfo(
        msg='[Sensors] Starting RPLIDAR A1 — mode: Express, port: /dev/lidar'
    )
    
    return LaunchDescription([
        serial_port_arg,
        frame_id_arg,
        scan_mode_arg,
        log_info,
        rplidar_node,
    ])