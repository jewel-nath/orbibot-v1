"""Diagnostics tool definitions — health check, time-series recording, ROS diagnostics."""

import logging
import threading
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Key topics to inspect in get_ros_diagnostics
_KEY_TOPICS = [
    '/odom',
    '/imu/data',
    '/imu/data_raw',
    '/scan',
    '/odometry/filtered',
    '/orbibot/system_status',
    '/orbibot/encoders',
]

# Expected TF chain links
_TF_CHAIN = [
    ('odom', 'base_footprint'),
    ('base_footprint', 'base_link'),
]


def register(registry, ros_bridge, safety_manager) -> None:
    """Register diagnostics tools on the given registry."""

    # -- run_health_check --

    def _handle_run_health_check(tests: Optional[List[str]] = None) -> Dict:
        """Wrap TestSuiteRunner for LLM-free deterministic hardware health check."""
        from ..core.test_suite_runner import TestSuiteRunner
        runner = TestSuiteRunner(registry)
        try:
            if tests:
                return runner.run_selected(tests)
            return runner.run_all()
        except Exception as e:
            return {'error': f'Health check failed: {e}'}

    registry.register_tool(
        name='run_health_check',
        description=(
            'Run deterministic hardware health check (no LLM involved). '
            'Checks battery, IMU, encoders, motors, and magnetometer. '
            'Returns PASS/FAIL per subsystem with a summary. '
            'Use tests parameter to run a subset, e.g. ["battery_test", "imu_test"].'
        ),
        parameters={
            'type': 'object',
            'properties': {
                'tests': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': (
                        'Optional list of tests to run. '
                        'Available: battery_test, imu_test, encoder_test, motor_test, magnetometer_test. '
                        'Omit to run all.'
                    ),
                },
            },
        },
        handler=_handle_run_health_check,
    )

    # -- record_timeseries --

    def _handle_record_timeseries(
        sources: List[str],
        duration_sec: float = 5.0,
        sample_hz: float = 20.0,
        cmd_vel: Optional[Dict[str, float]] = None,
    ) -> Dict:
        """Record sensor data over time, optionally publishing cmd_vel throughout.

        Generalizes the PID test to any combination of sensor sources.
        """
        VALID_SOURCES = {'odom', 'imu_raw', 'encoders', 'joint_states'}
        unknown = [s for s in sources if s not in VALID_SOURCES]
        if unknown:
            return {'error': f'Unknown sources: {unknown}. Valid: {sorted(VALID_SOURCES)}'}

        duration_sec = max(1.0, min(30.0, float(duration_sec)))
        sample_hz = max(5.0, min(50.0, float(sample_hz)))
        dt = 1.0 / sample_hz

        # Validate cmd_vel if provided
        vx, vy, wz = 0.0, 0.0, 0.0
        if cmd_vel:
            vx = float(cmd_vel.get('vx', 0.0))
            vy = float(cmd_vel.get('vy', 0.0))
            wz = float(cmd_vel.get('wz', 0.0))
            if safety_manager:
                vx, vy, wz = safety_manager.validate_velocity(vx, vy, wz)

        samples: List[Dict[str, Any]] = []
        stop_event = threading.Event()
        t0 = time.perf_counter()
        end_time = t0 + duration_sec

        try:
            while time.perf_counter() < end_time:
                if safety_manager and safety_manager.check_emergency_stop():
                    break

                if cmd_vel:
                    ros_bridge.publish_cmd_vel(vx, vy, wz)

                t = round(time.perf_counter() - t0, 3)
                sample: Dict[str, Any] = {'t': t}

                if 'odom' in sources:
                    odom = ros_bridge.get_odometry()
                    if odom:
                        sample['odom'] = {
                            'vx': odom.get('vx_m_s', 0.0),
                            'vy': odom.get('vy_m_s', 0.0),
                            'wz': odom.get('wz_rad_s', 0.0),
                        }

                if 'imu_raw' in sources:
                    imu = ros_bridge.get_imu_raw()
                    if imu:
                        sample['imu_raw'] = {
                            'gyro_x': imu.get('gyro', {}).get('x_rad_s', 0.0),
                            'gyro_y': imu.get('gyro', {}).get('y_rad_s', 0.0),
                            'gyro_z': imu.get('gyro', {}).get('z_rad_s', 0.0),
                        }

                if 'encoders' in sources:
                    enc = ros_bridge.get_encoder_counts()
                    if enc:
                        sample['encoders'] = enc

                if 'joint_states' in sources:
                    js = ros_bridge.get_joint_states()
                    if js:
                        sample['joint_states'] = js

                samples.append(sample)
                stop_event.wait(timeout=dt)

        finally:
            if cmd_vel:
                ros_bridge.publish_stop()

        # Downsample if too many points
        if len(samples) > 200:
            step = len(samples) / 200
            samples = [samples[int(i * step)] for i in range(200)]

        result: Dict[str, Any] = {
            'duration_sec': round(duration_sec, 1),
            'sample_count': len(samples),
            'sources': sources,
            'samples': samples,
        }

        # Compute velocity tracking metrics if cmd_vel was provided and odom recorded
        if cmd_vel and 'odom' in sources and samples:
            def _metrics(vals: List[float], target: float) -> Dict[str, float]:
                if not vals or abs(target) < 1e-9:
                    return {}
                errs = [abs(v - target) for v in vals]
                mae = sum(errs) / len(errs)
                max_err = max(errs)
                overshoot = 0.0
                if target > 0:
                    overshoot = max(0.0, (max(vals) - target) / target * 100.0)
                elif target < 0:
                    overshoot = max(0.0, (target - min(vals)) / abs(target) * 100.0)
                return {
                    'mae': round(mae, 4),
                    'max_error': round(max_err, 4),
                    'overshoot_pct': round(overshoot, 1),
                }

            vx_vals = [s['odom']['vx'] for s in samples if 'odom' in s]
            vy_vals = [s['odom']['vy'] for s in samples if 'odom' in s]
            wz_vals = [s['odom']['wz'] for s in samples if 'odom' in s]
            result['target_cmd_vel'] = {'vx': vx, 'vy': vy, 'wz': wz}
            result['tracking_metrics'] = {
                'vx': _metrics(vx_vals, vx),
                'vy': _metrics(vy_vals, vy),
                'wz': _metrics(wz_vals, wz),
            }

        return result

    registry.register_tool(
        name='record_timeseries',
        description=(
            'Record robot sensor data over time as a time series. '
            'Optionally publishes a constant cmd_vel during recording (useful for PID tuning and response analysis). '
            'Sources: "odom" (velocity from /odom), "imu_raw" (gyro), "encoders" (tick counts), "joint_states". '
            'If cmd_vel is provided, also computes velocity tracking metrics (MAE, overshoot).'
        ),
        parameters={
            'type': 'object',
            'properties': {
                'sources': {
                    'type': 'array',
                    'items': {'type': 'string', 'enum': ['odom', 'imu_raw', 'encoders', 'joint_states']},
                    'description': 'Sensor sources to record.',
                },
                'duration_sec': {
                    'type': 'number',
                    'description': 'Recording duration in seconds (1-30, default 5).',
                },
                'sample_hz': {
                    'type': 'number',
                    'description': 'Sampling rate in Hz (5-50, default 20).',
                },
                'cmd_vel': {
                    'type': 'object',
                    'description': 'Optional constant velocity to publish during recording.',
                    'properties': {
                        'vx': {'type': 'number', 'description': 'Forward velocity m/s'},
                        'vy': {'type': 'number', 'description': 'Strafe velocity m/s'},
                        'wz': {'type': 'number', 'description': 'Angular velocity rad/s'},
                    },
                },
            },
            'required': ['sources'],
        },
        handler=_handle_record_timeseries,
    )

    # -- get_ros_diagnostics --

    def _handle_get_ros_diagnostics() -> Dict:
        """Introspect the ROS graph for debugging."""
        issues: List[str] = []
        result: Dict[str, Any] = {}

        # Active nodes
        try:
            nodes_result = ros_bridge.list_active_nodes()
            result['active_nodes'] = nodes_result.get('nodes', [])
        except Exception as e:
            result['active_nodes'] = []
            issues.append(f'Cannot list nodes: {e}')

        # Check key topics (try to receive one message with short timeout)
        topic_status: Dict[str, Dict] = {}
        for topic in _KEY_TOPICS:
            try:
                # Use list_topics to check existence
                topics_result = ros_bridge.list_topics()
                all_topics = topics_result.get('topics', [])
                exists = any(
                    (t if isinstance(t, str) else t.get('name', '')) == topic
                    for t in all_topics
                )
                topic_status[topic] = {'exists': exists}
                if not exists:
                    issues.append(f'Topic {topic} not found')
            except Exception as e:
                topic_status[topic] = {'exists': False, 'error': str(e)}
                issues.append(f'Cannot check topic {topic}: {e}')

        result['key_topics'] = topic_status

        # TF chain check — try to get robot position (uses /odom)
        tf_status: Dict[str, bool] = {}
        try:
            odom = ros_bridge.get_odometry()
            tf_status['odom_readable'] = odom is not None
            if odom is None:
                issues.append('Cannot read /odom — odom→base_footprint TF may be missing')
        except Exception as e:
            tf_status['odom_readable'] = False
            issues.append(f'Odometry check failed: {e}')

        result['tf_status'] = tf_status

        # Summary
        result['issues'] = issues
        result['healthy'] = len(issues) == 0

        return result

    registry.register_tool(
        name='get_ros_diagnostics',
        description=(
            'Introspect the ROS graph for debugging. '
            'Returns: active nodes, key topic status (/odom, /scan, /imu/data, etc.), '
            'TF chain health, and a list of detected issues. '
            'Use this when the robot is not behaving as expected or to verify the stack is running.'
        ),
        parameters={'type': 'object', 'properties': {}},
        handler=_handle_get_ros_diagnostics,
    )
