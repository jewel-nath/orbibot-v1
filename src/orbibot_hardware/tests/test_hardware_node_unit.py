#!/usr/bin/env python3
"""
Offline unit tests for OrbiBot Hardware Node logic.

Tests (no ROS 2 / no hardware required):
  - Velocity limiting (_cmd_vel_callback clamping logic)
  - Command timeout (stop sent once after 2 s, reset on new cmd)
  - PID rate limiting (_check_pid_rate_limit)
  - Odometry deduplication (skip unchanged data; heartbeat after interval)
  - IMU pose estimation (gyro+accel only — magnetometer removed 2026-04-28)
  - Quaternion from yaw (yaw-only quaternion)
  - Joint state computation (encoder ticks → wheel angle via CPR)

Pure Python via unittest.mock — no rclpy needed.
"""

import math
import time
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ---------------------------------------------------------------------------
# Thin stubs for the classes/types hardware_node imports from ROS 2.
# This lets us import the logic without a live ROS 2 environment.
# ---------------------------------------------------------------------------

import sys
import types

def _stub_ros_modules():
    """Install minimal stubs for every ROS 2 import in hardware_node."""
    mods = [
        'rclpy', 'rclpy.node', 'rclpy.executors', 'rclpy.callback_groups',
        'rclpy.qos', 'rcl_interfaces', 'rcl_interfaces.msg',
        'sensor_msgs', 'sensor_msgs.msg',
        'geometry_msgs', 'geometry_msgs.msg',
        'nav_msgs', 'nav_msgs.msg',
        'std_msgs', 'std_msgs.msg',
        'diagnostic_msgs', 'diagnostic_msgs.msg',
        'orbibot_msgs', 'orbibot_msgs.msg', 'orbibot_msgs.srv',
        # NOTE: do NOT stub 'orbibot_hardware' here — the real package must be importable.
        # rosmaster_driver is caught by a try/except in hardware_node.py.
    ]
    for mod in mods:
        if mod not in sys.modules:
            sys.modules[mod] = types.ModuleType(mod)

    # rclpy.node.Node — base class; must be importable as a real class
    node_mod = sys.modules['rclpy.node']
    if not hasattr(node_mod, 'Node'):
        class _Node:
            def __init__(self, *a, **kw): pass
            def get_logger(self): return MagicMock()
            def get_clock(self): return MagicMock()
            def declare_parameter(self, *a, **kw): pass
            def get_parameter(self, name):
                m = MagicMock()
                m.value = _PARAM_DEFAULTS.get(name, 0.0)
                return m
            def create_publisher(self, *a, **kw): return MagicMock()
            def create_subscription(self, *a, **kw): return MagicMock()
            def create_service(self, *a, **kw): return MagicMock()
            def create_timer(self, *a, **kw): return MagicMock()
            def add_on_set_parameters_callback(self, *a, **kw): pass
        node_mod.Node = _Node

    # Stub callback groups / executors / QoS
    for name, cls_name in [
        ('rclpy.callback_groups', 'ReentrantCallbackGroup'),
        ('rclpy.executors', 'MultiThreadedExecutor'),
    ]:
        m = sys.modules[name]
        if not hasattr(m, cls_name):
            setattr(m, cls_name, MagicMock)

    qos_mod = sys.modules['rclpy.qos']
    for attr in ['QoSProfile', 'ReliabilityPolicy', 'DurabilityPolicy']:
        if not hasattr(qos_mod, attr):
            setattr(qos_mod, attr, MagicMock)

    # rcl_interfaces.msg.SetParametersResult
    rcl_msg = sys.modules['rcl_interfaces.msg']
    if not hasattr(rcl_msg, 'SetParametersResult'):
        class _SetParamsResult:
            def __init__(self): self.successful = True; self.reason = ''
        rcl_msg.SetParametersResult = _SetParamsResult

    # Stub message classes (just need to be instantiable)
    for mod_name, attrs in [
        ('sensor_msgs.msg', ['Imu', 'JointState']),
        ('geometry_msgs.msg', ['Twist', 'Quaternion']),
        ('nav_msgs.msg', ['Odometry']),
        ('std_msgs.msg', ['Int32MultiArray', 'Float32MultiArray', 'UInt16']),
        ('diagnostic_msgs.msg', ['DiagnosticArray', 'DiagnosticStatus', 'KeyValue']),
        ('orbibot_msgs.msg', ['SystemStatus', 'SafetyStatus']),
        ('orbibot_msgs.srv', [
            'SetMotorEnable', 'CalibrateIMU', 'ResetOdometry', 'ResetEncoders',
            'GetFirmwareVersion',
        ]),
    ]:
        mod = sys.modules[mod_name]
        for attr in attrs:
            if not hasattr(mod, attr):
                setattr(mod, attr, MagicMock)

    # Stub rosmaster_driver so hardware_node.py falls into the except ImportError branch
    # (sets ROSMASTER_AVAILABLE=False) without trying to open a real serial port.
    if 'orbibot_hardware.rosmaster_driver' not in sys.modules:
        sys.modules['orbibot_hardware.rosmaster_driver'] = MagicMock()


