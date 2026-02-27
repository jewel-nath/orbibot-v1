"""
Web GUI Launch File

Launches:
- rosapi (ROS API for service/topic introspection)
- rosbridge_server (WebSocket bridge for web UI)
- webrtc_server (WebRTC low-latency video streaming) - optional

Usage:
    ros2 launch orbibot_webgui webgui.launch.py                  # With video
    ros2 launch orbibot_webgui webgui.launch.py use_video:=false # Without video
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    # Declare launch arguments
    rosbridge_port_arg = DeclareLaunchArgument(
        'rosbridge_port',
        default_value='9090',
        description='Port for rosbridge WebSocket server'
    )

    use_video_arg = DeclareLaunchArgument(
        'use_video',
        default_value='true',
        description='Enable WebRTC server for camera streaming'
    )

    webrtc_port_arg = DeclareLaunchArgument(
        'webrtc_port',
        default_value='8081',
        description='Port for WebRTC signaling server'
    )

    # ROS API Node (provides service/topic introspection)
    rosapi_node = Node(
        package='rosapi',
        executable='rosapi_node',
        name='rosapi',
        output='screen',
    )

    # ROS Bridge WebSocket Server
    rosbridge_node = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        parameters=[{
            'port': LaunchConfiguration('rosbridge_port'),
            'address': '0.0.0.0',
            'retry_startup_delay': 2.0,
        }],
        output='screen',
    )

    # WebRTC Video Server (optional)
    webrtc_server_node = Node(
        package='orbibot_webgui',
        executable='webrtc_server',
        name='orbibot_webrtc_server',
        condition=IfCondition(LaunchConfiguration('use_video')),
        parameters=[{
            'image_topic': '/camera/color/image_raw',
            'port': LaunchConfiguration('webrtc_port'),
            'image_width': 640,
            'image_height': 480,
        }],
        output='screen',
        emulate_tty=True,
    )

    return LaunchDescription([
        rosbridge_port_arg,
        use_video_arg,
        webrtc_port_arg,
        rosapi_node,
        rosbridge_node,
        webrtc_server_node,
    ])
