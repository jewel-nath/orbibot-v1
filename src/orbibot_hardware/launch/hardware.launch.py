#!/usr/bin/env python3
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, ExecuteProcess, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    """
    Launch OrbiBot hardware interface
    """
    
    # Package directories
    pkg_orbibot_hardware = get_package_share_directory('orbibot_hardware')
    
    # Configuration files
    hardware_config = PathJoinSubstitution([
        pkg_orbibot_hardware, 'config', 'hardware_params.yaml'
    ])
    
    declare_serial_port = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/motordriver', 
        description='Serial port for motor driver'
    )
    
    # Default false, deliberately. Launching the stack must not arm four motors
    # on a robot that may be on the floor. Enabling is an explicit act:
    #   ros2 launch orbibot_bringup robot.launch.py motors_enabled:=true
    # or the dashboard's motor-enable control, or the SetMotorEnable service.
    #
    # This defaulted to 'true' until 2026-08-03. hardware_node.py never enables
    # motors itself, so reading the node gave the opposite answer to what the
    # launch actually did — see hardware-issue.md HW-BUG-9.
    declare_start_enabled = DeclareLaunchArgument(
        'motors_enabled',
        default_value='false',
        description='Arm the motors at startup. Default false — enabling is explicit.'
    )
    
    # Launch configuration variables
    serial_port = LaunchConfiguration('serial_port')
    motors_enabled = LaunchConfiguration('motors_enabled')
    
    # Hardware interface node
    hardware_node = Node(
        package='orbibot_hardware',
        executable='hardware_node',
        name='orbibot_hardware_node',
        output='screen',
        respawn=True,
        respawn_delay=3.0,
        parameters=[
            hardware_config,
            {
                'hardware.serial_port': serial_port,
            }
        ]
    )
    
    # Motor enable: single call after delay so hardware node and service are ready.
    # Only runs when motors_enabled:=true is passed explicitly — see above.
    motor_enable_cmd = TimerAction(
        period=6.0,
        actions=[
            LogInfo(msg='[Hardware] ⚠ ARMING MOTORS — motors_enabled:=true was passed'),
            ExecuteProcess(
                cmd=['ros2', 'service', 'call', '/orbibot/set_motor_enable',
                     'orbibot_msgs/srv/SetMotorEnable', '{enable: true}'],
                name='motor_enable_startup',
                condition=IfCondition(motors_enabled)
            )
        ],
        condition=IfCondition(motors_enabled)
    )
    
    log_info = LogInfo(
        msg=['[Hardware] Starting hardware interface — port: ', serial_port]
    )

    # System Monitor (CPU, RAM, temp for web dashboard)
    system_monitor_node = Node(
        package='orbibot_hardware',
        executable='system_monitor',
        name='system_monitor',
        output='screen',
        respawn=True,
        respawn_delay=5.0,
    )

    return LaunchDescription([
        # Arguments
        declare_serial_port,
        declare_start_enabled,

        log_info,

        # Nodes
        hardware_node,
        system_monitor_node,

        # Motor enable (when motors_enabled is true)
        motor_enable_cmd,
    ])