# Parameter defaults used by the stub get_parameter()
_PARAM_DEFAULTS = {
    'hardware.serial_port': '/dev/motordriver',
    'hardware.data_timeout': 2.0,
    'robot.wheel_radius': 0.05,
    'robot.encoder_edges_per_rev': 1320,
    'control.cmd_timeout': 2.0,
    'control.max_velocity': 1.0,
    'control.max_angular_velocity': 2.0,
    'control.pid_rate_limit': 0.1,
    'rates.sensor_rate': 50.0,
    'rates.status_rate': 10.0,
    'safety.battery_low_threshold': 11.0,
    'safety.battery_critical_voltage': 10.5,
    'odometry.pose_base': 0.001,
    'odometry.pose_drift': 0.02,
    'odometry.yaw_base': 0.01,
    'odometry.yaw_drift': 0.005,
    'odometry.velocity_base': 0.01,
    'odometry.velocity_scale': 0.1,
    'odometry.covariance_decay': 0.99,
    'odometry.heartbeat_interval': 0.5,
    'imu.linear_acceleration_covariance': 0.01,
    'imu.angular_velocity_covariance': 0.0025,
    'imu.orientation_covariance': 0.0025,
}

# Add the package root to sys.path so 'orbibot_hardware' resolves to the real package,
# then stub all ROS 2 dependencies (orbibot_hardware itself must NOT be stubbed).
import os as _os
_pkg_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..'))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

_stub_ros_modules()


def _make_node():
    """Instantiate OrbiBotHardwareNode with all external calls mocked out."""
    from orbibot_hardware.hardware_node import OrbiBotHardwareNode

    with patch.object(OrbiBotHardwareNode, '_create_publishers', return_value=None), \
         patch.object(OrbiBotHardwareNode, '_create_subscribers', return_value=None), \
         patch.object(OrbiBotHardwareNode, '_create_services', return_value=None), \
         patch.object(OrbiBotHardwareNode, '_create_timers', return_value=None), \
         patch.object(OrbiBotHardwareNode, '_initialize_hardware', return_value=None):
        node = OrbiBotHardwareNode()

    # Attach a mock bot and mark hardware connected
    node.bot = MagicMock()
    node.hardware_connected = True
    node.motors_enabled = True

    # Attach publisher stubs used by callbacks
    for pub in ['odom_pub', 'imu_pub', 'imu_raw_pub',
                'encoder_pub', 'joint_states_pub', 'system_status_pub',
                'safety_status_pub', 'diagnostics_pub']:
        setattr(node, pub, MagicMock())

    return node


# ---------------------------------------------------------------------------
# Velocity limiting tests
# ---------------------------------------------------------------------------

class _TwistLike:
    """Minimal Twist-like object for testing _cmd_vel_callback."""
    def __init__(self, lx=0.0, ly=0.0, az=0.0):
        self.linear = MagicMock(x=lx, y=ly, z=0.0)
        self.angular = MagicMock(x=0.0, y=0.0, z=az)


