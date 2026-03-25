"""Motion tool definitions — move, stop, motor enable, firmware reset."""

from typing import Any, Dict


def register(registry, ros_bridge, safety_manager) -> None:
    """Register motion tools on the given registry."""

    def _handle_move_robot(vx: float, vy: float, wz: float, duration: float) -> Dict:
        return ros_bridge.move_for_duration(vx, vy, wz, duration)

    def _handle_stop_robot() -> Dict:
        ros_bridge.publish_stop()
        return {'status': 'stopped'}

    def _handle_set_motor_enable(enable: bool) -> Dict:
        return ros_bridge.call_service(
            '/orbibot/set_motor_enable', 'orbibot_msgs/srv/SetMotorEnable',
            {'enable': enable}, timeout=5.0)

    def _handle_reset_firmware_state() -> Dict:
        return ros_bridge.reset_firmware_state()

    registry.register_tool(
        name='move_robot',
        description='Move the robot with specified velocities for a duration. '
                    'Use positive vx for forward, negative for backward. '
                    'Use positive vy for left, negative for right (mecanum). '
                    'Use positive wz for counter-clockwise rotation.',
        parameters={
            'type': 'object',
            'properties': {
                'vx': {'type': 'number', 'description': 'Forward/backward velocity in m/s (-0.5 to 0.5)'},
                'vy': {'type': 'number', 'description': 'Left/right velocity in m/s (-0.5 to 0.5, mecanum)'},
                'wz': {'type': 'number', 'description': 'Angular velocity in rad/s (-2.0 to 2.0)'},
                'duration': {'type': 'number', 'description': 'Duration in seconds (0.1 to 10.0)'},
            },
            'required': ['vx', 'vy', 'wz', 'duration'],
        },
        handler=_handle_move_robot,
    )

    registry.register_tool(
        name='stop_robot',
        description='Immediately stop all robot motion (emergency stop).',
        parameters={'type': 'object', 'properties': {}},
        handler=_handle_stop_robot,
    )

    registry.register_tool(
        name='set_motor_enable',
        description='Enable or disable robot motors. enable=true to turn on, false for emergency stop.',
        parameters={
            'type': 'object',
            'properties': {
                'enable': {'type': 'boolean', 'description': 'True to enable motors, False to disable'},
            },
            'required': ['enable'],
        },
        handler=_handle_set_motor_enable,
    )

    registry.register_tool(
        name='reset_firmware_state',
        description='Emergency: stop motors, clear odometry, reset agent e-stop. '
                    'Call set_motor_enable(true) after to resume.',
        parameters={'type': 'object', 'properties': {}},
        handler=_handle_reset_firmware_state,
    )
