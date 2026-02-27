"""Tool registry for OrbiBot Agent.

Manages all available tools and their schemas for LLM function calling.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

from ..core.ros_bridge import RosBridge
from ..core.safety_manager import SafetyManager

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for all robot tools."""

    def __init__(self, ros_bridge: RosBridge, safety_manager: SafetyManager):
        """Initialize tool registry.

        Args:
            ros_bridge: ROS bridge for robot communication
            safety_manager: Safety manager for validation
        """
        self._ros_bridge = ros_bridge
        self._safety_manager = safety_manager
        self._tools: Dict[str, Dict] = {}
        self._handlers: Dict[str, Callable] = {}

        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register all default tools."""
        # Motion tools
        self.register_tool(
            name='move_robot',
            description='Move the robot with specified velocities for a duration. '
                       'Use positive vx for forward, negative for backward. '
                       'Use positive vy for left, negative for right (mecanum). '
                       'Use positive wz for counter-clockwise rotation.',
            parameters={
                'type': 'object',
                'properties': {
                    'vx': {
                        'type': 'number',
                        'description': 'Forward/backward velocity in m/s (range: -0.5 to 0.5)'
                    },
                    'vy': {
                        'type': 'number',
                        'description': 'Left/right velocity in m/s (range: -0.5 to 0.5, mecanum)'
                    },
                    'wz': {
                        'type': 'number',
                        'description': 'Angular velocity in rad/s (range: -2.0 to 2.0)'
                    },
                    'duration': {
                        'type': 'number',
                        'description': 'Duration in seconds (range: 0.1 to 10.0)'
                    }
                },
                'required': ['vx', 'vy', 'wz', 'duration']
            },
            handler=self._handle_move_robot
        )

        self.register_tool(
            name='stop_robot',
            description='Immediately stop all robot motion (emergency stop).',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_stop_robot
        )

        # Sensor tools
        self.register_tool(
            name='get_battery',
            description='Get battery voltage and status level.',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_get_battery
        )

        self.register_tool(
            name='get_imu',
            description='Get IMU orientation (roll, pitch, yaw) and angular velocities.',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_get_imu
        )

        self.register_tool(
            name='get_odometry',
            description='Get robot position, orientation, and velocity from odometry.',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_get_odometry
        )

        self.register_tool(
            name='get_robot_position',
            description='Get simplified robot position (x, y, yaw).',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_get_robot_position
        )

        self.register_tool(
            name='get_lidar_summary',
            description='Get LiDAR scan summary with obstacle detection.',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_get_lidar_summary
        )

        # System tools
        self.register_tool(
            name='list_topics',
            description='List all active ROS topics.',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_list_topics
        )

        self.register_tool(
            name='get_system_status',
            description='Get comprehensive system status including CPU, RAM, temperature, and battery.',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_get_system_status
        )

        # Service tools
        self.register_tool(
            name='list_services',
            description='List all available ROS services with their types.',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_list_services
        )

        self.register_tool(
            name='ros2_service_call',
            description='Call a ROS service with specified request data. '
                       'Common services: /map_server/load_map (nav2_msgs/srv/LoadMap), '
                       '/planner_server/change_state (lifecycle_msgs/srv/ChangeState), '
                       '/global_costmap/clear_entirely_global_costmap (nav2_msgs/srv/ClearEntireCostmap).',
            parameters={
                'type': 'object',
                'properties': {
                    'service_name': {
                        'type': 'string',
                        'description': 'Full service name (e.g., "/map_server/load_map")'
                    },
                    'service_type': {
                        'type': 'string',
                        'description': 'Service type (e.g., "nav2_msgs/srv/LoadMap", "lifecycle_msgs/srv/ChangeState")'
                    },
                    'request': {
                        'type': 'object',
                        'description': 'Service request fields as dictionary'
                    },
                    'timeout': {
                        'type': 'number',
                        'description': 'Timeout in seconds (default: 5.0)',
                        'default': 5.0
                    }
                },
                'required': ['service_name', 'service_type', 'request']
            },
            handler=self._handle_ros2_service_call
        )

        # Action tools
        self.register_tool(
            name='ros2_list_actions',
            description='List all available ROS action servers. '
                       'Common Nav2 actions: /navigate_to_pose, /navigate_through_poses.',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_ros2_list_actions
        )

        self.register_tool(
            name='ros2_send_action_goal',
            description='Send a goal to a ROS action server. '
                       'For Nav2 navigation: use action_type "nav2_msgs/action/NavigateToPose" '
                       'with goal containing pose (position x,y and orientation quaternion). '
                       'Returns a goal_id for tracking.',
            parameters={
                'type': 'object',
                'properties': {
                    'action_name': {
                        'type': 'string',
                        'description': 'Action name (e.g., "/navigate_to_pose")'
                    },
                    'action_type': {
                        'type': 'string',
                        'description': 'Action type (e.g., "nav2_msgs/action/NavigateToPose")'
                    },
                    'goal': {
                        'type': 'object',
                        'description': 'Goal fields as dictionary. For NavigateToPose: {"pose": {"pose": {"position": {"x": 1.0, "y": 0.0}, "orientation": {"x": 0, "y": 0, "z": 0, "w": 1}}}}'
                    },
                    'timeout': {
                        'type': 'number',
                        'description': 'Timeout in seconds (default: 30.0)',
                        'default': 30.0
                    }
                },
                'required': ['action_name', 'action_type', 'goal']
            },
            handler=self._handle_ros2_send_action_goal
        )

        self.register_tool(
            name='ros2_cancel_action_goal',
            description='Cancel a specific action goal using its goal_id.',
            parameters={
                'type': 'object',
                'properties': {
                    'goal_id': {
                        'type': 'string',
                        'description': 'Goal ID returned by ros2_send_action_goal'
                    }
                },
                'required': ['goal_id']
            },
            handler=self._handle_ros2_cancel_action_goal
        )

        self.register_tool(
            name='ros2_action_request_result',
            description='Get the result of an action goal. '
                       'Check the status field to see if it completed (SUCCEEDED, ABORTED, CANCELED).',
            parameters={
                'type': 'object',
                'properties': {
                    'goal_id': {
                        'type': 'string',
                        'description': 'Goal ID returned by ros2_send_action_goal'
                    },
                    'timeout': {
                        'type': 'number',
                        'description': 'Timeout to wait for result in seconds (default: 10.0)',
                        'default': 10.0
                    }
                },
                'required': ['goal_id']
            },
            handler=self._handle_ros2_action_request_result
        )

        self.register_tool(
            name='ros2_action_subscribe_status',
            description='Get the current status of an action server.',
            parameters={
                'type': 'object',
                'properties': {
                    'action_name': {
                        'type': 'string',
                        'description': 'Action name (e.g., "/navigate_to_pose")'
                    }
                },
                'required': ['action_name']
            },
            handler=self._handle_ros2_action_subscribe_status
        )

        self.register_tool(
            name='ros2_list_active_goals',
            description='List all currently active action goals with their status.',
            parameters={
                'type': 'object',
                'properties': {}
            },
            handler=self._handle_ros2_list_active_goals
        )

        logger.info(f'Registered {len(self._tools)} default tools')

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict,
        handler: Callable
    ) -> None:
        """Register a new tool.

        Args:
            name: Tool name
            description: Tool description
            parameters: JSON schema for parameters
            handler: Function to handle tool calls
        """
        self._tools[name] = {
            'type': 'function',
            'function': {
                'name': name,
                'description': description,
                'parameters': parameters
            }
        }
        self._handlers[name] = handler
        logger.debug(f'Registered tool: {name}')

    def get_tool_schemas(self) -> List[Dict]:
        """Get all tool schemas for LLM.

        Returns:
            List of tool schema dictionaries
        """
        return list(self._tools.values())

    def execute_tool(self, name: str, arguments: Dict) -> Dict:
        """Execute a tool by name.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result
        """
        if name not in self._handlers:
            return {'error': f'Unknown tool: {name}'}

        try:
            handler = self._handlers[name]
            return handler(**arguments)
        except Exception as e:
            logger.error(f'Tool {name} execution failed: {e}')
            return {'error': str(e)}

    # Tool handlers
    def _handle_move_robot(self, vx: float, vy: float, wz: float, duration: float) -> Dict:
        """Handle move_robot tool."""
        return self._ros_bridge.move_for_duration(vx, vy, wz, duration)

    def _handle_stop_robot(self) -> Dict:
        """Handle stop_robot tool."""
        self._ros_bridge.publish_stop()
        return {'status': 'stopped'}

    def _handle_get_battery(self) -> Dict:
        """Handle get_battery tool."""
        result = self._ros_bridge.get_battery_status()
        return result or {'error': 'Battery data unavailable'}

    def _handle_get_imu(self) -> Dict:
        """Handle get_imu tool."""
        result = self._ros_bridge.get_imu_data()
        return result or {'error': 'IMU data unavailable'}

    def _handle_get_odometry(self) -> Dict:
        """Handle get_odometry tool."""
        result = self._ros_bridge.get_odometry()
        return result or {'error': 'Odometry data unavailable'}

    def _handle_get_robot_position(self) -> Dict:
        """Handle get_robot_position tool."""
        odom = self._ros_bridge.get_odometry()
        if not odom:
            return {'error': 'Position data unavailable'}
        return {
            'x': odom['position']['x'],
            'y': odom['position']['y'],
            'yaw_deg': odom['yaw_deg']
        }

    def _handle_get_lidar_summary(self) -> Dict:
        """Handle get_lidar_summary tool."""
        result = self._ros_bridge.get_lidar_summary()
        return result or {'error': 'LiDAR data unavailable'}

    def _handle_list_topics(self) -> Dict:
        """Handle list_topics tool."""
        topics = self._ros_bridge.list_topics()
        return {'topics': topics, 'count': len(topics)}

    def _handle_get_system_status(self) -> Dict:
        """Handle get_system_status tool."""
        return self._ros_bridge.get_system_status()

    # Service tool handlers
    def _handle_list_services(self) -> Dict:
        """Handle list_services tool."""
        services = self._ros_bridge.list_services()
        return {'services': services, 'count': len(services)}

    def _handle_ros2_service_call(
        self,
        service_name: str,
        service_type: str,
        request: Dict,
        timeout: float = 5.0
    ) -> Dict:
        """Handle ros2_service_call tool."""
        return self._ros_bridge.call_service(service_name, service_type, request, timeout)

    # Action tool handlers
    def _handle_ros2_list_actions(self) -> Dict:
        """Handle ros2_list_actions tool."""
        actions = self._ros_bridge.list_actions()
        return {'actions': actions, 'count': len(actions)}

    def _handle_ros2_send_action_goal(
        self,
        action_name: str,
        action_type: str,
        goal: Dict,
        timeout: float = 30.0
    ) -> Dict:
        """Handle ros2_send_action_goal tool."""
        return self._ros_bridge.send_action_goal(action_name, action_type, goal, timeout=timeout)

    def _handle_ros2_cancel_action_goal(self, goal_id: str) -> Dict:
        """Handle ros2_cancel_action_goal tool."""
        return self._ros_bridge.cancel_action_goal(goal_id)

    def _handle_ros2_action_request_result(
        self,
        goal_id: str,
        timeout: float = 10.0
    ) -> Dict:
        """Handle ros2_action_request_result tool."""
        return self._ros_bridge.get_action_result(goal_id, timeout)

    def _handle_ros2_action_subscribe_status(self, action_name: str) -> Dict:
        """Handle ros2_action_subscribe_status tool."""
        return self._ros_bridge.get_action_status(action_name)

    def _handle_ros2_list_active_goals(self) -> Dict:
        """Handle ros2_list_active_goals tool."""
        goals = self._ros_bridge.get_active_goals()
        return {'active_goals': goals, 'count': len(goals)}