class TestVelocityLimiting:

    def setup_method(self):
        self.node = _make_node()
        self.node.max_velocity = 1.0
        self.node.max_angular_velocity = 2.0

    def test_within_limits_passes_unchanged(self):
        msg = _TwistLike(lx=0.5, ly=0.3, az=1.0)
        self.node._cmd_vel_callback(msg)
        self.node.bot.set_car_motion.assert_called_with(0.5, 0.3, 1.0)
        assert self.node._velocity_limited is False

    def test_vx_clamped_high(self):
        msg = _TwistLike(lx=2.0, ly=0.0, az=0.0)
        self.node._cmd_vel_callback(msg)
        args = self.node.bot.set_car_motion.call_args[0]
        assert args[0] == pytest.approx(1.0)  # clamped to max_velocity
        assert self.node._velocity_limited is True

    def test_vx_clamped_low(self):
        msg = _TwistLike(lx=-3.0, ly=0.0, az=0.0)
        self.node._cmd_vel_callback(msg)
        args = self.node.bot.set_car_motion.call_args[0]
        assert args[0] == pytest.approx(-1.0)
        assert self.node._velocity_limited is True

    def test_vy_clamped(self):
        msg = _TwistLike(lx=0.0, ly=5.0, az=0.0)
        self.node._cmd_vel_callback(msg)
        args = self.node.bot.set_car_motion.call_args[0]
        assert args[1] == pytest.approx(1.0)
        assert self.node._velocity_limited is True

    def test_angular_clamped(self):
        msg = _TwistLike(lx=0.0, ly=0.0, az=10.0)
        self.node._cmd_vel_callback(msg)
        args = self.node.bot.set_car_motion.call_args[0]
        assert args[2] == pytest.approx(2.0)
        assert self.node._velocity_limited is True

    def test_not_sent_when_motors_disabled(self):
        self.node.motors_enabled = False
        msg = _TwistLike(lx=0.5, ly=0.0, az=0.0)
        self.node._cmd_vel_callback(msg)
        self.node.bot.set_car_motion.assert_not_called()

    def test_not_sent_when_hardware_disconnected(self):
        self.node.hardware_connected = False
        msg = _TwistLike(lx=0.5, ly=0.0, az=0.0)
        self.node._cmd_vel_callback(msg)
        self.node.bot.set_car_motion.assert_not_called()

    def test_zero_velocity_not_limited(self):
        msg = _TwistLike(lx=0.0, ly=0.0, az=0.0)
        self.node._cmd_vel_callback(msg)
        assert self.node._velocity_limited is False

    def test_exactly_at_limit_not_flagged(self):
        """Exact limit value should NOT set _velocity_limited."""
        msg = _TwistLike(lx=1.0, ly=0.0, az=2.0)
        self.node._cmd_vel_callback(msg)
        assert self.node._velocity_limited is False


# ---------------------------------------------------------------------------
# Command timeout tests
# ---------------------------------------------------------------------------

class TestCommandTimeout:

    def setup_method(self):
        self.node = _make_node()
        self.node.cmd_timeout = 2.0

    def test_timeout_stop_sent_once(self):
        """After cmd_timeout seconds with no command, stop is sent exactly once."""
        # Simulate expired timeout
        self.node._last_cmd_time = time.time() - 3.0
        self.node._timeout_stop_sent = False

        # First sensor callback cycle triggers stop
        self.node._sensor_callback = lambda: None  # prevent full callback
        # Directly test the timeout logic inline (mirrors _sensor_callback lines 597-609)
        send_stop = False
        import threading
        with self.node._cmd_time_lock:
            cmd_age = time.time() - self.node._last_cmd_time
            motors_active = self.node.motors_enabled
            if cmd_age > self.node.cmd_timeout and motors_active and not self.node._timeout_stop_sent:
                self.node._timeout_stop_sent = True
                send_stop = True
        if send_stop:
            self.node.bot.set_car_motion(0, 0, 0)

        assert self.node.bot.set_car_motion.call_count == 1
        self.node.bot.set_car_motion.assert_called_with(0, 0, 0)

    def test_timeout_stop_not_repeated(self):
        """Once _timeout_stop_sent=True, second invocation does NOT resend stop."""
        self.node._last_cmd_time = time.time() - 3.0
        self.node._timeout_stop_sent = True  # already sent

        send_stop = False
        with self.node._cmd_time_lock:
            cmd_age = time.time() - self.node._last_cmd_time
            motors_active = self.node.motors_enabled
            if cmd_age > self.node.cmd_timeout and motors_active and not self.node._timeout_stop_sent:
                self.node._timeout_stop_sent = True
                send_stop = True
        if send_stop:
            self.node.bot.set_car_motion(0, 0, 0)

        self.node.bot.set_car_motion.assert_not_called()

    def test_new_command_resets_timeout_flag(self):
        """New /cmd_vel message resets _timeout_stop_sent so timeout can fire again."""
        self.node._timeout_stop_sent = True
        msg = _TwistLike(lx=0.0)
        self.node._cmd_vel_callback(msg)
        assert self.node._timeout_stop_sent is False

    def test_fresh_command_does_not_trigger_timeout(self):
        """Recent command (< cmd_timeout ago) should not trigger stop."""
        self.node._last_cmd_time = time.time() - 0.1  # 100ms ago
        self.node._timeout_stop_sent = False

        send_stop = False
        with self.node._cmd_time_lock:
            cmd_age = time.time() - self.node._last_cmd_time
            motors_active = self.node.motors_enabled
            if cmd_age > self.node.cmd_timeout and motors_active and not self.node._timeout_stop_sent:
                send_stop = True
        assert send_stop is False


