#!/usr/bin/env python3
"""
OrbiBot Sensor System Launch
Configurable sensor launching for different sensor combinations
Uses individual sensor launch files from orbibot_sensors package
"""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, EqualsSubstitution, OrSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """Generate sensor launch description"""
    
    # Launch arguments
    sensors_arg = DeclareLaunchArgument(
        'sensors',
        default_value='both',
        description='Sensor configuration: lidar, camera, or both',
        choices=['lidar', 'camera', 'both']
    )
    
    log_level_arg = DeclareLaunchArgument(
        'log_level',
        default_value='info',
        description='Log level for all nodes'
    )
    
    enable_camera_to_scan_arg = DeclareLaunchArgument(
        'enable_camera_to_scan',
        default_value='false',
        description='Enable camera depth to laser scan conversion'
    )
    
    # Launch configuration
    sensors = LaunchConfiguration('sensors')
    log_level = LaunchConfiguration('log_level')
    enable_camera_to_scan = LaunchConfiguration('enable_camera_to_scan')
    
    # LIDAR Launch (using orbibot_sensors lidar.launch.py)
    lidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_sensors'),
                'launch',
                'lidar.launch.py'
            ])
        ]),
        launch_arguments={
            'serial_port': '/dev/lidar',
            'frame_id': 'lidar_link',
            'scan_mode': 'Express',
        }.items(),
        condition=IfCondition(OrSubstitution(
            EqualsSubstitution(sensors, 'lidar'),
            EqualsSubstitution(sensors, 'both')
        ))
    )
    
    # RealSense Camera Launch (using orbibot_sensors camera.launch.py)
    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_sensors'),
                'launch',
                'camera.launch.py'
            ])
        ]),
        launch_arguments={
            'camera_name': 'camera',
            'enable_color': 'true',
            'enable_depth': 'true',
            'enable_pointcloud': 'false',  # Pointcloud disabled — too heavy for RPi
            'color_width': '424',
            'color_height': '240',
            'color_fps': '15',
        }.items(),
        condition=IfCondition(OrSubstitution(
            EqualsSubstitution(sensors, 'camera'),
            EqualsSubstitution(sensors, 'both')
        ))
    )
    
    # Camera depth to LaserScan converter (for RealSense navigation)
    camera_to_scan_node = Node(
        package='depthimage_to_laserscan',
        executable='depthimage_to_laserscan_node',
        name='camera_to_scan',
        output='screen',
        parameters=[{
            'output_frame': 'camera_depth_frame',
            'range_min': 0.4,
            'range_max': 4.0,
            'scan_height': 100,
            'scan_time': 0.033,
        }],
        remappings=[
            ('depth', '/camera/depth/image_rect_raw'),
            ('depth_camera_info', '/camera/depth/camera_info'),
            ('scan', '/scan_from_camera'),
        ],
        arguments=['--ros-args', '--log-level', log_level],
        condition=IfCondition(
            EqualsSubstitution(enable_camera_to_scan, 'true')
        )
    )
    
    return LaunchDescription([
        # Launch arguments
        sensors_arg,
        log_level_arg,
        enable_camera_to_scan_arg,
        
        # Sensor launches
        lidar_launch,
        camera_launch,
        camera_to_scan_node,
    ])