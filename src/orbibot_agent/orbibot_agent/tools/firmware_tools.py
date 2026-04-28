"""Firmware command tool definitions — PID, beep, calibration, reset."""

from typing import Any, Dict


def register(registry, ros_bridge, safety_manager) -> None:
    """Register firmware SET/command tools on the given registry."""

    # -- PID --

    def _handle_set_motor_pid(kp: float, ki: float, kd: float) -> Dict:
        ros_bridge.set_motor_pid(kp, ki, kd)
        return {'status': 'ok', 'motor_pid': {'kp': kp, 'ki': ki, 'kd': kd}}

    def _handle_set_yaw_pid(kp: float, ki: float, kd: float) -> Dict:
        ros_bridge.set_yaw_pid(kp, ki, kd)
        return {'status': 'ok', 'yaw_pid': {'kp': kp, 'ki': ki, 'kd': kd}}

    pid_params = {
        'type': 'object',
        'properties': {
            'kp': {'type': 'number', 'description': 'Proportional gain'},
            'ki': {'type': 'number', 'description': 'Integral gain'},
            'kd': {'type': 'number', 'description': 'Derivative gain'},
        },
        'required': ['kp', 'ki', 'kd'],
    }

    pid_save_params = {
        'type': 'object',
        'properties': {
            'kp': {'type': 'number', 'description': 'Proportional gain [0-10]'},
            'ki': {'type': 'number', 'description': 'Integral gain [0-10]'},
            'kd': {'type': 'number', 'description': 'Derivative gain [0-10]'},
        },
        'required': ['kp', 'ki', 'kd'],
    }

    registry.register_tool(
        name='set_motor_pid',
        description='Set motor PID gains (Kp, Ki, Kd). Immediate, not persistent. Use save_motor_pid to persist.',
        parameters=pid_params,
        handler=_handle_set_motor_pid,
    )

    registry.register_tool(
        name='set_yaw_pid',
        description='Set yaw PID gains. Immediate, not persistent. Use save_yaw_pid to persist.',
        parameters=pid_params,
        handler=_handle_set_yaw_pid,
    )

    registry.register_tool(
        name='save_motor_pid',
        description='Save motor PID gains to firmware flash. Persists across power cycles.',
        parameters=pid_save_params,
        handler=lambda kp, ki, kd: ros_bridge.save_motor_pid(kp, ki, kd),
    )

    registry.register_tool(
        name='save_yaw_pid',
        description='Save yaw PID gains to firmware flash. Persists across power cycles.',
        parameters=pid_save_params,
        handler=lambda kp, ki, kd: ros_bridge.save_yaw_pid(kp, ki, kd),
    )

    # -- Buzzer --

    registry.register_tool(
        name='set_beep',
        description='Control buzzer: 0=off, 1=continuous, >=10=beep for N ms.',
        parameters={
            'type': 'object',
            'properties': {
                'duration_ms': {'type': 'integer', 'description': '0=off, 1=continuous, >=10=N ms beep'},
            },
            'required': ['duration_ms'],
        },
        handler=lambda duration_ms: ros_bridge.set_beep(duration_ms),
    )

    # -- Reset / calibration --

    registry.register_tool(
        name='reset_odometry',
        description='Reset firmware odometry to zero (encoder counts unchanged).',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.reset_odometry(),
    )

    registry.register_tool(
        name='reset_encoders',
        description='Reset encoder counts to zero on MCU (odometry unchanged).',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.reset_encoders(),
    )

