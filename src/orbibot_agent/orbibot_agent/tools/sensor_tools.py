"""Sensor tool definitions — battery, IMU, encoders, odometry, LiDAR, system status."""

from typing import Any, Dict


def register(registry, ros_bridge, safety_manager) -> None:
    """Register sensor/GET tools on the given registry."""

    def _get_or_error(fn, error_msg):
        """Call a RosBridge getter; return error dict if None."""
        result = fn()
        return result or {'error': error_msg}

    registry.register_tool(
        name='get_battery',
        description='Get battery voltage and status level.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_battery_status, 'Battery data unavailable'),
    )

    registry.register_tool(
        name='get_imu',
        description='Get IMU orientation (roll, pitch, yaw) and angular velocities.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_imu_data, 'IMU data unavailable'),
    )

    registry.register_tool(
        name='get_imu_raw',
        description='Get raw ICM-20948 gyro (rad/s) and accel (m/s²) before Madgwick fusion.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_imu_raw, 'Raw IMU data unavailable'),
    )

    registry.register_tool(
        name='get_magnetometer',
        description='Get magnetometer compass readings from ICM-20948 AK09916 in uT.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_magnetometer, 'Magnetometer data unavailable'),
    )

    registry.register_tool(
        name='get_encoder_counts',
        description='Get raw encoder tick counts [FL, BL, FR, BR]. Ticks accumulate since startup or last reset.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_encoder_counts, 'Encoder data unavailable'),
    )

    registry.register_tool(
        name='get_joint_states',
        description='Get wheel joint positions (rad) and velocities (rad/s) for all four wheels.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_joint_states, 'Joint state data unavailable'),
    )

    registry.register_tool(
        name='get_odometry',
        description='Get robot position, orientation, and velocity from odometry.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_odometry, 'Odometry data unavailable'),
    )

    def _handle_get_robot_position() -> Dict:
        odom = ros_bridge.get_odometry()
        if not odom:
            return {'error': 'Position data unavailable'}
        return {'x': odom['position']['x'], 'y': odom['position']['y'], 'yaw_deg': odom['yaw_deg']}

    registry.register_tool(
        name='get_robot_position',
        description='Get simplified robot position (x, y, yaw).',
        parameters={'type': 'object', 'properties': {}},
        handler=_handle_get_robot_position,
    )

    registry.register_tool(
        name='get_lidar_summary',
        description='Get LiDAR scan summary with obstacle detection.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_lidar_summary, 'LiDAR data unavailable'),
    )

    registry.register_tool(
        name='get_safety_status',
        description='Get safety system status: e-stop, faults, cmd_timeout, battery warnings.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_safety_status, 'Safety status unavailable'),
    )

    registry.register_tool(
        name='get_system_enriched',
        description='Get enriched system status: battery, CPU%, RAM%, temp, disk%, motor state.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_system_enriched, 'Enriched status unavailable'),
    )

    registry.register_tool(
        name='get_firmware_version',
        description='Get STM32 firmware version (major.minor).',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: _get_or_error(ros_bridge.get_firmware_version, 'Firmware version unavailable'),
    )

    registry.register_tool(
        name='get_all_firmware_data',
        description='One-shot snapshot of ALL firmware values: battery, IMU, encoders, odometry, etc.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.get_all_firmware_data(),
    )

    registry.register_tool(
        name='get_system_status',
        description='Get system status: CPU load, RAM, temperature, battery.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.get_system_status(),
    )
