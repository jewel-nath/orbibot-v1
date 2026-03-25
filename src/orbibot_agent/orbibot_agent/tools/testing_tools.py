"""Hardware testing tool definitions — PID test, motor, IMU, encoder, mag, battery, beep tests."""

import logging
import math
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def register(registry, ros_bridge, safety_manager) -> None:
    """Register hardware testing tools on the given registry."""

    # -- PID test --

    def _handle_run_pid_test(vx: float, vy: float, wz: float, **kwargs) -> Dict:
        duration = kwargs.get('duration', 5.0)
        sample_hz = kwargs.get('sample_hz', 20.0)
        return ros_bridge.run_pid_test(vx=vx, vy=vy, wz=wz, duration=duration, sample_hz=sample_hz)

    registry.register_tool(
        name='run_pid_test',
        description='Run PID response test: send velocities, record /odom response. Returns MAE and overshoot.',
        parameters={
            'type': 'object',
            'properties': {
                'vx': {'type': 'number', 'description': 'Target forward velocity (m/s)'},
                'vy': {'type': 'number', 'description': 'Target strafe velocity (m/s)'},
                'wz': {'type': 'number', 'description': 'Target angular velocity (rad/s)'},
                'duration': {'type': 'number', 'description': 'Test duration in seconds (1-15), default 5'},
                'sample_hz': {'type': 'number', 'description': 'Sampling rate (Hz), default 20'},
            },
            'required': ['vx', 'vy', 'wz'],
        },
        handler=_handle_run_pid_test,
    )

    # -- Motor test --

    def _handle_run_motor_test(motor_id: str = 'all', speed_mps: float = 0.2, duration_s: float = 2.0) -> Dict:
        speed_mps = max(0.05, min(0.5, float(speed_mps)))
        duration_s = max(0.5, min(5.0, float(duration_s)))

        WHEEL_RADIUS_M = 0.050
        ENCODER_PPR = 1320
        ticks_per_meter = ENCODER_PPR / (2.0 * math.pi * WHEEL_RADIUS_M)
        expected_ticks = int(speed_mps * duration_s * ticks_per_meter)

        before = ros_bridge.get_encoder_counts()
        if before is None:
            return {'error': 'Cannot read encoder counts — is hardware_node running?'}

        motor_id_str = str(motor_id).strip().lower()
        if motor_id_str not in ('all', '1', '2', '3', '4'):
            return {'error': f'Invalid motor_id: {motor_id}. Use 1, 2, 3, 4, or "all"'}

        ros_bridge.move_for_duration(speed_mps, 0.0, 0.0, duration_s)

        after = ros_bridge.get_encoder_counts()
        if after is None:
            return {'error': 'Cannot read encoder counts after test'}

        results = {}
        for key in ('front_left', 'back_left', 'front_right', 'back_right'):
            delta = abs(after[key] - before[key])
            error_pct = abs(delta - expected_ticks) / max(expected_ticks, 1) * 100
            results[key] = {
                'delta_ticks': delta, 'expected_ticks': expected_ticks,
                'error_pct': round(error_pct, 1), 'pass': error_pct < 20.0,
            }

        all_pass = all(r['pass'] for r in results.values())
        return {
            'motor_id': motor_id_str, 'speed_mps': speed_mps, 'duration_s': duration_s,
            'expected_ticks_per_wheel': expected_ticks, 'wheels': results,
            'overall_pass': all_pass,
            'verdict': 'PASS' if all_pass else 'FAIL — check motor wiring or PID gains',
        }

    registry.register_tool(
        name='run_motor_test',
        description='Spin motor(s) and compare encoder response vs expected ticks.',
        parameters={
            'type': 'object',
            'properties': {
                'motor_id': {'type': 'string', 'description': '1, 2, 3, 4, or "all"', 'default': 'all'},
                'speed_mps': {'type': 'number', 'description': 'Speed in m/s (default 0.2)', 'default': 0.2},
                'duration_s': {'type': 'number', 'description': 'Duration in seconds (default 2)', 'default': 2.0},
            },
            'required': [],
        },
        handler=_handle_run_motor_test,
    )

    # -- IMU test --

    def _handle_run_imu_test() -> Dict:
        SAMPLE_COUNT = 20
        SAMPLE_INTERVAL = 0.1
        gyro_x, gyro_y, gyro_z = [], [], []
        accel_x, accel_y, accel_z = [], [], []

        for _ in range(SAMPLE_COUNT):
            sample = ros_bridge.get_imu_raw()
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
        gravity_ok = abs(accel_magnitude - 9.81) < 0.5
        gyro_bias_ok = all(abs(b) < 0.05 for b in [gx_mean, gy_mean, gz_mean])

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

    registry.register_tool(
        name='run_imu_test',
        description='Validate IMU health by sampling raw data. Checks gyro bias and gravity magnitude.',
        parameters={'type': 'object', 'properties': {}},
        handler=_handle_run_imu_test,
    )

    # -- Encoder test --

    def _handle_run_encoder_test(distance_cm: float = 30.0) -> Dict:
        distance_cm = max(5.0, min(100.0, float(distance_cm)))
        distance_m = distance_cm / 100.0
        WHEEL_RADIUS_M = 0.050
        ENCODER_PPR = 1320
        SPEED_MPS = 0.15
        ticks_per_meter = ENCODER_PPR / (2.0 * math.pi * WHEEL_RADIUS_M)
        expected_ticks = int(distance_m * ticks_per_meter)
        duration_s = distance_m / SPEED_MPS

        before = ros_bridge.get_encoder_counts()
        if before is None:
            return {'error': 'Cannot read encoder counts'}

        ros_bridge.reset_encoders()
        time.sleep(0.1)
        ros_bridge.move_for_duration(SPEED_MPS, 0.0, 0.0, duration_s)

        after = ros_bridge.get_encoder_counts()
        if after is None:
            return {'error': 'Cannot read encoder counts after movement'}

        wheel_results = {}
        for key in ('front_left', 'back_left', 'front_right', 'back_right'):
            actual = abs(after[key])
            err_pct = abs(actual - expected_ticks) / max(expected_ticks, 1) * 100
            wheel_results[key] = {
                'actual_ticks': actual, 'expected_ticks': expected_ticks,
                'measured_distance_cm': round(actual / ticks_per_meter * 100, 1),
                'error_pct': round(err_pct, 1), 'pass': err_pct < 15.0,
            }

        all_pass = all(r['pass'] for r in wheel_results.values())
        return {
            'commanded_distance_cm': distance_cm, 'speed_mps': SPEED_MPS,
            'wheels': wheel_results, 'overall_pass': all_pass,
            'verdict': 'PASS' if all_pass else 'FAIL — check wheel radius config or encoder wiring',
        }

    registry.register_tool(
        name='run_encoder_test',
        description='Drive forward a set distance and compare commanded vs encoder-measured distance.',
        parameters={
            'type': 'object',
            'properties': {
                'distance_cm': {'type': 'number', 'description': 'Distance to drive in cm (default 30)', 'default': 30.0},
            },
        },
        handler=_handle_run_encoder_test,
    )

    # -- Magnetometer test --

    def _handle_run_mag_test() -> Dict:
        SAMPLE_COUNT = 15
        x_vals, y_vals, z_vals = [], [], []
        for _ in range(SAMPLE_COUNT):
            sample = ros_bridge.get_magnetometer()
            if sample and 'x_uT' in sample:
                x_vals.append(sample['x_uT'])
                y_vals.append(sample['y_uT'])
                z_vals.append(sample['z_uT'])
            time.sleep(0.2)

        if len(x_vals) < 5:
            return {'error': 'Insufficient magnetometer samples'}

        def field_stats(vals):
            return {
                'min': round(min(vals), 2), 'max': round(max(vals), 2),
                'mean': round(sum(vals) / len(vals), 2),
                'range': round(max(vals) - min(vals), 2),
            }

        x_s, y_s, z_s = field_stats(x_vals), field_stats(y_vals), field_stats(z_vals)
        magnitude = math.sqrt(x_s['mean'] ** 2 + y_s['mean'] ** 2 + z_s['mean'] ** 2)
        field_ok = 20.0 <= magnitude <= 80.0
        stability_ok = all(s['range'] < 10.0 for s in [x_s, y_s, z_s])

        return {
            'samples_collected': len(x_vals),
            'x_uT': x_s, 'y_uT': y_s, 'z_uT': z_s,
            'magnitude_uT': round(magnitude, 2),
            'estimated_hard_iron_bias': {'x': x_s['mean'], 'y': y_s['mean'], 'z': z_s['mean']},
            'checks': {'field_magnitude_in_range': field_ok, 'field_stability': stability_ok},
            'overall_pass': field_ok and stability_ok,
            'verdict': 'PASS' if field_ok and stability_ok else 'FAIL — check for magnetic interference',
        }

    registry.register_tool(
        name='run_mag_test',
        description='Test magnetometer by sampling 3 seconds. Checks field magnitude and stability.',
        parameters={'type': 'object', 'properties': {}},
        handler=_handle_run_mag_test,
    )

    # -- Battery test --

    def _handle_run_battery_test() -> Dict:
        voltages = []
        for _ in range(10):
            battery = ros_bridge.get_battery_status()
            if battery and 'voltage' in battery:
                voltages.append(battery['voltage'])
            time.sleep(0.5)

        if len(voltages) < 3:
            return {'error': 'Insufficient battery samples'}

        mean_v = sum(voltages) / len(voltages)
        swing = max(voltages) - min(voltages)
        stable = swing < 0.5

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
            'mean_voltage': round(mean_v, 3), 'min_voltage': round(min(voltages), 3),
            'max_voltage': round(max(voltages), 3), 'swing_v': round(swing, 3),
            'status': status,
            'checks': {'voltage_stable': stable, 'battery_ok': status in ('full', 'normal')},
            'overall_pass': stable and status in ('full', 'normal'),
            'verdict': ('PASS' if stable and status in ('full', 'normal')
                        else f'FAIL — status={status}, swing={swing:.2f}V'),
        }

    registry.register_tool(
        name='run_battery_test',
        description='Monitor battery voltage stability over 5 seconds (10 samples).',
        parameters={'type': 'object', 'properties': {}},
        handler=_handle_run_battery_test,
    )

    # -- Beep test --

    def _handle_run_beep_test() -> Dict:
        for duration_ms in [200, 0, 200, 0, 200, 0]:
            result = ros_bridge.set_beep(duration_ms)
            if 'error' in result:
                return {'error': f'Beep command failed: {result["error"]}'}
            time.sleep(0.2)
        return {'status': 'ok', 'pattern': '3x 200ms beeps',
                'verdict': 'PASS — buzzer command sent (verify audible beep on robot)'}

    registry.register_tool(
        name='run_beep_test',
        description='Test buzzer with a 3-beep confirmation pattern.',
        parameters={'type': 'object', 'properties': {}},
        handler=_handle_run_beep_test,
    )

    # -- Full hardware test --

    def _handle_run_full_hardware_test() -> Dict:
        report = {}
        start = time.monotonic()

        logger.info('Starting full hardware test suite...')

        report['firmware_version'] = ros_bridge.get_firmware_version() or {'error': 'unavailable'}
        report['battery'] = _handle_run_battery_test()
        report['imu'] = _handle_run_imu_test()
        report['magnetometer'] = _handle_run_mag_test()
        report['encoders_static'] = ros_bridge.get_encoder_counts() or {'error': 'unavailable'}
        report['motor_encoder'] = _handle_run_motor_test(motor_id='all', speed_mps=0.15, duration_s=2.0)
        report['beep'] = _handle_run_beep_test()

        elapsed = round(time.monotonic() - start, 1)
        subsystems = ['battery', 'imu', 'magnetometer', 'motor_encoder', 'beep']
        passed = [s for s in subsystems
                  if isinstance(report.get(s), dict) and report[s].get('overall_pass', False)]
        failed = [s for s in subsystems if s not in passed]

        return {
            'elapsed_seconds': elapsed, 'subsystems_tested': subsystems,
            'passed': passed, 'failed': failed,
            'overall_pass': len(failed) == 0,
            'verdict': 'ALL PASS' if not failed else f'FAILED: {", ".join(failed)}',
            'details': report,
        }

    registry.register_tool(
        name='run_full_hardware_test',
        description='Run complete hardware test suite (20-30 seconds). Motors must be enabled.',
        parameters={'type': 'object', 'properties': {}},
        handler=_handle_run_full_hardware_test,
    )
