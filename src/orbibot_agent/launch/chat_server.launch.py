"""Launch chat server for OrbiBot Agent."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'port',
            default_value='8082',
            description='HTTP server port'
        ),
        DeclareLaunchArgument(
            'config',
            default_value='',
            description='Path to config file'
        ),
        Node(
            package='orbibot_agent',
            executable='chat_server',
            name='chat_server',
            output='screen',
            parameters=[{
                'port': LaunchConfiguration('port'),
                'config_file': LaunchConfiguration('config'),
            }]
        ),
    ])