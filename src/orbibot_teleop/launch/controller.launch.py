#!/usr/bin/env python3
"""
Mecanum Teleop Launch using S4/PS5 DualSense controller
Launches mecanum controller with all holonomic movement modes
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, LogInfo
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """Generate launch description for mecanum teleop"""

    # Get package path
    pkg_share = FindPackageShare('orbibot_teleop')

    # Configuration file path
    config_file = PathJoinSubstitution([
        pkg_share, 'config', 'controller.yaml'
    ])

    # Launch arguments
    device_arg = DeclareLaunchArgument(
        'device',
        default_value='/dev/input/js0',
        description='Joystick device path'
    )

    max_linear_arg = DeclareLaunchArgument(
        'max_linear_speed',
        default_value='0.3',
        description='Maximum linear speed (m/s) for advanced mode'
    )

    max_angular_arg = DeclareLaunchArgument(
        'max_angular_speed',
        default_value='1.0',
        description='Maximum angular speed (rad/s) for advanced mode'
    )

    use_keyboard_arg = DeclareLaunchArgument(
        'use_keyboard',
        default_value='false',
        description='Use keyboard teleop instead of gamepad'
    )

    # Joy node
    joy_node = Node(
        package='joy',
        executable='joy_node',
        name='joy_node',
        parameters=[{
            'device': LaunchConfiguration('device'),
            'deadzone': 0.08,
            'autorepeat_rate': 20.0,
        }],
        output='screen',
        respawn=True,
        respawn_delay=2.0,
    )

    # Controller node (gamepad)
    controller_node = Node(
        package='orbibot_teleop',
        executable='controller',
        name='controller',
        parameters=[
            config_file,
            {
                'max_linear_speed': LaunchConfiguration('max_linear_speed'),
                'max_angular_speed': LaunchConfiguration('max_angular_speed'),
            }
        ],
        remappings=[
            ('cmd_vel', '/cmd_vel'),
        ],
        output='screen',
        respawn=True,
        respawn_delay=2.0,
    )

    # Keyboard teleop (alternative to gamepad)
    keyboard_node = Node(
        package='teleop_twist_keyboard',
        executable='teleop_twist_keyboard',
        name='teleop_twist_keyboard',
        output='screen',
        prefix='xterm -e',
        remappings=[('cmd_vel', '/cmd_vel')],
        condition=IfCondition(LaunchConfiguration('use_keyboard')),
    )

    log_info = LogInfo(
        msg='[Teleop] Starting controller'
    )

    return LaunchDescription([
        device_arg,
        max_linear_arg,
        max_angular_arg,
        use_keyboard_arg,
        log_info,
        joy_node,
        controller_node,
        keyboard_node,
    ])
