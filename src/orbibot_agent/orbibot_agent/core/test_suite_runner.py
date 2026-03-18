"""Structured test suite runner for OrbiBot hardware validation.

Runs fixed, reproducible test sequences using the tool registry directly
(no LLM involved). Returns a JSON-serialisable report dict.

Usage:
    runner = TestSuiteRunner(tool_registry)
    report = runner.run_all()
    # report = {
    #   'battery_test': {'pass': True, 'voltage': 12.1, ...},
    #   'encoder_test': {'pass': True, 'delta': {...}, ...},
    #   ...
    # }
"""

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TestSuiteRunner:
    """Runs fixed hardware test sequences using the tool registry directly.

    Each test method returns a dict with at least:
      - 'pass': bool
      - 'details': dict (raw tool output)
      - Any test-specific fields (e.g. 'voltage', 'delta', ...)
    """

    def __init__(self, tool_registry):
        """Initialize with a ToolRegistry instance.

        Args:
            tool_registry: ToolRegistry instance from agent_node
        """
        self._tools = tool_registry

    def _call(self, tool_name: str, args: Dict = None) -> Dict[str, Any]:
        """Execute a tool and return its result dict.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments

        Returns:
            Tool result dict (never raises — returns error dict on failure)
        """
        try:
            result = self._tools.execute_tool(tool_name, args or {})
            if isinstance(result, dict):
                return result
            return {'result': result}
        except Exception as e:
            logger.error(f'TestSuiteRunner: tool {tool_name} failed: {e}')
            return {'error': str(e)}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_all(self) -> Dict[str, Any]:
        """Run all hardware tests and return a combined report.

        Returns:
            Dict mapping test name → test result dict
        """
        report = {}

        logger.info('TestSuiteRunner: starting full test suite')

        report['battery_test'] = self._run_battery_test()
        report['imu_test'] = self._run_imu_test()
        report['encoder_test'] = self._run_encoder_test()
        report['motor_test'] = self._run_motor_test()
        report['magnetometer_test'] = self._run_magnetometer_test()

        # Summary
        total = len(report)
        passed = sum(1 for v in report.values() if v.get('pass', False))
        report['_summary'] = {
            'total': total,
            'passed': passed,
            'failed': total - passed,
            'all_pass': passed == total,
        }

        logger.info(f'TestSuiteRunner: {passed}/{total} tests passed')
        return report

    def run_selected(self, tests: List[str]) -> Dict[str, Any]:
        """Run a selected subset of tests.

        Args:
            tests: List of test names, e.g. ['battery_test', 'imu_test']

        Returns:
            Dict mapping test name → test result dict
        """
        test_map = {
            'battery_test': self._run_battery_test,
            'imu_test': self._run_imu_test,
            'encoder_test': self._run_encoder_test,
            'motor_test': self._run_motor_test,
            'magnetometer_test': self._run_magnetometer_test,
        }
        report = {}
        for name in tests:
            if name in test_map:
                report[name] = test_map[name]()
            else:
                report[name] = {'pass': False, 'error': f'Unknown test: {name}'}
        return report

    # ------------------------------------------------------------------
    # Individual tests
    # ------------------------------------------------------------------

    def _run_battery_test(self) -> Dict[str, Any]:
        """Test battery voltage and percentage.

        PASS: voltage > 10.5 V (3S LiPo minimum safe)
        """
        result = self._call('get_battery_status')
        if 'error' in result:
            return {'pass': False, 'error': result['error'], 'details': result}

        voltage = float(result.get('voltage', 0))
        percentage = result.get('percentage', None)
        current = result.get('current', None)

        passed = voltage > 10.5

        return {
            'pass': passed,
            'voltage': voltage,
            'percentage': percentage,
            'current': current,
            'threshold': 10.5,
            'verdict': 'PASS' if passed else f'FAIL — voltage {voltage:.2f} V < 10.5 V minimum',
            'details': result,
        }

    def _run_imu_test(self) -> Dict[str, Any]:
        """Test IMU accelerometer and gyroscope data.

        PASS: no NaN values, accelerometer magnitude near 9.81 m/s²,
              gyroscope values near zero (robot stationary).
        """
        result = self._call('get_imu_data')
        if 'error' in result:
            return {'pass': False, 'error': result['error'], 'details': result}

        import math

        accel = result.get('linear_acceleration', {})
        gyro = result.get('angular_velocity', {})

        ax = float(accel.get('x', float('nan')))
        ay = float(accel.get('y', float('nan')))
        az = float(accel.get('z', float('nan')))
        gx = float(gyro.get('x', float('nan')))
        gy = float(gyro.get('y', float('nan')))
        gz = float(gyro.get('z', float('nan')))

        has_nan = any(math.isnan(v) for v in [ax, ay, az, gx, gy, gz])

        if has_nan:
            return {
                'pass': False,
                'verdict': 'FAIL — NaN values in IMU data (check SPI/I2C wiring)',
                'accel': {'x': ax, 'y': ay, 'z': az},
                'gyro': {'x': gx, 'y': gy, 'z': gz},
                'details': result,
            }

        accel_mag = math.sqrt(ax**2 + ay**2 + az**2)
        accel_ok = 8.0 < accel_mag < 11.5  # near 9.81 m/s²
        gyro_ok = all(abs(v) < 0.5 for v in [gx, gy, gz])  # near zero when stationary

        passed = accel_ok and gyro_ok

        return {
            'pass': passed,
            'accel_magnitude': round(accel_mag, 3),
            'accel': {'x': round(ax, 3), 'y': round(ay, 3), 'z': round(az, 3)},
            'gyro': {'x': round(gx, 4), 'y': round(gy, 4), 'z': round(gz, 4)},
            'accel_ok': accel_ok,
            'gyro_ok': gyro_ok,
            'verdict': 'PASS' if passed else (
                f'FAIL — accel_mag={accel_mag:.2f} (expected 8–11.5), '
                f'gyro_ok={gyro_ok}'
            ),
            'details': result,
        }

    def _run_encoder_test(self) -> Dict[str, Any]:
        """Test encoder counts by moving forward briefly and checking delta.

        PASS: all four wheels show encoder delta > 10 ticks (robot actually moved).
        """
        before = self._call('get_encoder_counts')
        if 'error' in before:
            return {'pass': False, 'error': before['error'], 'details': before}

        # Move forward 0.2 m/s for 1 second
        move_result = self._call('move_robot', {
            'linear_x': 0.2,
            'linear_y': 0.0,
            'angular_z': 0.0,
            'duration': 1.0,
        })

        time.sleep(0.5)  # wait for motion to settle

        after = self._call('get_encoder_counts')
        if 'error' in after:
            return {'pass': False, 'error': after['error'], 'details': after}

        # Compute delta for each wheel
        wheel_keys = ['fl', 'fr', 'rl', 'rr']
        delta = {}
        for key in wheel_keys:
            b = before.get(key, before.get(f'{key}_encoder', 0))
            a = after.get(key, after.get(f'{key}_encoder', 0))
            delta[key] = abs(int(a) - int(b))

        # All wheels must have moved
        min_delta = 10
        all_moved = all(v >= min_delta for v in delta.values())
        failed_wheels = [k for k, v in delta.items() if v < min_delta]

        return {
            'pass': all_moved,
            'delta': delta,
            'min_expected': min_delta,
            'failed_wheels': failed_wheels,
            'verdict': 'PASS' if all_moved else (
                f'FAIL — wheels with insufficient delta: {failed_wheels}'
            ),
            'details': {'before': before, 'after': after, 'move': move_result},
        }

    def _run_motor_test(self) -> Dict[str, Any]:
        """Test motors by running the built-in motor test tool."""
        result = self._call('run_motor_test')
        if 'error' in result:
            return {'pass': False, 'error': result['error'], 'details': result}

        passed = result.get('success', result.get('pass', False))
        return {
            'pass': bool(passed),
            'verdict': 'PASS' if passed else 'FAIL — motor test reported failure',
            'details': result,
        }

    def _run_magnetometer_test(self) -> Dict[str, Any]:
        """Test magnetometer by checking heading data.

        PASS: heading is a valid float in [-180, 360] degrees, no NaN.
        """
        result = self._call('get_magnetometer_data')
        if 'error' in result:
            return {'pass': False, 'error': result['error'], 'details': result}

        import math

        heading = result.get('heading', result.get('yaw', float('nan')))
        try:
            heading = float(heading)
        except (TypeError, ValueError):
            heading = float('nan')

        has_nan = math.isnan(heading)
        in_range = not has_nan and -180.0 <= heading <= 360.0

        passed = not has_nan and in_range

        return {
            'pass': passed,
            'heading': None if has_nan else round(heading, 2),
            'verdict': 'PASS' if passed else (
                'FAIL — NaN heading (check magnetometer wiring/calibration)'
                if has_nan else f'FAIL — heading {heading} out of range'
            ),
            'details': result,
        }
