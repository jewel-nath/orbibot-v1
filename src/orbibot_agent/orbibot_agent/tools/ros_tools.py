"""ROS interface tool definitions — topics, services, actions, generic publish."""

from typing import Any, Dict


def register(registry, ros_bridge, safety_manager) -> None:
    """Register ROS interface tools (topics, services, actions)."""

    registry.register_tool(
        name='list_topics',
        description='List all active ROS topics.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: {'topics': ros_bridge.list_topics(), 'count': len(ros_bridge.list_topics())},
    )

    registry.register_tool(
        name='list_services',
        description='List all available ROS services with their types.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: {'services': ros_bridge.list_services(), 'count': len(ros_bridge.list_services())},
    )

    registry.register_tool(
        name='ros2_service_call',
        description='Call a ROS service with specified request data.',
        parameters={
            'type': 'object',
            'properties': {
                'service_name': {'type': 'string', 'description': 'Full service name'},
                'service_type': {'type': 'string', 'description': 'Service type (e.g. "nav2_msgs/srv/LoadMap")'},
                'request': {'type': 'object', 'description': 'Service request fields'},
                'timeout': {'type': 'number', 'description': 'Timeout in seconds (default 5)', 'default': 5.0},
            },
            'required': ['service_name', 'service_type', 'request'],
        },
        handler=lambda service_name, service_type, request, timeout=5.0: (
            ros_bridge.call_service(service_name, service_type, request, timeout)),
    )

    # -- Actions --

    registry.register_tool(
        name='ros2_list_actions',
        description='List all available ROS action servers.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: {'actions': ros_bridge.list_actions(), 'count': len(ros_bridge.list_actions())},
    )

    registry.register_tool(
        name='ros2_send_action_goal',
        description='Send a goal to a ROS action server. Returns goal_id for tracking.',
        parameters={
            'type': 'object',
            'properties': {
                'action_name': {'type': 'string', 'description': 'Action name'},
                'action_type': {'type': 'string', 'description': 'Action type'},
                'goal': {'type': 'object', 'description': 'Goal fields as dictionary'},
                'timeout': {'type': 'number', 'description': 'Timeout in seconds (default 30)', 'default': 30.0},
            },
            'required': ['action_name', 'action_type', 'goal'],
        },
        handler=lambda action_name, action_type, goal, timeout=30.0: (
            ros_bridge.send_action_goal(action_name, action_type, goal, timeout=timeout)),
    )

    registry.register_tool(
        name='ros2_cancel_action_goal',
        description='Cancel a specific action goal using its goal_id.',
        parameters={
            'type': 'object',
            'properties': {'goal_id': {'type': 'string', 'description': 'Goal ID to cancel'}},
            'required': ['goal_id'],
        },
        handler=lambda goal_id: ros_bridge.cancel_action_goal(goal_id),
    )

    registry.register_tool(
        name='ros2_action_request_result',
        description='Get the result of an action goal.',
        parameters={
            'type': 'object',
            'properties': {
                'goal_id': {'type': 'string', 'description': 'Goal ID'},
                'timeout': {'type': 'number', 'description': 'Timeout (default 10)', 'default': 10.0},
            },
            'required': ['goal_id'],
        },
        handler=lambda goal_id, timeout=10.0: ros_bridge.get_action_result(goal_id, timeout),
    )

    registry.register_tool(
        name='ros2_action_subscribe_status',
        description='Get current status of an action server.',
        parameters={
            'type': 'object',
            'properties': {'action_name': {'type': 'string', 'description': 'Action name'}},
            'required': ['action_name'],
        },
        handler=lambda action_name: ros_bridge.get_action_status(action_name),
    )

    registry.register_tool(
        name='ros2_list_active_goals',
        description='List all currently active action goals.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: {'active_goals': ros_bridge.get_active_goals(), 'count': len(ros_bridge.get_active_goals())},
    )

    # -- Generic publish --

    registry.register_tool(
        name='ros2_topic_publish',
        description='Publish a one-shot message to any ROS 2 topic.',
        parameters={
            'type': 'object',
            'properties': {
                'topic': {'type': 'string', 'description': 'Full topic name'},
                'msg_type': {'type': 'string', 'description': 'Message type (e.g. "std_msgs/msg/String")'},
                'data': {'type': 'object', 'description': 'Message fields as dict'},
            },
            'required': ['topic', 'msg_type', 'data'],
        },
        handler=lambda topic, msg_type, data: ros_bridge.publish_topic(topic, msg_type, data),
    )