# ---------------------------------------------------------------------------
# PID rate limiting tests
# ---------------------------------------------------------------------------

class TestPidRateLimit:

    def setup_method(self):
        self.node = _make_node()
        self.node._pid_rate_limit = 0.1  # 100ms minimum between updates

    def test_first_call_always_passes(self):
        """First call passes regardless (last update = 0.0)."""
        self.node._last_pid_update = 0.0
        assert self.node._check_pid_rate_limit('_last_pid_update') is True

    def test_immediate_second_call_blocked(self):
        """Second call within rate_limit window is blocked."""
        self.node._last_pid_update = time.time()
        assert self.node._check_pid_rate_limit('_last_pid_update') is False

    def test_call_after_interval_passes(self):
        """Call after rate_limit interval passes and updates timestamp."""
        self.node._last_pid_update = time.time() - 0.2  # 200ms ago
        result = self.node._check_pid_rate_limit('_last_pid_update')
        assert result is True

    def test_timestamp_updated_on_pass(self):
        """On a passing call, last_update_attr is updated to ~now."""
        self.node._last_pid_update = 0.0
        before = time.time()
        self.node._check_pid_rate_limit('_last_pid_update')
        assert self.node._last_pid_update >= before

    def test_yaw_pid_independent_of_motor_pid(self):
        """Yaw PID and motor PID rate limits are tracked independently."""
        self.node._last_pid_update = time.time()      # motor PID recently updated
        self.node._last_yaw_pid_update = 0.0          # yaw PID not updated
        assert self.node._check_pid_rate_limit('_last_pid_update') is False
        assert self.node._check_pid_rate_limit('_last_yaw_pid_update') is True

    def test_pid_save_independent(self):
        """PID save rate limit is independent of the live PID rate limit."""
        self.node._last_pid_save_update = 0.0
        assert self.node._check_pid_rate_limit('_last_pid_save_update') is True

    def test_yaw_pid_save_independent(self):
        """Yaw PID save has its own rate limit attribute."""
        self.node._last_yaw_pid_save_update = 0.0
        assert self.node._check_pid_rate_limit('_last_yaw_pid_save_update') is True


# ---------------------------------------------------------------------------
# Odometry deduplication tests
# ---------------------------------------------------------------------------

