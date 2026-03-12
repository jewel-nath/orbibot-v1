"""Launch chat server for OrbiBot Agent."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node

# Pass through env vars so the chat server process sees them (API keys and
# ORBIBOT_WS for finding src/orbibot_agent/.env.local when launched by ros2 launch).
_API_KEY_VARS = ('GEMINI_API_KEY', 'ANTHROPIC_API_KEY', 'MOONSHOT_API_KEY')


def _get_api_env():
    env = {k: os.environ[k] for k in _API_KEY_VARS if k in os.environ}
    if 'ORBIBOT_WS' in os.environ:
        env['ORBIBOT_WS'] = os.path.expanduser(os.environ['ORBIBOT_WS'].strip())
    return env


def generate_launch_description():
    pkg_dir = get_package_share_directory('orbibot_agent')
    default_config = PathJoinSubstitution([pkg_dir, 'config', 'agent_params.yaml'])

    return LaunchDescription([
        DeclareLaunchArgument(
            'port',
            default_value='8082',
            description='HTTP server port'
        ),
        DeclareLaunchArgument(
            'config',
            default_value=default_config,
            description='Path to config file (default: package agent_params.yaml)'
        ),
        Node(
            package='orbibot_agent',
            executable='chat_server',
            name='orbibot_chat_server',
            output='screen',
            parameters=[{
                'port': LaunchConfiguration('port'),
                'config_file': LaunchConfiguration('config'),
            }],
            additional_env=_get_api_env(),
        ),
    ])