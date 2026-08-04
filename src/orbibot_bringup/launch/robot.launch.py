#!/usr/bin/env python3
"""
OrbiBot Robot Base Launch
Launches all core components: description, hardware, lidar, EKF.
Optionally launches camera.

Usage:
    ros2 launch orbibot_bringup robot.launch.py
    ros2 launch orbibot_bringup robot.launch.py use_camera:=true
"""

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    LogInfo,
    TimerAction,
)
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    declare_use_camera_arg = DeclareLaunchArgument(
        'use_camera',
        default_value='false',
        description='Launch RealSense camera'
    )

    # Both serial devices are named here, under distinct argument names, and
    # passed explicitly into the includes below. The included launch files each
    # call their argument 'serial_port'; sharing one context means the first one
    # included wins for everybody. Naming them apart here makes that impossible.
    declare_motor_port_arg = DeclareLaunchArgument(
        'motor_port',
        default_value='/dev/motordriver',
        description='Serial port for the ROSMaster motor board'
    )

    declare_lidar_port_arg = DeclareLaunchArgument(
        'lidar_port',
        default_value='/dev/lidar',
        description='Serial port for the RPLidar A1'
    )

    use_camera = LaunchConfiguration('use_camera')
    motor_port = LaunchConfiguration('motor_port')
    lidar_port = LaunchConfiguration('lidar_port')

    log_startup = LogInfo(
        msg=['[Bringup] Robot base started — camera: ', use_camera]
    )

    # Robot Description (URDF + robot_state_publisher)
    description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_description'),
                'launch',
                'description.launch.py'
            ])
        ])
    )

    # Command arbitration. Started before the hardware node so that /cmd_vel has
    # exactly one publisher from the first moment anything could command motion.
    twist_mux_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_bringup'),
                'launch',
                'twist_mux.launch.py'
            ])
        ])
    )

    # Hardware Interface (serial bridge to firmware + system monitor)
    hardware_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_hardware'),
                'launch',
                'hardware.launch.py'
            ])
        ]),
        launch_arguments={'serial_port': motor_port}.items()
    )

    # Lidar, delayed so the hardware node has opened /dev/motordriver first.
    #
    # This used to be ExecuteProcess(['ros2', 'launch', ...]) "for isolation, to
    # avoid USB serial conflict between /dev/motordriver and /dev/lidar". The
    # symptom was real; the explanation was not. There is no device conflict —
    # the two have separate udev symlinks and separate processes. What actually
    # happened is a **launch argument name collision**:
    #
    #   hardware.launch.py declares 'serial_port', default /dev/motordriver
    #   lidar.launch.py    declares 'serial_port', default /dev/lidar
    #
    # Included launch files share one context, and a DeclareLaunchArgument does
    # not overwrite a value already in it. Whichever is included first wins, so
    # rplidar_composition opened /dev/motordriver, sent A1 commands to the motor
    # board and died with RESULT_OPERATION_TIMEOUT. Verified 2026-08-04:
    # `ros2 param get /rplidar_node serial_port` returned /dev/motordriver.
    #
    # Running it as a subprocess hid this, because a separate `ros2 launch` gets
    # a separate context — at the cost of a second launch service that had to be
    # torn down separately, and that orphaned itself. See bringup-issue.md.
    #
    # Passing launch_arguments explicitly is the fix: it pins the value instead
    # of inheriting whatever the context happens to hold. Every include below
    # does this, so adding a package later cannot silently repoint a device.
    lidar_launch = TimerAction(
        period=5.0,
        actions=[
            LogInfo(msg='[Bringup] Starting LiDAR...'),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([
                    PathJoinSubstitution([
                        FindPackageShare('orbibot_sensors'),
                        'launch',
                        'lidar.launch.py'
                    ])
                ]),
                launch_arguments={'serial_port': lidar_port}.items()
            )
        ]
    )

    # EKF Localization (delayed — wait for hardware_node to publish /odom)
    localization_launch = TimerAction(
        period=3.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource([
                    PathJoinSubstitution([
                        FindPackageShare('orbibot_localization'),
                        'launch',
                        'localization.launch.py'
                    ])
                ])
            )
        ]
    )

    # Camera (optional)
    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('orbibot_sensors'),
                'launch',
                'camera.launch.py'
            ])
        ]),
        condition=IfCondition(use_camera)
    )

    return LaunchDescription([
        declare_use_camera_arg,
        declare_motor_port_arg,
        declare_lidar_port_arg,
        log_startup,
        description_launch,
        twist_mux_launch,
        hardware_launch,
        lidar_launch,
        localization_launch,
        camera_launch,
    ])