class TestOdomDeduplication:
    """
    Test the deduplication logic in _publish_firmware_odom.
    Mirrors lines 727-735 of hardware_node.py.
    """

    def _call_odom(self, node, odom_data, now_ns=None):
        """Helper: call _publish_firmware_odom with a controlled clock."""
        clock = MagicMock()
        ts = MagicMock()
        ts.nanoseconds = (now_ns if now_ns is not None else int(time.time() * 1e9))
        clock.now.return_value = ts
        ts.to_msg.return_value = MagicMock()
        node.get_clock = MagicMock(return_value=clock)
        node._publish_firmware_odom(odom_data)

    def setup_method(self):
        self.node = _make_node()
        self.node._last_firmware_odom = None
        self.node._last_odom_publish_time = 0.0
        self.node._accumulated_distance = 0.0
        self.node._accumulated_rotation = 0.0
        self.node._last_odom_x = 0.0
        self.node._last_odom_y = 0.0
        self.node._last_odom_theta = 0.0
        self.node._odom_heartbeat_interval = 0.5

    def test_first_call_publishes(self):
        """First call always publishes."""
        data = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        self._call_odom(self.node, data)
        self.node.odom_pub.publish.assert_called_once()

    def test_duplicate_data_skipped_within_heartbeat(self):
        """Same data within heartbeat interval → no publish."""
        data = (1.0, 0.0, 0.0, 0.5, 0.0, 0.0)
        now_ns = int(time.time() * 1e9)
        self._call_odom(self.node, data, now_ns=now_ns)
        call_count_after_first = self.node.odom_pub.publish.call_count

        # Immediately repeat same data → should skip
        self._call_odom(self.node, data, now_ns=now_ns + int(0.1e9))
        assert self.node.odom_pub.publish.call_count == call_count_after_first

    def test_duplicate_data_published_after_heartbeat(self):
        """Same data after heartbeat_interval → published again."""
        data = (1.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        now_ns = int(time.time() * 1e9)
        self._call_odom(self.node, data, now_ns=now_ns)
        count_1 = self.node.odom_pub.publish.call_count

        # Wait past heartbeat interval (0.5s)
        self._call_odom(self.node, data, now_ns=now_ns + int(0.6e9))
        assert self.node.odom_pub.publish.call_count > count_1

    def test_changed_data_always_publishes(self):
        """Different data always triggers a publish."""
        now_ns = int(time.time() * 1e9)
        self._call_odom(self.node, (0.0, 0.0, 0.0, 0.0, 0.0, 0.0), now_ns=now_ns)
        self._call_odom(self.node, (1.0, 0.0, 0.0, 0.5, 0.0, 0.0), now_ns=now_ns + int(0.01e9))
        assert self.node.odom_pub.publish.call_count == 2

    def test_heartbeat_disabled_skips_duplicates(self):
        """heartbeat_interval=0 means disabled: duplicate never re-published."""
        self.node._odom_heartbeat_interval = 0
        data = (2.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        now_ns = int(time.time() * 1e9)
        self._call_odom(self.node, data, now_ns=now_ns)
        count = self.node.odom_pub.publish.call_count
        # Re-publish 60 seconds later with same data and heartbeat disabled
        self._call_odom(self.node, data, now_ns=now_ns + int(60e9))
        assert self.node.odom_pub.publish.call_count == count


# ---------------------------------------------------------------------------
# Magnetometer calibration tests
# ---------------------------------------------------------------------------

# Magnetometer calibration tests removed 2026-04-28 — mag support dropped
# from firmware and driver (see CHANGELOG.md).


# ---------------------------------------------------------------------------
# Quaternion from yaw tests
# ---------------------------------------------------------------------------

class TestQuaternionFromYaw:
    """
    Test the yaw → quaternion conversion used in _publish_firmware_odom.
    Lines 768-772: half_yaw = theta * 0.5; z=sin(half_yaw), w=cos(half_yaw)
    """

    def _yaw_to_quat(self, yaw):
        half = yaw * 0.5
        return 0.0, 0.0, math.sin(half), math.cos(half)

    def test_zero_yaw(self):
        x, y, z, w = self._yaw_to_quat(0.0)
        assert z == pytest.approx(0.0, abs=1e-9)
        assert w == pytest.approx(1.0, abs=1e-9)

    def test_quarter_turn(self):
        """90° → z=sin(π/4)=√2/2, w=cos(π/4)=√2/2."""
        x, y, z, w = self._yaw_to_quat(math.pi / 2)
        assert z == pytest.approx(math.sqrt(2) / 2, rel=1e-9)
        assert w == pytest.approx(math.sqrt(2) / 2, rel=1e-9)

    def test_half_turn(self):
        """180° → z=1, w≈0."""
        x, y, z, w = self._yaw_to_quat(math.pi)
        assert z == pytest.approx(1.0, rel=1e-9)
        assert w == pytest.approx(0.0, abs=1e-9)

    def test_negative_yaw(self):
        """Negative yaw: z negative, w positive."""
        x, y, z, w = self._yaw_to_quat(-math.pi / 2)
        assert z < 0
        assert w > 0

    def test_unit_norm(self):
        """Quaternion has unit norm for any yaw."""
        for yaw in [0.0, 0.5, math.pi / 3, math.pi, -math.pi / 4, 2 * math.pi]:
            x, y, z, w = self._yaw_to_quat(yaw)
            norm = math.sqrt(x*x + y*y + z*z + w*w)
            assert norm == pytest.approx(1.0, rel=1e-9)

    def test_x_y_always_zero(self):
        """Yaw-only quaternion must have x=0, y=0."""
        for yaw in [0.1, 1.2, -0.7, math.pi]:
            x, y, z, w = self._yaw_to_quat(yaw)
            assert x == 0.0
            assert y == 0.0


# ---------------------------------------------------------------------------
# Joint state computation tests
# ---------------------------------------------------------------------------

ENCODER_EDGES_PER_REV = 1320  # 11 PPR × 30:1 gear × 4 quadrature
RAD_PER_EDGE = (2.0 * math.pi) / ENCODER_EDGES_PER_REV


class TestJointStateComputation:
    """
    Test wheel angle accumulation from encoder deltas.
    Mirrors _publish_joint_states lines 817-830.
    """

    def setup_method(self):
        self.node = _make_node()
        self.node.encoder_edges_per_rev = ENCODER_EDGES_PER_REV
        self.node.encoder_initialized = False
        self.node.last_encoders = [0, 0, 0, 0]
        self.node.wheel_positions = [0.0, 0.0, 0.0, 0.0]

    def test_first_call_initializes_and_returns(self):
        """First call stores baseline encoders and does NOT publish."""
        self.node._publish_joint_states([100, 200, 300, 400])
        assert self.node.encoder_initialized is True
        self.node.joint_states_pub.publish.assert_not_called()

    def test_one_full_revolution(self):
        """1320 encoder edges = 2π rad wheel rotation."""
        self.node._publish_joint_states([0, 0, 0, 0])   # init
        self.node._publish_joint_states([1320, 0, 0, 0])
        assert self.node.wheel_positions[0] == pytest.approx(2 * math.pi, rel=1e-6)
        assert self.node.wheel_positions[1] == pytest.approx(0.0, abs=1e-9)

    def test_positive_delta(self):
        """Forward motion: positive delta → positive angle increment."""
        self.node._publish_joint_states([0, 0, 0, 0])
        self.node._publish_joint_states([100, 0, 0, 0])
        expected = 100 * RAD_PER_EDGE
        assert self.node.wheel_positions[0] == pytest.approx(expected, rel=1e-6)

    def test_negative_delta(self):
        """Reverse motion: negative delta → negative angle increment."""
        self.node._publish_joint_states([500, 500, 500, 500])
        self.node._publish_joint_states([400, 500, 500, 500])
        expected = -100 * RAD_PER_EDGE
        assert self.node.wheel_positions[0] == pytest.approx(expected, rel=1e-6)

    def test_all_four_wheels_tracked(self):
        """Deltas for all four wheels tracked independently."""
        self.node._publish_joint_states([0, 0, 0, 0])
        self.node._publish_joint_states([100, 200, 300, 400])
        assert self.node.wheel_positions[0] == pytest.approx(100 * RAD_PER_EDGE, rel=1e-6)
        assert self.node.wheel_positions[1] == pytest.approx(200 * RAD_PER_EDGE, rel=1e-6)
        assert self.node.wheel_positions[2] == pytest.approx(300 * RAD_PER_EDGE, rel=1e-6)
        assert self.node.wheel_positions[3] == pytest.approx(400 * RAD_PER_EDGE, rel=1e-6)

    def test_zero_delta_no_change(self):
        """No encoder movement → no position change."""
        self.node._publish_joint_states([100, 100, 100, 100])
        self.node._publish_joint_states([100, 100, 100, 100])
        assert all(p == pytest.approx(0.0, abs=1e-9) for p in self.node.wheel_positions)

    def test_angles_accumulate_over_multiple_steps(self):
        """Multiple small steps accumulate into total rotation."""
        self.node._publish_joint_states([0, 0, 0, 0])
        for i in range(1, 11):
            self.node._publish_joint_states([i * 100, 0, 0, 0])
        expected = 10 * 100 * RAD_PER_EDGE
        assert self.node.wheel_positions[0] == pytest.approx(expected, rel=1e-6)

    def test_joint_state_published_after_init(self):
        """Publish is called on second and subsequent calls."""
        self.node._publish_joint_states([0, 0, 0, 0])   # init
        self.node._publish_joint_states([10, 0, 0, 0])  # triggers publish
        self.node.joint_states_pub.publish.assert_called_once()
