"""Launch MCP server for OrbiBot Agent."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'config',
            default_value='',
            description='Path to config file'
        ),
        DeclareLaunchArgument(
            'provider',
            default_value='gemini',
            description='Default LLM provider'
        ),
        Node(
            package='orbibot_agent',
            executable='mcp_server',
            name='mcp_server',
            output='screen',
            parameters=[{
                'config_file': LaunchConfiguration('config'),
                'default_provider': LaunchConfiguration('provider'),
            }]
        ),
    ])