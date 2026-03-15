"""Tool registry for OrbiBot Agent.

Manages all available tools and their schemas for LLM function calling.
"""

import logging
import math
import time
import threading
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

        self.register_tool(
            name='set_motor_enable',
            description='Enable or disable robot motors via /orbibot/set_motor_enable. '
                       'Use enable=true to turn motors on (required for movement). '
                       'Use enable=false for emergency stop / motor off. '
                       'If motors fail to enable, check for emergency stop or low battery.',
            parameters={
                'type': 'object',
                'properties': {
                    'enable': {
                        'type': 'boolean',
                        'description': 'True to enable motors, False to disable (emergency stop)'
                    }
                },
                'required': ['enable']
            },
            handler=self._handle_set_motor_enable
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
            name='run_pid_test',
            description=(
                'Run a PID response test: send target velocities (vx, vy, wz) for a duration, '
                'record actual velocities from /odom, return samples and metrics (MAE, max_error, '
                'overshoot_pct) per axis. Use to tune motor and yaw PID from graph-like data.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'vx': {
                        'type': 'number',
                        'description': 'Target forward/back velocity (m/s), e.g. 0.2'
                    },
                    'vy': {
                        'type': 'number',
                        'description': 'Target strafe velocity (m/s), e.g. 0'
                    },
                    'wz': {
                        'type': 'number',
                        'description': 'Target angular velocity (rad/s), e.g. 0'
                    },
                    'duration': {
                        'type': 'number',
                        'description': 'Test duration in seconds (1–15), default 5'
                    },
                    'sample_hz': {
                        'type': 'number',
                        'description': 'Odom sampling rate (Hz), default 20'
                    }
                },
                'required': ['vx', 'vy', 'wz']
            },
            handler=self._handle_run_pid_test
        )

        self.register_tool(
            name='set_motor_pid',
            description=(
                'Set motor PID gains (Kp, Ki, Kd) for all wheels. Takes effect immediately. '
                'Use for PID tuning; typical range 0–10. Use save_motor_pid_to_flash to persist.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'kp': {'type': 'number', 'description': 'Proportional gain'},
                    'ki': {'type': 'number', 'description': 'Integral gain'},
                    'kd': {'type': 'number', 'description': 'Derivative gain'},
                },
                'required': ['kp', 'ki', 'kd']
            },
            handler=self._handle_set_motor_pid
        )

        self.register_tool(
            name='set_yaw_pid',
            description=(
                'Set yaw (heading) PID gains. Takes effect immediately. Use to reduce Wz drift when going straight.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'kp': {'type': 'number', 'description': 'Proportional gain'},
                    'ki': {'type': 'number', 'description': 'Integral gain'},
                    'kd': {'type': 'number', 'description': 'Derivative gain'},
                },
                'required': ['kp', 'ki', 'kd']
            },
            handler=self._handle_set_yaw_pid
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

        # ── GET tools ──────────────────────────────────────────────────────────
        self.register_tool(
            name='get_encoder_counts',
            description=(
                'Get raw encoder tick counts for all four wheels '
                '(front_left, back_left, front_right, back_right). '
                'Ticks accumulate since firmware startup or last reset. '
                'Use to verify encoder health, measure distance, or detect wheel slip.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_get_encoder_counts,
        )

        self.register_tool(
            name='get_imu_raw',
            description=(
                'Get raw IMU data from the ICM-20948 before Madgwick fusion: '
                'gyroscope (rad/s) and accelerometer (m/s²) on all three axes. '
                'Use to check sensor noise, bias, or calibration quality.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_get_imu_raw,
        )

        self.register_tool(
            name='get_magnetometer',
            description=(
                'Get magnetometer (compass) readings from the ICM-20948 AK09916 in µT. '
                'Returns x, y, z field strength and total magnitude. '
                'Use to assess magnetic environment or verify calibration.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_get_magnetometer,
        )

        self.register_tool(
            name='get_joint_states',
            description=(
                'Get wheel joint positions (radians) and velocities (rad/s) for all four wheels. '
                'Published at 50Hz by the hardware node for RViz visualization.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_get_joint_states,
        )

        self.register_tool(
            name='get_safety_status',
            description=(
                'Get safety system status: emergency stop, command timeout, low battery, '
                'hardware fault, velocity limit, temperature limit, and motors_disabled flags. '
                'Use to diagnose why the robot is not moving.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_get_safety_status,
        )

        self.register_tool(
            name='get_system_enriched',
            description=(
                'Get enriched system status including battery voltage, CPU%, RAM%, '
                'CPU temperature (°C), disk usage%, motor state, and hardware health. '
                'More complete than get_system_status; includes all hardware fields.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_get_system_enriched,
        )

        self.register_tool(
            name='get_firmware_version',
            description=(
                'Request the firmware version from the STM32 microcontroller via serial. '
                'Returns major, minor, and version_string (e.g., "2.0").'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_get_firmware_version,
        )

        self.register_tool(
            name='get_all_firmware_data',
            description=(
                'Get a comprehensive one-shot snapshot of ALL firmware-accessible values: '
                'battery, IMU attitude, raw IMU, magnetometer, encoders, joint states, '
                'odometry, safety status, firmware version, and system resources. '
                'Use when you need a full picture of robot state.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_get_all_firmware_data,
        )

        # ── SET / COMMAND tools ────────────────────────────────────────────────
        self.register_tool(
            name='save_motor_pid',
            description=(
                'Save motor PID gains (Kp, Ki, Kd) to firmware flash. '
                'These gains will persist across power cycles. '
                'Range [0, 10]. Use after tuning with set_motor_pid to make permanent.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'kp': {'type': 'number', 'description': 'Proportional gain [0–10]'},
                    'ki': {'type': 'number', 'description': 'Integral gain [0–10]'},
                    'kd': {'type': 'number', 'description': 'Derivative gain [0–10]'},
                },
                'required': ['kp', 'ki', 'kd'],
            },
            handler=self._handle_save_motor_pid,
        )

        self.register_tool(
            name='save_yaw_pid',
            description=(
                'Save yaw PID gains (Kp, Ki, Kd) to firmware flash. '
                'These gains will persist across power cycles. '
                'Range [0, 10]. Use after tuning with set_yaw_pid to make permanent.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'kp': {'type': 'number', 'description': 'Proportional gain [0–10]'},
                    'ki': {'type': 'number', 'description': 'Integral gain [0–10]'},
                    'kd': {'type': 'number', 'description': 'Derivative gain [0–10]'},
                },
                'required': ['kp', 'ki', 'kd'],
            },
            handler=self._handle_save_yaw_pid,
        )

        self.register_tool(
            name='set_beep',
            description=(
                'Control the robot buzzer. '
                'duration_ms=0: off, '
                'duration_ms=1: continuous on, '
                'duration_ms>=10: beep for that many milliseconds then auto-off.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'duration_ms': {
                        'type': 'integer',
                        'description': '0=off, 1=continuous, >=10=N ms beep',
                    }
                },
                'required': ['duration_ms'],
            },
            handler=self._handle_set_beep,
        )

        self.register_tool(
            name='reset_odometry',
            description=(
                'Reset the firmware odometry (x, y, theta) to zero. '
                'Encoder counts are NOT affected. '
                'Use before starting a new navigation session.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_reset_odometry,
        )

        self.register_tool(
            name='reset_encoders',
            description=(
                'Reset raw encoder tick counts to zero on the MCU. '
                'Odometry position is NOT affected. '
                'Use before a distance-measurement test.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_reset_encoders,
        )

        self.register_tool(
            name='calibrate_imu',
            description=(
                'Trigger magnetometer hard-iron auto-calibration. '
                'The firmware applies the current magnetometer reading as the zero offset. '
                'Keep the robot stationary during calibration. '
                'calibration_time: seconds to wait (default 5).'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'calibration_time': {
                        'type': 'integer',
                        'description': 'Seconds to wait for stabilisation (default 5)',
                        'default': 5,
                    }
                },
            },
            handler=self._handle_calibrate_imu,
        )

        self.register_tool(
            name='set_mag_calibration',
            description=(
                'Set explicit magnetometer hard-iron calibration offsets in µT. '
                'Use when you have known offset values from a previous calibration run. '
                'The firmware saves these offsets to flash automatically.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'offset_x': {'type': 'number', 'description': 'X axis hard-iron offset in µT'},
                    'offset_y': {'type': 'number', 'description': 'Y axis hard-iron offset in µT'},
                    'offset_z': {'type': 'number', 'description': 'Z axis hard-iron offset in µT'},
                },
                'required': ['offset_x', 'offset_y', 'offset_z'],
            },
            handler=self._handle_set_mag_calibration,
        )

        self.register_tool(
            name='reset_firmware_state',
            description=(
                'Emergency firmware state reset: stops all motors, zeroes odometry, '
                'and resets the agent emergency stop flag. '
                'Call set_motor_enable(true) after this to resume movement.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_reset_firmware_state,
        )

        # ── TESTING tools ──────────────────────────────────────────────────────
        self.register_tool(
            name='run_motor_test',
            description=(
                'Test one or all motors by spinning at a given speed and measuring encoder response. '
                'motor_id: 1=FL, 2=BL, 3=FR, 4=BR, "all"=all four. '
                'Reports expected vs actual encoder ticks and error percentage.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'motor_id': {
                        'type': 'string',
                        'description': '1, 2, 3, 4, or "all"',
                        'default': 'all',
                    },
                    'speed_mps': {
                        'type': 'number',
                        'description': 'Test speed in m/s (default 0.2, max 0.5)',
                        'default': 0.2,
                    },
                    'duration_s': {
                        'type': 'number',
                        'description': 'Test duration in seconds (default 2, max 5)',
                        'default': 2.0,
                    },
                },
                'required': [],
            },
            handler=self._handle_run_motor_test,
        )

        self.register_tool(
            name='run_imu_test',
            description=(
                'Validate IMU health by sampling raw data for 2 seconds. '
                'Checks: gyro bias (<0.05 rad/s at rest), accel magnitude (should be ~9.8 m/s²), '
                'and data continuity. Returns mean/stddev per axis and pass/fail verdict.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_run_imu_test,
        )

        self.register_tool(
            name='run_encoder_test',
            description=(
                'Verify encoder accuracy by driving forward a set distance and comparing '
                'commanded vs encoder-measured distance. '
                'distance_cm: how far to drive (default 30 cm). '
                'Returns expected ticks, actual ticks, and error %.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'distance_cm': {
                        'type': 'number',
                        'description': 'Distance to drive in cm (default 30, max 100)',
                        'default': 30.0,
                    }
                },
            },
            handler=self._handle_run_encoder_test,
        )

        self.register_tool(
            name='run_mag_test',
            description=(
                'Test magnetometer by sampling data for 3 seconds and reporting '
                'min/max/range per axis plus estimated hard-iron bias. '
                'Robot should be stationary. Flags if field magnitude is outside 20–80 µT range.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_run_mag_test,
        )

        self.register_tool(
            name='run_battery_test',
            description=(
                'Monitor battery voltage stability over 5 seconds (10 samples). '
                'Reports mean, min, max voltage and flags if variance is high '
                '(>0.5V swing may indicate loose connector or failing cell).'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_run_battery_test,
        )

        self.register_tool(
            name='run_beep_test',
            description=(
                'Test the buzzer with a 3-beep confirmation pattern '
                '(200ms on, 200ms off). Returns success if hardware node responded.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_run_beep_test,
        )

        self.register_tool(
            name='run_full_hardware_test',
            description=(
                'Run the complete hardware test suite in sequence: '
                'firmware version → battery → IMU → magnetometer → encoders → motors → beep. '
                'Returns a structured pass/fail report for each subsystem. '
                'This may take 20–30 seconds. Motors must be enabled beforehand.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=self._handle_run_full_hardware_test,
        )

        # Phase 2: SLAM / Nav2 / Exploration tools
        self._register_phase2_tools()

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

    def _handle_set_motor_enable(self, enable: bool) -> Dict:
        """Handle set_motor_enable tool. Uses correct 'enable' field for the service."""
        return self._ros_bridge.call_service(
            '/orbibot/set_motor_enable',
            'orbibot_msgs/srv/SetMotorEnable',
            {'enable': enable},
            timeout=5.0
        )

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

    def _handle_run_pid_test(self, vx: float, vy: float, wz: float, **kwargs) -> Dict:
        """Handle run_pid_test tool."""
        duration = kwargs.get('duration', 5.0)
        sample_hz = kwargs.get('sample_hz', 20.0)
        return self._ros_bridge.run_pid_test(
            vx=vx, vy=vy, wz=wz, duration=duration, sample_hz=sample_hz
        )

    def _handle_set_motor_pid(self, kp: float, ki: float, kd: float) -> Dict:
        """Handle set_motor_pid tool."""
        self._ros_bridge.set_motor_pid(kp, ki, kd)
        return {'status': 'ok', 'motor_pid': {'kp': kp, 'ki': ki, 'kd': kd}}

    def _handle_set_yaw_pid(self, kp: float, ki: float, kd: float) -> Dict:
        """Handle set_yaw_pid tool."""
        self._ros_bridge.set_yaw_pid(kp, ki, kd)
        return {'status': 'ok', 'yaw_pid': {'kp': kp, 'ki': ki, 'kd': kd}}

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

    # ── GET tool handlers ──────────────────────────────────────────────────────

    def _handle_get_encoder_counts(self) -> Dict:
        result = self._ros_bridge.get_encoder_counts()
        return result or {'error': 'Encoder data unavailable'}

    def _handle_get_imu_raw(self) -> Dict:
        result = self._ros_bridge.get_imu_raw()
        return result or {'error': 'Raw IMU data unavailable'}

    def _handle_get_magnetometer(self) -> Dict:
        result = self._ros_bridge.get_magnetometer()
        return result or {'error': 'Magnetometer data unavailable'}

    def _handle_get_joint_states(self) -> Dict:
        result = self._ros_bridge.get_joint_states()
        return result or {'error': 'Joint state data unavailable'}

    def _handle_get_safety_status(self) -> Dict:
        result = self._ros_bridge.get_safety_status()
        return result or {'error': 'Safety status unavailable'}

    def _handle_get_system_enriched(self) -> Dict:
        result = self._ros_bridge.get_system_enriched()
        return result or {'error': 'Enriched system status unavailable'}

    def _handle_get_firmware_version(self) -> Dict:
        result = self._ros_bridge.get_firmware_version()
        return result or {'error': 'Firmware version unavailable'}

    def _handle_get_all_firmware_data(self) -> Dict:
        return self._ros_bridge.get_all_firmware_data()

    # ── SET / COMMAND tool handlers ────────────────────────────────────────────

    def _handle_save_motor_pid(self, kp: float, ki: float, kd: float) -> Dict:
        return self._ros_bridge.save_motor_pid(kp, ki, kd)

    def _handle_save_yaw_pid(self, kp: float, ki: float, kd: float) -> Dict:
        return self._ros_bridge.save_yaw_pid(kp, ki, kd)

    def _handle_set_beep(self, duration_ms: int) -> Dict:
        return self._ros_bridge.set_beep(duration_ms)

    def _handle_reset_odometry(self) -> Dict:
        return self._ros_bridge.reset_odometry()

    def _handle_reset_encoders(self) -> Dict:
        return self._ros_bridge.reset_encoders()

    def _handle_calibrate_imu(self, calibration_time: int = 5) -> Dict:
        return self._ros_bridge.calibrate_imu(calibration_time)

    def _handle_set_mag_calibration(
        self, offset_x: float, offset_y: float, offset_z: float
    ) -> Dict:
        return self._ros_bridge.set_mag_calibration(offset_x, offset_y, offset_z)

    def _handle_reset_firmware_state(self) -> Dict:
        return self._ros_bridge.reset_firmware_state()

    # ── TESTING tool handlers ──────────────────────────────────────────────────

    def _handle_run_motor_test(
        self,
        motor_id: str = 'all',
        speed_mps: float = 0.2,
        duration_s: float = 2.0,
    ) -> Dict:
        """Drive one or all motors and compare encoder response."""
        speed_mps = max(0.05, min(0.5, float(speed_mps)))
        duration_s = max(0.5, min(5.0, float(duration_s)))

        # Wheel radius and encoder resolution from orbibot_config.h
        WHEEL_RADIUS_M = 0.050
        ENCODER_PPR = 1320
        ticks_per_meter = ENCODER_PPR / (2.0 * math.pi * WHEEL_RADIUS_M)
        expected_ticks = int(speed_mps * duration_s * ticks_per_meter)

        # Read encoder counts before test
        before = self._ros_bridge.get_encoder_counts()
        if before is None:
            return {'error': 'Cannot read encoder counts — is hardware_node running?'}

        # Drive using appropriate velocity combination for motor_id
        motor_id_str = str(motor_id).strip().lower()
        vx, vy = 0.0, 0.0
        if motor_id_str == 'all':
            vx = speed_mps
        elif motor_id_str in ('1', '3'):  # FL, FR → forward
            vx = speed_mps
        elif motor_id_str in ('2', '4'):  # BL, BR → forward
            vx = speed_mps
        else:
            return {'error': f'Invalid motor_id: {motor_id}. Use 1, 2, 3, 4, or "all"'}

        self._ros_bridge.move_for_duration(vx, vy, 0.0, duration_s)

        # Read encoder counts after test
        after = self._ros_bridge.get_encoder_counts()
        if after is None:
            return {'error': 'Cannot read encoder counts after test'}

        wheel_map = {
            'front_left': ('1', '3', 'all'),
            'back_left': ('2', '4', 'all'),
            'front_right': ('3', '1', 'all'),
            'back_right': ('4', '2', 'all'),
        }
        results = {}
        keys = ['front_left', 'back_left', 'front_right', 'back_right']
        for key in keys:
            delta = abs(after[key] - before[key])
            error_pct = abs(delta - expected_ticks) / max(expected_ticks, 1) * 100
            results[key] = {
                'delta_ticks': delta,
                'expected_ticks': expected_ticks,
                'error_pct': round(error_pct, 1),
                'pass': error_pct < 20.0,
            }

        all_pass = all(r['pass'] for r in results.values())
        return {
            'motor_id': motor_id_str,
            'speed_mps': speed_mps,
            'duration_s': duration_s,
            'expected_ticks_per_wheel': expected_ticks,
            'wheels': results,
            'overall_pass': all_pass,
            'verdict': 'PASS' if all_pass else 'FAIL — check motor wiring or PID gains',
        }

    def _handle_run_imu_test(self) -> Dict:
        """Sample raw IMU data for 2 seconds and validate health."""
        SAMPLE_COUNT = 20
        SAMPLE_INTERVAL = 0.1  # 10Hz sampling over 2s
        GYRO_BIAS_LIMIT_RAD_S = 0.05
        GRAVITY_M_S2 = 9.81
        GRAVITY_TOLERANCE = 0.5

        gyro_x, gyro_y, gyro_z = [], [], []
        accel_x, accel_y, accel_z = [], [], []

        for _ in range(SAMPLE_COUNT):
            sample = self._ros_bridge.get_imu_raw()
            if sample and 'gyro' in sample:
                gyro_x.append(sample['gyro']['x_rad_s'])
                gyro_y.append(sample['gyro']['y_rad_s'])
                gyro_z.append(sample['gyro']['z_rad_s'])
                accel_x.append(sample['accel']['x_m_s2'])
                accel_y.append(sample['accel']['y_m_s2'])
                accel_z.append(sample['accel']['z_m_s2'])
            time.sleep(SAMPLE_INTERVAL)

        if len(gyro_x) < 5:
            return {'error': 'Insufficient IMU samples — is hardware_node running?'}

        def stats(vals):
            mean = sum(vals) / len(vals)
            variance = sum((v - mean) ** 2 for v in vals) / len(vals)
            return round(mean, 5), round(math.sqrt(variance), 5)

        gx_mean, gx_std = stats(gyro_x)
        gy_mean, gy_std = stats(gyro_y)
        gz_mean, gz_std = stats(gyro_z)
        ax_mean, ax_std = stats(accel_x)
        ay_mean, ay_std = stats(accel_y)
        az_mean, az_std = stats(accel_z)

        accel_magnitude = math.sqrt(ax_mean ** 2 + ay_mean ** 2 + az_mean ** 2)
        gravity_ok = abs(accel_magnitude - GRAVITY_M_S2) < GRAVITY_TOLERANCE
        gyro_bias_ok = all(
            abs(b) < GYRO_BIAS_LIMIT_RAD_S for b in [gx_mean, gy_mean, gz_mean]
        )

        checks = {
            'gyro_bias_ok': gyro_bias_ok,
            'gravity_magnitude_ok': gravity_ok,
            'data_continuity': len(gyro_x) >= SAMPLE_COUNT * 0.8,
        }
        overall = all(checks.values())

        return {
            'samples_collected': len(gyro_x),
            'gyro': {
                'x': {'mean_rad_s': gx_mean, 'std': gx_std},
                'y': {'mean_rad_s': gy_mean, 'std': gy_std},
                'z': {'mean_rad_s': gz_mean, 'std': gz_std},
            },
            'accel': {
                'x': {'mean_m_s2': ax_mean, 'std': ax_std},
                'y': {'mean_m_s2': ay_mean, 'std': ay_std},
                'z': {'mean_m_s2': az_mean, 'std': az_std},
            },
            'accel_magnitude_m_s2': round(accel_magnitude, 4),
            'checks': checks,
            'overall_pass': overall,
            'verdict': 'PASS' if overall else 'FAIL — check IMU wiring or sensor calibration',
        }

    def _handle_run_encoder_test(self, distance_cm: float = 30.0) -> Dict:
        """Drive forward and compare commanded vs encoder-measured distance."""
        distance_cm = max(5.0, min(100.0, float(distance_cm)))
        distance_m = distance_cm / 100.0
        WHEEL_RADIUS_M = 0.050
        ENCODER_PPR = 1320
        SPEED_MPS = 0.15
        ticks_per_meter = ENCODER_PPR / (2.0 * math.pi * WHEEL_RADIUS_M)
        expected_ticks = int(distance_m * ticks_per_meter)
        duration_s = distance_m / SPEED_MPS

        before = self._ros_bridge.get_encoder_counts()
        if before is None:
            return {'error': 'Cannot read encoder counts — is hardware_node running?'}

        self._ros_bridge.reset_encoders()
        time.sleep(0.1)

        self._ros_bridge.move_for_duration(SPEED_MPS, 0.0, 0.0, duration_s)

        after = self._ros_bridge.get_encoder_counts()
        if after is None:
            return {'error': 'Cannot read encoder counts after movement'}

        keys = ['front_left', 'back_left', 'front_right', 'back_right']
        wheel_results = {}
        for key in keys:
            actual = abs(after[key])
            err_pct = abs(actual - expected_ticks) / max(expected_ticks, 1) * 100
            wheel_results[key] = {
                'actual_ticks': actual,
                'expected_ticks': expected_ticks,
                'measured_distance_cm': round(actual / ticks_per_meter * 100, 1),
                'error_pct': round(err_pct, 1),
                'pass': err_pct < 15.0,
            }

        all_pass = all(r['pass'] for r in wheel_results.values())
        return {
            'commanded_distance_cm': distance_cm,
            'speed_mps': SPEED_MPS,
            'wheels': wheel_results,
            'overall_pass': all_pass,
            'verdict': 'PASS' if all_pass
                else 'FAIL — check wheel radius config or encoder wiring',
        }

    def _handle_run_mag_test(self) -> Dict:
        """Sample magnetometer for 3 seconds and check field health."""
        SAMPLE_COUNT = 15
        SAMPLE_INTERVAL = 0.2
        MIN_FIELD_UT = 20.0
        MAX_FIELD_UT = 80.0

        x_vals, y_vals, z_vals = [], [], []
        for _ in range(SAMPLE_COUNT):
            sample = self._ros_bridge.get_magnetometer()
            if sample and 'x_uT' in sample:
                x_vals.append(sample['x_uT'])
                y_vals.append(sample['y_uT'])
                z_vals.append(sample['z_uT'])
            time.sleep(SAMPLE_INTERVAL)

        if len(x_vals) < 5:
            return {'error': 'Insufficient magnetometer samples — is hardware_node running?'}

        def field_stats(vals):
            return {
                'min': round(min(vals), 2),
                'max': round(max(vals), 2),
                'mean': round(sum(vals) / len(vals), 2),
                'range': round(max(vals) - min(vals), 2),
            }

        x_stats = field_stats(x_vals)
        y_stats = field_stats(y_vals)
        z_stats = field_stats(z_vals)

        magnitude = math.sqrt(
            x_stats['mean'] ** 2 + y_stats['mean'] ** 2 + z_stats['mean'] ** 2
        )
        field_ok = MIN_FIELD_UT <= magnitude <= MAX_FIELD_UT
        stability_ok = all(
            s['range'] < 10.0 for s in [x_stats, y_stats, z_stats]
        )

        return {
            'samples_collected': len(x_vals),
            'x_uT': x_stats,
            'y_uT': y_stats,
            'z_uT': z_stats,
            'magnitude_uT': round(magnitude, 2),
            'estimated_hard_iron_bias': {
                'x': x_stats['mean'],
                'y': y_stats['mean'],
                'z': z_stats['mean'],
            },
            'checks': {
                'field_magnitude_in_range': field_ok,
                'field_stability': stability_ok,
            },
            'overall_pass': field_ok and stability_ok,
            'verdict': (
                'PASS' if field_ok and stability_ok
                else 'FAIL — check for magnetic interference or run calibrate_imu'
            ),
        }

    def _handle_run_battery_test(self) -> Dict:
        """Monitor battery voltage over 5 seconds for stability."""
        SAMPLE_COUNT = 10
        SAMPLE_INTERVAL = 0.5
        VARIANCE_THRESHOLD = 0.5

        voltages = []
        for _ in range(SAMPLE_COUNT):
            battery = self._ros_bridge.get_battery_status()
            if battery and 'voltage' in battery:
                voltages.append(battery['voltage'])
            time.sleep(SAMPLE_INTERVAL)

        if len(voltages) < 3:
            return {'error': 'Insufficient battery samples — is hardware_node running?'}

        mean_v = sum(voltages) / len(voltages)
        swing = max(voltages) - min(voltages)
        stable = swing < VARIANCE_THRESHOLD

        if mean_v >= 14.6:
            status = 'full'
        elif mean_v >= 11.0:
            status = 'normal'
        elif mean_v >= 10.5:
            status = 'low'
        else:
            status = 'critical'

        return {
            'samples': len(voltages),
            'mean_voltage': round(mean_v, 3),
            'min_voltage': round(min(voltages), 3),
            'max_voltage': round(max(voltages), 3),
            'swing_v': round(swing, 3),
            'status': status,
            'checks': {
                'voltage_stable': stable,
                'battery_ok': status in ('full', 'normal'),
            },
            'overall_pass': stable and status in ('full', 'normal'),
            'verdict': (
                'PASS' if stable and status in ('full', 'normal')
                else f'FAIL — status={status}, swing={swing:.2f}V'
                     ' (check connections if swing > 0.5V)'
            ),
        }

    def _handle_run_beep_test(self) -> Dict:
        """Beep 3 times and confirm hardware node responded."""
        pattern = [200, 0, 200, 0, 200, 0]
        for duration_ms in pattern:
            result = self._ros_bridge.set_beep(duration_ms)
            if 'error' in result:
                return {'error': f'Beep command failed: {result["error"]}'}
            time.sleep(0.2)

        return {
            'status': 'ok',
            'pattern': '3× 200ms beeps',
            'verdict': 'PASS — buzzer command sent (verify audible beep on robot)',
        }

    def _handle_run_full_hardware_test(self) -> Dict:
        """Run complete hardware test suite and return structured report."""
        report = {}
        start = time.monotonic()

        logger.info('Starting full hardware test suite...')

        # 1. Firmware version
        report['firmware_version'] = self._handle_get_firmware_version()

        # 2. Battery
        report['battery'] = self._handle_run_battery_test()

        # 3. IMU
        report['imu'] = self._handle_run_imu_test()

        # 4. Magnetometer
        report['magnetometer'] = self._handle_run_mag_test()

        # 5. Encoder counts (static check)
        enc = self._handle_get_encoder_counts()
        report['encoders_static'] = enc if enc else {'error': 'unavailable'}

        # 6. Motor + encoder dynamic test
        report['motor_encoder'] = self._handle_run_motor_test(
            motor_id='all', speed_mps=0.15, duration_s=2.0
        )

        # 7. Beep confirmation
        report['beep'] = self._handle_run_beep_test()

        elapsed = round(time.monotonic() - start, 1)

        # Compute summary
        subsystems = ['battery', 'imu', 'magnetometer', 'motor_encoder', 'beep']
        passed = [
            s for s in subsystems
            if isinstance(report.get(s), dict) and report[s].get('overall_pass', False)
        ]
        failed = [s for s in subsystems if s not in passed]

        return {
            'elapsed_seconds': elapsed,
            'subsystems_tested': subsystems,
            'passed': passed,
            'failed': failed,
            'overall_pass': len(failed) == 0,
            'verdict': 'ALL PASS' if not failed else f'FAILED: {", ".join(failed)}',
            'details': report,
        }

    # =========================================================================
    # Phase 2 — Registration helpers (called from _register_default_tools)
    # =========================================================================

    def _register_phase2_tools(self) -> None:
        """Register Phase 2 SLAM / Nav2 / Exploration tools."""
        self._register_slam_tools()
        self._register_nav_tools()
        self._register_exploration_tools()
        self._register_generic_publish_tool()

    def _register_slam_tools(self) -> None:
        # ---- slam_save_map ------------------------------------------------
        self.register_tool(
            name='slam_save_map',
            description=(
                'Save the current SLAM map to disk. '
                'Writes both the slam_toolbox pose graph (<path>.posegraph / .data) '
                'and triggers map_saver to generate <path>.pgm + <path>.yaml for Nav2. '
                'Call this when you want to persist the map for later navigation.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': (
                            'Absolute file path without extension, '
                            'e.g. "/home/orbibot/maps/my_map"'
                        ),
                    }
                },
                'required': ['path'],
            },
            handler=lambda path: self._ros_bridge.slam_save_map(path),
        )

        # ---- slam_serialize_map -------------------------------------------
        self.register_tool(
            name='slam_serialize_map',
            description=(
                'Serialize the SLAM pose graph only (for localization-mode reload). '
                'Use this instead of slam_save_map when you want a smaller checkpoint '
                'to resume localization later without generating a pgm image.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'path': {
                        'type': 'string',
                        'description': 'Absolute file path without extension.',
                    }
                },
                'required': ['path'],
            },
            handler=lambda path: self._ros_bridge.slam_serialize_map(path),
        )

        # ---- slam_get_map_info --------------------------------------------
        self.register_tool(
            name='slam_get_map_info',
            description=(
                'Get current map dimensions, resolution, origin, and exploration coverage. '
                'Returns width_m, height_m, resolution_m, origin {x,y}, total_cells, '
                'free_cells, occupied_cells, unknown_cells, and explored_pct. '
                'Works during active SLAM mapping or after loading a saved map.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: self._ros_bridge.slam_get_map_info(),
        )

    def _register_nav_tools(self) -> None:
        # ---- set_initial_pose ---------------------------------------------
        self.register_tool(
            name='set_initial_pose',
            description=(
                'Set the AMCL initial pose estimate so the robot knows where it is '
                'on the map. Publishes a PoseWithCovarianceStamped to /initialpose. '
                'Use this when you know roughly where the robot is (e.g. after '
                'placing it on the map manually). After calling, drive a bit to '
                'help the particle filter converge.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'x': {'type': 'number', 'description': 'X position in map frame (metres).'},
                    'y': {'type': 'number', 'description': 'Y position in map frame (metres).'},
                    'yaw_deg': {
                        'type': 'number',
                        'description': 'Heading in degrees (0 = facing +X / East). Default 0.',
                    },
                    'frame_id': {
                        'type': 'string',
                        'description': 'Coordinate frame (default "map").',
                    },
                },
                'required': ['x', 'y'],
            },
            handler=lambda x, y, yaw_deg=0.0, frame_id='map': (
                self._ros_bridge.set_initial_pose(x, y, yaw_deg, frame_id)
            ),
        )

        # ---- navigate_to_pose --------------------------------------------
        self.register_tool(
            name='navigate_to_pose',
            description=(
                'Send the robot to a target position using Nav2 NavigateToPose action. '
                'Returns immediately with a goal_id. Use ros2_action_request_result '
                'to poll for completion. Nav2 must be running with a loaded map.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'x': {'type': 'number', 'description': 'Target X in map frame (metres).'},
                    'y': {'type': 'number', 'description': 'Target Y in map frame (metres).'},
                    'yaw_deg': {
                        'type': 'number',
                        'description': 'Target heading in degrees (default 0).',
                    },
                    'frame_id': {
                        'type': 'string',
                        'description': 'Coordinate frame (default "map").',
                    },
                    'timeout': {
                        'type': 'number',
                        'description': 'Seconds to wait for goal acceptance (default 120).',
                    },
                },
                'required': ['x', 'y'],
            },
            handler=lambda x, y, yaw_deg=0.0, frame_id='map', timeout=120.0: (
                self._ros_bridge.navigate_to_pose(x, y, yaw_deg, frame_id, timeout)
            ),
        )

        # ---- navigate_through_poses ----------------------------------------
        self.register_tool(
            name='navigate_through_poses',
            description=(
                'Send the robot through an ordered list of poses using Nav2 '
                'NavigateThroughPoses action. The robot visits each pose in sequence. '
                'Useful for sweeping paths or ordered multi-point missions.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'poses': {
                        'type': 'array',
                        'description': (
                            'List of pose dicts: [{x, y, yaw_deg (optional)}, ...]'
                        ),
                        'items': {
                            'type': 'object',
                            'properties': {
                                'x': {'type': 'number'},
                                'y': {'type': 'number'},
                                'yaw_deg': {'type': 'number'},
                            },
                            'required': ['x', 'y'],
                        },
                    },
                    'frame_id': {
                        'type': 'string',
                        'description': 'Coordinate frame (default "map").',
                    },
                    'timeout': {
                        'type': 'number',
                        'description': 'Seconds to wait for goal acceptance (default 300).',
                    },
                },
                'required': ['poses'],
            },
            handler=lambda poses, frame_id='map', timeout=300.0: (
                self._ros_bridge.navigate_through_poses(poses, frame_id, timeout)
            ),
        )

        # ---- follow_waypoints --------------------------------------------
        self.register_tool(
            name='follow_waypoints',
            description=(
                'Command the robot to follow a patrol route through an ordered list '
                'of waypoints using Nav2 FollowWaypoints action. If one waypoint '
                'is unreachable the behaviour tree tries the next one.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'waypoints': {
                        'type': 'array',
                        'description': (
                            'List of waypoint dicts: [{x, y, yaw_deg (optional)}, ...]'
                        ),
                        'items': {
                            'type': 'object',
                            'properties': {
                                'x': {'type': 'number'},
                                'y': {'type': 'number'},
                                'yaw_deg': {'type': 'number'},
                            },
                            'required': ['x', 'y'],
                        },
                    },
                    'frame_id': {
                        'type': 'string',
                        'description': 'Coordinate frame (default "map").',
                    },
                    'timeout': {
                        'type': 'number',
                        'description': 'Seconds to wait for goal acceptance (default 300).',
                    },
                },
                'required': ['waypoints'],
            },
            handler=lambda waypoints, frame_id='map', timeout=300.0: (
                self._ros_bridge.follow_waypoints(waypoints, frame_id, timeout)
            ),
        )

        # ---- nav_cancel -------------------------------------------------
        self.register_tool(
            name='nav_cancel',
            description='Cancel all active Nav2 navigation goals immediately.',
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: self._ros_bridge.nav_cancel(),
        )

        # ---- nav_clear_costmaps -----------------------------------------
        self.register_tool(
            name='nav_clear_costmaps',
            description=(
                'Clear Nav2 local, global, or both costmaps. '
                'Use this to force Nav2 to re-evaluate obstacles after the '
                'environment changes (e.g. a person moved). '
                'Then retry navigation.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'which': {
                        'type': 'string',
                        'enum': ['local', 'global', 'both'],
                        'description': 'Which costmap(s) to clear (default "both").',
                    }
                },
            },
            handler=lambda which='both': self._ros_bridge.nav_clear_costmaps(which),
        )

        # ---- nav_spin ---------------------------------------------------
        self.register_tool(
            name='nav_spin',
            description=(
                'Perform an in-place rotation recovery using Nav2 Spin action. '
                'Rotates by angle_rad radians (positive = counter-clockwise). '
                'Useful for getting unstuck or scanning surroundings.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'angle_rad': {
                        'type': 'number',
                        'description': (
                            'Target rotation in radians. Positive = CCW. '
                            'Use 3.14159 for half-turn, 6.28318 for full turn.'
                        ),
                    },
                    'time_allowance_sec': {
                        'type': 'number',
                        'description': 'Time budget for the spin in seconds (default 10).',
                    },
                },
                'required': ['angle_rad'],
            },
            handler=lambda angle_rad, time_allowance_sec=10.0: (
                self._ros_bridge.nav_spin(angle_rad, time_allowance_sec)
            ),
        )

        # ---- nav_backup -------------------------------------------------
        self.register_tool(
            name='nav_backup',
            description=(
                'Drive backward a short distance using Nav2 BackUp recovery action. '
                'Useful for getting unstuck when the robot is too close to an obstacle.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'distance_m': {
                        'type': 'number',
                        'description': 'Distance to reverse in metres (default 0.15).',
                    },
                    'speed_mps': {
                        'type': 'number',
                        'description': 'Backup speed in m/s (default 0.025).',
                    },
                    'time_allowance_sec': {
                        'type': 'number',
                        'description': 'Time budget in seconds (default 10).',
                    },
                },
            },
            handler=lambda distance_m=0.15, speed_mps=0.025, time_allowance_sec=10.0: (
                self._ros_bridge.nav_backup(distance_m, speed_mps, time_allowance_sec)
            ),
        )

        # ---- nav_get_plan -----------------------------------------------
        self.register_tool(
            name='nav_get_plan',
            description=(
                'Get the current Nav2 planned path from the /plan topic. '
                'Returns waypoint count, start and end coordinates, and frame. '
                'Only useful while a navigation goal is active.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: self._ros_bridge.nav_get_plan(),
        )

        # ---- amcl_reinitialize ------------------------------------------
        self.register_tool(
            name='amcl_reinitialize',
            description=(
                'Trigger global AMCL relocalization — scatters particles across '
                'the entire map so AMCL can find the robot when it is completely lost. '
                'After calling, drive the robot slowly to allow particles to converge. '
                'Use when set_initial_pose is not precise enough.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: self._ros_bridge.amcl_reinitialize(),
        )

    def _register_exploration_tools(self) -> None:
        # ---- exploration_start ------------------------------------------
        self.register_tool(
            name='exploration_start',
            description=(
                'Start autonomous frontier exploration. The robot will explore '
                'all reachable unknown areas, building the map as it goes. '
                'Requires orbibot_bringup with exploration=true and SLAM active.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: self._ros_bridge.exploration_command('start'),
        )

        # ---- exploration_stop -------------------------------------------
        self.register_tool(
            name='exploration_stop',
            description='Stop autonomous exploration completely.',
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: self._ros_bridge.exploration_command('stop'),
        )

        # ---- exploration_pause ------------------------------------------
        self.register_tool(
            name='exploration_pause',
            description=(
                'Pause autonomous exploration (robot stays in place). '
                'Resume with exploration_resume.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: self._ros_bridge.exploration_command('pause'),
        )

        # ---- exploration_resume -----------------------------------------
        self.register_tool(
            name='exploration_resume',
            description='Resume autonomous exploration after a pause.',
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: self._ros_bridge.exploration_command('resume'),
        )

        # ---- get_exploration_status ------------------------------------
        self.register_tool(
            name='get_exploration_status',
            description=(
                'Get the current autonomous exploration state. '
                'Possible values: idle, exploring, navigating, returning, '
                'complete, stopped.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: self._ros_bridge.get_exploration_status(),
        )

        # ---- get_exploration_frontiers ----------------------------------
        self.register_tool(
            name='get_exploration_frontiers',
            description=(
                'Get the list of unexplored frontier regions from the exploration node. '
                'Returns frontier count and centroid positions {x, y} in map frame. '
                'Useful for understanding how much of the map remains unexplored.'
            ),
            parameters={'type': 'object', 'properties': {}},
            handler=lambda: self._ros_bridge.get_exploration_frontiers(),
        )

    def _register_generic_publish_tool(self) -> None:
        # ---- ros2_topic_publish -----------------------------------------
        self.register_tool(
            name='ros2_topic_publish',
            description=(
                'Publish a one-shot message to any ROS 2 topic. '
                'Use this for interfaces not covered by dedicated tools. '
                'The publisher is cached so subsequent calls to the same topic are fast. '
                'Example: topic="/my_topic", msg_type="std_msgs/msg/String", '
                'data={"data": "hello"}.'
            ),
            parameters={
                'type': 'object',
                'properties': {
                    'topic': {
                        'type': 'string',
                        'description': 'Full ROS 2 topic name (e.g. "/orbibot/beep").',
                    },
                    'msg_type': {
                        'type': 'string',
                        'description': (
                            'Message type in package/msg/Type format '
                            '(e.g. "std_msgs/msg/String", "geometry_msgs/msg/Twist").'
                        ),
                    },
                    'data': {
                        'type': 'object',
                        'description': (
                            'Dict of message fields. '
                            'Nested messages use nested dicts. '
                            'Arrays use JSON arrays.'
                        ),
                    },
                },
                'required': ['topic', 'msg_type', 'data'],
            },
            handler=lambda topic, msg_type, data: (
                self._ros_bridge.publish_topic(topic, msg_type, data)
            ),
        )