"""ROS 2 bridge for OrbiBot Agent.

Handles all ROS 2 communication including topics, services, and actions.
"""

import logging
import math
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import rclpy
from action_msgs.msg import GoalStatus
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import (
    DurabilityPolicy,
    QoSProfile,
    ReliabilityPolicy,
    qos_profile_sensor_data,
)
from rclpy.service import Service
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid, Path
from sensor_msgs.msg import Imu, JointState, LaserScan, MagneticField
from std_msgs.msg import Float32MultiArray, Int32MultiArray, String, UInt16
from visualization_msgs.msg import MarkerArray

from orbibot_msgs.msg import SafetyStatus, SystemStatus

logger = logging.getLogger(__name__)


class RosBridge:
    """ROS 2 communication bridge for robot operations."""

    def __init__(self, node: Node):
        """Initialize ROS bridge with a ROS node.

        Args:
            node: rclpy Node instance
        """
        self._node = node
        self._safety_manager = None

        # Publishers
        self._cmd_vel_pub = node.create_publisher(Twist, '/cmd_vel', 10)
        self._pid_params_pub = node.create_publisher(Float32MultiArray, '/orbibot/pid_params', 10)
        self._yaw_pid_params_pub = node.create_publisher(
            Float32MultiArray, '/orbibot/yaw_pid_params', 10
        )
        self._pid_save_pub = node.create_publisher(Float32MultiArray, '/orbibot/pid_save', 10)
        self._yaw_pid_save_pub = node.create_publisher(
            Float32MultiArray, '/orbibot/yaw_pid_save', 10
        )
        self._beep_pub = node.create_publisher(UInt16, '/orbibot/beep', 10)

        # Cached subscriptions (created on demand)
        self._subscriptions: Dict[str, Any] = {}
        self._latest_messages: Dict[str, Any] = {}

        # Action clients cache
        self._action_clients: Dict[str, ActionClient] = {}

        # Active action goals tracking
        self._active_goals: Dict[str, Dict] = {}

        # Service clients cache
        self._service_clients: Dict[str, Any] = {}

        # Cached dynamic publishers (created on demand by publish_topic)
        self._topic_publishers: Dict[str, Any] = {}

        logger.info('RosBridge initialized')

    def set_safety_manager(self, safety_manager) -> None:
        """Set safety manager for validation.

        Args:
            safety_manager: SafetyManager instance
        """
        self._safety_manager = safety_manager

    def publish_cmd_vel(self, vx: float, vy: float, wz: float) -> None:
        """Publish velocity command.

        Args:
            vx: Linear x velocity (forward/back)
            vy: Linear y velocity (left/right for mecanum)
            wz: Angular z velocity (rotation)
        """
        # Validate with safety manager if available
        if self._safety_manager:
            vx, vy, wz = self._safety_manager.validate_velocity(vx, vy, wz)
            if self._safety_manager.check_emergency_stop():
                logger.warning('Emergency stop active - blocking cmd_vel')
                vx, vy, wz = 0.0, 0.0, 0.0

        msg = Twist()
        msg.linear.x = float(vx)
        msg.linear.y = float(vy)
        msg.angular.z = float(wz)

        self._cmd_vel_pub.publish(msg)
        logger.debug(f'Published cmd_vel: vx={vx}, vy={vy}, wz={wz}')

    def publish_stop(self) -> None:
        """Publish zero velocity (emergency stop)."""
        self.publish_cmd_vel(0.0, 0.0, 0.0)
        logger.info('Published stop command')

    def set_motor_pid(self, kp: float, ki: float, kd: float) -> None:
        """Set motor PID gains (all wheels). Takes effect immediately; use pid_save to persist."""
        msg = Float32MultiArray()
        msg.data = [float(kp), float(ki), float(kd)]
        self._pid_params_pub.publish(msg)
        logger.info(f'Published motor PID: kp={kp}, ki={ki}, kd={kd}')

    def set_yaw_pid(self, kp: float, ki: float, kd: float) -> None:
        """Set yaw (heading) PID gains. Takes effect immediately."""
        msg = Float32MultiArray()
        msg.data = [float(kp), float(ki), float(kd)]
        self._yaw_pid_params_pub.publish(msg)
        logger.info(f'Published yaw PID: kp={kp}, ki={ki}, kd={kd}')

    def save_motor_pid(self, kp: float, ki: float, kd: float) -> Dict[str, Any]:
        """Save motor PID gains to firmware flash (persists across reboot)."""
        msg = Float32MultiArray()
        msg.data = [float(kp), float(ki), float(kd)]
        self._pid_save_pub.publish(msg)
        logger.info(f'Published motor PID save: kp={kp}, ki={ki}, kd={kd}')
        return {'status': 'ok', 'motor_pid_saved': {'kp': kp, 'ki': ki, 'kd': kd},
                'note': 'Gains written to firmware flash — will persist after reboot'}

    def save_yaw_pid(self, kp: float, ki: float, kd: float) -> Dict[str, Any]:
        """Save yaw PID gains to firmware flash (persists across reboot)."""
        msg = Float32MultiArray()
        msg.data = [float(kp), float(ki), float(kd)]
        self._yaw_pid_save_pub.publish(msg)
        logger.info(f'Published yaw PID save: kp={kp}, ki={ki}, kd={kd}')
        return {'status': 'ok', 'yaw_pid_saved': {'kp': kp, 'ki': ki, 'kd': kd},
                'note': 'Gains written to firmware flash — will persist after reboot'}

    def set_beep(self, duration_ms: int) -> Dict[str, Any]:
        """Control the buzzer.

        Args:
            duration_ms: 0=off, 1=continuous, >=10=beep for N milliseconds.

        Returns:
            Status dict.
        """
        msg = UInt16()
        msg.data = int(max(0, duration_ms))
        self._beep_pub.publish(msg)
        if duration_ms == 0:
            description = 'off'
        elif duration_ms == 1:
            description = 'continuous'
        else:
            description = f'{duration_ms}ms'
        logger.info(f'Published beep: {description}')
        return {'status': 'ok', 'buzzer': description}

    def reset_odometry(self) -> Dict[str, Any]:
        """Reset firmware odometry to zero via /orbibot/reset_odometry service."""
        return self.call_service(
            '/orbibot/reset_odometry',
            'orbibot_msgs/srv/ResetOdometry',
            {},
            timeout=5.0,
        )

    def reset_encoders(self) -> Dict[str, Any]:
        """Reset encoder counts to zero on MCU via /orbibot/reset_encoders service."""
        return self.call_service(
            '/orbibot/reset_encoders',
            'orbibot_msgs/srv/ResetEncoders',
            {},
            timeout=5.0,
        )

    def calibrate_imu(self, calibration_time: int = 5) -> Dict[str, Any]:
        """Trigger magnetometer auto-calibration via /orbibot/calibrate_imu service."""
        return self.call_service(
            '/orbibot/calibrate_imu',
            'orbibot_msgs/srv/CalibrateIMU',
            {'calibration_time': int(calibration_time)},
            timeout=max(calibration_time + 5, 10.0),
        )

    def set_mag_calibration(
        self, offset_x: float, offset_y: float, offset_z: float
    ) -> Dict[str, Any]:
        """Set magnetometer hard-iron calibration offsets (µT).

        Args:
            offset_x: Hard-iron offset for X axis in µT.
            offset_y: Hard-iron offset for Y axis in µT.
            offset_z: Hard-iron offset for Z axis in µT.

        Returns:
            Service response dict.
        """
        return self.call_service(
            '/orbibot/set_mag_calibration',
            'orbibot_msgs/srv/SetMagCalibration',
            {
                'offset_x': float(offset_x),
                'offset_y': float(offset_y),
                'offset_z': float(offset_z),
            },
            timeout=5.0,
        )

    def reset_firmware_state(self) -> Dict[str, Any]:
        """Emergency: stop motors and reset firmware state machine.

        Sends a stop command then calls reset_odometry to clear firmware state.
        Motors must be re-enabled after this call.
        """
        self.publish_stop()
        result = self.reset_odometry()
        if self._safety_manager:
            self._safety_manager.reset_emergency_stop()
        logger.warning('Firmware state reset: motors stopped, odometry cleared')
        return {
            'status': 'ok',
            'actions': ['cmd_vel zeroed', 'odometry reset'],
            'note': 'Call set_motor_enable(true) to resume movement',
            'reset_odometry_result': result,
        }

    def wait_for_message(
        self,
        msg_type: type,
        topic: str,
        timeout: Optional[float] = None,
        qos=None,
    ) -> Optional[Any]:
        """Wait for a single message on a topic.

        Args:
            msg_type: ROS message type
            topic: Topic name
            timeout: Timeout in seconds
            qos: QoS profile

        Returns:
            Message or None if timeout
        """
        timeout = timeout or (self._safety_manager.sensor_timeout if self._safety_manager else 3.0)

        result = [None]
        event = threading.Event()

        def _callback(msg):
            result[0] = msg
            event.set()

        profile = qos or qos_profile_sensor_data
        sub = self._node.create_subscription(msg_type, topic, _callback, profile)

        event.wait(timeout=timeout)
        self._node.destroy_subscription(sub)

        if result[0] is None:
            logger.warning(f'Timeout waiting for message on {topic}')

        return result[0]

    def get_battery_status(self) -> Optional[Dict[str, Any]]:
        """Get battery status from system_status topic.

        Returns:
            Dictionary with voltage and status, or None if unavailable
        """
        try:
            msg = self.wait_for_message(
                SystemStatus, '/orbibot/system_status',
                qos=qos_profile_sensor_data,
            )
            if msg is None:
                return None

            voltage = msg.battery_voltage
            if voltage >= 14.6:
                level = 'full'
            elif voltage >= 11.0:
                level = 'normal'
            elif voltage >= 10.5:
                level = 'low'
            else:
                level = 'critical'

            return {
                'voltage': round(voltage, 2),
                'status': level,
            }
        except Exception as e:
            logger.error(f'Failed to get battery status: {e}')
            return None

    def get_imu_data(self) -> Optional[Dict[str, Any]]:
        """Get IMU data.

        Returns:
            Dictionary with orientation and velocities, or None if unavailable
        """
        try:
            msg = self.wait_for_message(Imu, '/imu/data')
            if msg is None:
                return None

            o = msg.orientation
            yaw = self._quat_to_yaw(o)

            # Calculate pitch and roll
            siny = 2.0 * (o.w * o.y - o.z * o.x)
            pitch = math.degrees(math.asin(max(-1.0, min(1.0, siny))))
            sinr = 2.0 * (o.w * o.x + o.y * o.z)
            cosr = 1.0 - 2.0 * (o.x * o.x + o.y * o.y)
            roll = math.degrees(math.atan2(sinr, cosr))

            return {
                'roll_deg': round(roll, 2),
                'pitch_deg': round(pitch, 2),
                'yaw_deg': round(yaw, 2),
                'angular_velocity': {
                    'x': round(msg.angular_velocity.x, 4),
                    'y': round(msg.angular_velocity.y, 4),
                    'z': round(msg.angular_velocity.z, 4),
                },
            }
        except Exception as e:
            logger.error(f'Failed to get IMU data: {e}')
            return None

    def get_encoder_counts(self) -> Optional[Dict[str, Any]]:
        """Get raw encoder tick counts for all four wheels.

        Returns:
            Dict with fl, bl, fr, br ticks, or None if unavailable.
        """
        try:
            msg = self.wait_for_message(Int32MultiArray, '/orbibot/encoders')
            if msg is None or len(msg.data) < 4:
                return None
            return {
                'front_left': int(msg.data[0]),
                'back_left': int(msg.data[1]),
                'front_right': int(msg.data[2]),
                'back_right': int(msg.data[3]),
                'note': 'Raw encoder ticks since firmware startup or last reset',
            }
        except Exception as e:
            logger.error(f'Failed to get encoder counts: {e}')
            return None

    def get_imu_raw(self) -> Optional[Dict[str, Any]]:
        """Get raw IMU data (pre-Madgwick) — gyroscope and accelerometer only.

        Returns:
            Dict with gyro (rad/s) and accel (m/s²), or None if unavailable.
        """
        try:
            msg = self.wait_for_message(Imu, '/imu/data_raw')
            if msg is None:
                return None
            return {
                'gyro': {
                    'x_rad_s': round(msg.angular_velocity.x, 5),
                    'y_rad_s': round(msg.angular_velocity.y, 5),
                    'z_rad_s': round(msg.angular_velocity.z, 5),
                },
                'accel': {
                    'x_m_s2': round(msg.linear_acceleration.x, 4),
                    'y_m_s2': round(msg.linear_acceleration.y, 4),
                    'z_m_s2': round(msg.linear_acceleration.z, 4),
                },
                'note': 'Raw sensor values before Madgwick fusion (no orientation)',
            }
        except Exception as e:
            logger.error(f'Failed to get raw IMU data: {e}')
            return None

    def get_magnetometer(self) -> Optional[Dict[str, Any]]:
        """Get magnetometer data from the ICM-20948 AK09916 compass.

        Returns:
            Dict with x, y, z in µT, or None if unavailable.
        """
        try:
            msg = self.wait_for_message(MagneticField, '/imu/mag')
            if msg is None:
                return None
            # hardware_node publishes in Tesla; convert to µT for readability
            return {
                'x_uT': round(msg.magnetic_field.x * 1e6, 3),
                'y_uT': round(msg.magnetic_field.y * 1e6, 3),
                'z_uT': round(msg.magnetic_field.z * 1e6, 3),
                'magnitude_uT': round(
                    math.sqrt(
                        msg.magnetic_field.x ** 2
                        + msg.magnetic_field.y ** 2
                        + msg.magnetic_field.z ** 2
                    ) * 1e6,
                    3,
                ),
            }
        except Exception as e:
            logger.error(f'Failed to get magnetometer data: {e}')
            return None

    def get_joint_states(self) -> Optional[Dict[str, Any]]:
        """Get wheel joint positions and velocities.

        Returns:
            Dict with per-wheel position (rad) and velocity (rad/s), or None.
        """
        try:
            msg = self.wait_for_message(JointState, '/joint_states')
            if msg is None:
                return None
            names = list(msg.name)
            positions = [round(float(p), 4) for p in msg.position]
            velocities = [round(float(v), 4) for v in msg.velocity] if msg.velocity else []
            joints = {}
            for i, name in enumerate(names):
                joints[name] = {
                    'position_rad': positions[i] if i < len(positions) else 0.0,
                    'velocity_rad_s': velocities[i] if i < len(velocities) else 0.0,
                }
            return {'joints': joints}
        except Exception as e:
            logger.error(f'Failed to get joint states: {e}')
            return None

    def get_safety_status(self) -> Optional[Dict[str, Any]]:
        """Get safety system status (e-stop, faults, battery warnings).

        Returns:
            Dict with all safety flags, or None if unavailable.
        """
        try:
            msg = self.wait_for_message(SafetyStatus, '/orbibot/safety_status')
            if msg is None:
                return None
            return {
                'emergency_stop': bool(msg.emergency_stop),
                'cmd_timeout': bool(msg.cmd_timeout),
                'low_battery': bool(msg.low_battery),
                'hardware_fault': bool(msg.hardware_fault),
                'velocity_limit': bool(msg.velocity_limit),
                'temperature_limit': bool(msg.temperature_limit),
                'motors_disabled': bool(msg.motors_disabled),
                'fault_code': int(msg.fault_code),
                'all_clear': not any([
                    msg.emergency_stop, msg.cmd_timeout, msg.low_battery,
                    msg.hardware_fault, msg.temperature_limit,
                ]),
            }
        except Exception as e:
            logger.error(f'Failed to get safety status: {e}')
            return None

    def get_system_enriched(self) -> Optional[Dict[str, Any]]:
        """Get enriched system status (CPU%, RAM%, temp, disk, battery).

        Returns:
            Dict with all system_status_enriched fields, or None if unavailable.
        """
        try:
            msg = self.wait_for_message(SystemStatus, '/orbibot/system_status_enriched')
            if msg is None:
                # Fall back to basic system_status
                msg = self.wait_for_message(SystemStatus, '/orbibot/system_status')
            if msg is None:
                return None
            return {
                'battery_voltage': round(float(msg.battery_voltage), 2),
                'cpu_percent': round(float(msg.cpu_percent), 1),
                'ram_percent': round(float(msg.ram_percent), 1),
                'cpu_temp_c': round(float(msg.cpu_temp), 1),
                'disk_percent': round(float(msg.disk_percent), 1),
                'motors_enabled': bool(msg.motors_enabled),
                'emergency_stop': bool(msg.emergency_stop),
                'hardware_ok': bool(msg.hardware_ok),
            }
        except Exception as e:
            logger.error(f'Failed to get enriched system status: {e}')
            return None

    def get_firmware_version(self) -> Optional[Dict[str, Any]]:
        """Get firmware version by calling /orbibot/get_firmware_version service.

        Returns:
            Dict with major, minor, version_string, or None if unavailable.
        """
        try:
            result = self.call_service(
                '/orbibot/get_firmware_version',
                'orbibot_msgs/srv/GetFirmwareVersion',
                {},
                timeout=3.0,
            )
            if not result.get('success'):
                return {'error': result.get('error', 'Service call failed')}
            resp = result.get('response', {})
            return {
                'version': resp.get('version_string', 'unknown'),
                'major': resp.get('major', 0),
                'minor': resp.get('minor', 0),
            }
        except Exception as e:
            logger.error(f'Failed to get firmware version: {e}')
            return None

    def get_all_firmware_data(self) -> Dict[str, Any]:
        """Get a comprehensive snapshot of all firmware-accessible values.

        Returns:
            Dict with battery, imu, imu_raw, magnetometer, encoders, joint_states,
            odometry, safety_status, and firmware_version merged.
        """
        snapshot = {}

        battery = self.get_battery_status()
        snapshot['battery'] = battery or {'error': 'unavailable'}

        imu = self.get_imu_data()
        snapshot['imu_attitude'] = imu or {'error': 'unavailable'}

        imu_raw = self.get_imu_raw()
        snapshot['imu_raw'] = imu_raw or {'error': 'unavailable'}

        mag = self.get_magnetometer()
        snapshot['magnetometer'] = mag or {'error': 'unavailable'}

        encoders = self.get_encoder_counts()
        snapshot['encoders'] = encoders or {'error': 'unavailable'}

        joints = self.get_joint_states()
        snapshot['joint_states'] = joints or {'error': 'unavailable'}

        odom = self.get_odometry()
        snapshot['odometry'] = odom or {'error': 'unavailable'}

        safety = self.get_safety_status()
        snapshot['safety_status'] = safety or {'error': 'unavailable'}

        version = self.get_firmware_version()
        snapshot['firmware_version'] = version or {'error': 'unavailable'}

        system = self.get_system_enriched()
        snapshot['system'] = system or {'error': 'unavailable'}

        return snapshot

    def get_odometry(self) -> Optional[Dict[str, Any]]:
        """Get odometry data.

        Returns:
            Dictionary with position and velocity, or None if unavailable
        """
        try:
            # /odom from hardware uses RELIABLE + TRANSIENT_LOCAL; must match for compatibility
            odom_qos = QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                depth=5,
            )
            msg = self.wait_for_message(Odometry, '/odom', qos=odom_qos)
            if msg is None:
                return None

            pos = msg.pose.pose.position
            yaw = self._quat_to_yaw(msg.pose.pose.orientation)
            vel = msg.twist.twist

            return {
                'position': {'x': round(pos.x, 3), 'y': round(pos.y, 3)},
                'yaw_deg': round(yaw, 2),
                'velocity': {
                    'linear_x': round(vel.linear.x, 3),
                    'linear_y': round(vel.linear.y, 3),
                    'angular_z': round(vel.angular.z, 3),
                },
            }
        except Exception as e:
            logger.error(f'Failed to get odometry: {e}')
            return None

    def run_pid_test(
        self,
        vx: float,
        vy: float,
        wz: float,
        duration: float = 5.0,
        sample_hz: float = 20.0,
    ) -> Dict[str, Any]:
        """Run a PID test: publish cmd_vel and record /odom velocity response.

        Used to tune motor/yaw PID by comparing target vs actual (MAE, overshoot).

        Args:
            vx: Target linear x velocity (m/s)
            vy: Target linear y velocity (m/s)
            wz: Target angular z velocity (rad/s)
            duration: Test duration in seconds (clamped 1–15)
            sample_hz: Approximate sampling rate for /odom (Hz)

        Returns:
            Dict with samples (t, vx, vy, wz), metrics (MAE, max_error, overshoot_pct per axis),
            and target. Samples may be downsampled if > 200 points.
        """
        if self._safety_manager:
            vx, vy, wz = self._safety_manager.validate_velocity(vx, vy, wz)
        duration = max(1.0, min(15.0, float(duration)))
        dt = 1.0 / max(10.0, min(50.0, sample_hz))

        odom_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=5,
        )
        latest: Dict[str, float] = {'vx': 0.0, 'vy': 0.0, 'wz': 0.0}

        def _odom_cb(msg):
            latest['vx'] = msg.twist.twist.linear.x
            latest['vy'] = msg.twist.twist.linear.y
            latest['wz'] = msg.twist.twist.angular.z

        sub = self._node.create_subscription(
            Odometry, '/odom', _odom_cb, odom_qos
        )

        samples: List[Dict[str, float]] = []
        t0 = time.perf_counter()
        end_time = t0 + duration

        # Use threading.Event-based sleep to allow safe interruption from other threads.
        # Avoid calling rclpy.spin_once() here: when run from the MCP server the node is
        # already spinning in an executor; a nested spin_once would deadlock.
        stop_event = threading.Event()

        try:
            while time.perf_counter() < end_time:
                if self._safety_manager and self._safety_manager.check_emergency_stop():
                    break
                self.publish_cmd_vel(vx, vy, wz)
                t = time.perf_counter() - t0
                samples.append({
                    't': round(t, 3),
                    'vx': round(latest['vx'], 4),
                    'vy': round(latest['vy'], 4),
                    'wz': round(latest['wz'], 4),
                })
                stop_event.wait(timeout=dt)
        finally:
            self._node.destroy_subscription(sub)
            self.publish_stop()

        # Downsample if too many points (keep at most 200)
        if len(samples) > 200:
            step = len(samples) / 200
            indices = [int(i * step) for i in range(200)]
            samples = [samples[i] for i in indices]

        def _metrics(vals: List[float], target: float) -> Dict[str, float]:
            errs = [abs(v - target) for v in vals]
            mae = sum(errs) / len(errs) if errs else 0.0
            max_err = max(errs) if errs else 0.0
            overshoot_pct = 0.0
            if abs(target) > 1e-9:
                if target > 0 and vals:
                    overshoot_pct = max(0.0, (max(vals) - target) / target * 100.0)
                elif target < 0 and vals:
                    overshoot_pct = max(0.0, (target - min(vals)) / abs(target) * 100.0)
            return {'mae': round(mae, 4), 'max_error': round(max_err, 4), 'overshoot_pct': round(overshoot_pct, 1)}

        vx_vals = [s['vx'] for s in samples]
        vy_vals = [s['vy'] for s in samples]
        wz_vals = [s['wz'] for s in samples]

        return {
            'target': {'vx': vx, 'vy': vy, 'wz': wz},
            'duration_sec': round(duration, 1),
            'sample_count': len(samples),
            'metrics': {
                'vx': _metrics(vx_vals, vx),
                'vy': _metrics(vy_vals, vy),
                'wz': _metrics(wz_vals, wz),
            },
            'samples': samples,
        }

    def get_lidar_summary(self) -> Optional[Dict[str, Any]]:
        """Get LiDAR scan summary.

        Returns:
            Dictionary with scan statistics, or None if unavailable
        """
        try:
            msg = self.wait_for_message(LaserScan, '/scan')
            if msg is None:
                return None

            ranges = [r for r in msg.ranges if msg.range_min < r < msg.range_max]

            if not ranges:
                return {
                    'point_count': len(msg.ranges),
                    'valid_points': 0,
                    'message': 'No valid range readings',
                }

            # Find front clearance (around 0 degrees)
            front_idx = len(msg.ranges) // 2
            front_range = msg.ranges[front_idx] if front_idx < len(msg.ranges) else float('inf')

            # Find nearby obstacles
            obstacles = []
            for i, r in enumerate(msg.ranges):
                if msg.range_min < r < 0.5:  # Within 0.5m
                    angle = msg.angle_min + i * msg.angle_increment
                    angle_deg = math.degrees(angle)
                    obstacles.append({
                        'angle_deg': round(angle_deg, 1),
                        'distance': round(r, 3),
                    })

            return {
                'point_count': len(msg.ranges),
                'valid_points': len(ranges),
                'min_range': round(min(ranges), 3),
                'max_range': round(max(ranges), 3),
                'avg_range': round(sum(ranges) / len(ranges), 3),
                'front_clearance': round(front_range, 3) if front_range < msg.range_max else 'inf',
                'nearby_obstacles': obstacles[:10],  # Limit to 10 closest
                'obstacle_count': len(obstacles),
            }
        except Exception as e:
            logger.error(f'Failed to get LiDAR data: {e}')
            return None

    def list_topics(self) -> List[Dict[str, Any]]:
        """List all active ROS topics.

        Returns:
            List of topic information dictionaries
        """
        try:
            topic_list = self._node.get_topic_names_and_types()
            return [
                {'name': name, 'types': types}
                for name, types in topic_list
            ]
        except Exception as e:
            logger.error(f'Failed to list topics: {e}')
            return []

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status.

        Returns:
            Dictionary with system information
        """
        result = {}

        # CPU load
        try:
            with open('/proc/loadavg', 'r') as f:
                load = f.read().split()
            result['cpu_load_1min'] = float(load[0])
        except Exception:
            result['cpu_load_1min'] = None

        # RAM usage
        try:
            with open('/proc/meminfo', 'r') as f:
                lines = f.readlines()
            mem = {}
            for line in lines[:3]:
                key, val = line.split(':')
                mem[key.strip()] = int(val.strip().split()[0])
            total = mem.get('MemTotal', 1)
            avail = mem.get('MemAvailable', 0)
            result['ram_used_pct'] = round((1 - avail / total) * 100, 1)
        except Exception:
            result['ram_used_pct'] = None

        # CPU temperature
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = f.read().strip()
            result['cpu_temp_c'] = round(int(temp) / 1000.0, 1)
        except Exception:
            result['cpu_temp_c'] = None

        # Battery
        battery = self.get_battery_status()
        result['battery'] = battery or {'error': 'Unavailable'}

        return result

    @staticmethod
    def _quat_to_yaw(q) -> float:
        """Convert quaternion to yaw in degrees.

        Args:
            q: Quaternion message

        Returns:
            Yaw angle in degrees
        """
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.degrees(math.atan2(siny_cosp, cosy_cosp))

    def move_for_duration(
        self,
        vx: float,
        vy: float,
        wz: float,
        duration: float,
        callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Move robot for a specified duration.

        Args:
            vx: Forward/backward velocity
            vy: Left/right velocity (mecanum)
            wz: Angular velocity
            duration: Duration in seconds
            callback: Optional callback function for progress updates

        Returns:
            Dictionary with movement result
        """
        # Validate with safety manager
        if self._safety_manager:
            vx, vy, wz = self._safety_manager.validate_velocity(vx, vy, wz)
            duration = self._safety_manager.validate_duration(duration)

        hz = 10  # Publish at 10 Hz
        steps = int(duration * hz)

        logger.info(f'Moving: vx={vx}, vy={vy}, wz={wz} for {duration}s')

        for i in range(steps):
            if self._safety_manager and self._safety_manager.check_emergency_stop():
                logger.warning('Emergency stop during movement')
                break

            self.publish_cmd_vel(vx, vy, wz)
            time.sleep(1.0 / hz)

            if callback:
                callback(i / steps)

        # Send stop
        self.publish_stop()

        return {
            'status': 'completed',
            'vx': vx,
            'vy': vy,
            'wz': wz,
            'duration': duration,
        }

    # =========================================================================
    # Service Methods
    # =========================================================================

    def list_services(self) -> List[Dict[str, Any]]:
        """List all available ROS services.

        Returns:
            List of service information dictionaries
        """
        try:
            service_list = self._node.get_service_names_and_types()
            return [
                {'name': name, 'types': types}
                for name, types in service_list
            ]
        except Exception as e:
            logger.error(f'Failed to list services: {e}')
            return []

    def call_service(
        self,
        service_name: str,
        service_type: str,
        request_dict: Dict[str, Any],
        timeout: float = 5.0,
    ) -> Dict[str, Any]:
        """Call a ROS service.

        Args:
            service_name: Full service name (e.g., '/map_server/load_map')
            service_type: Service type string (e.g., 'nav2_msgs/srv/LoadMap')
            request_dict: Dictionary with request fields
            timeout: Timeout in seconds

        Returns:
            Dictionary with service response or error
        """
        try:
            # Import service type dynamically
            # ROS 2 service types: package/srv/ServiceName (3 parts)
            parts = service_type.split('/')
            if len(parts) == 3 and parts[1] == 'srv':
                module_name, _, srv_name = parts
            elif len(parts) == 2:
                module_name, srv_name = parts  # legacy: package/ServiceName
            else:
                return {
                    'success': False,
                    'error': f'Invalid service type format: {service_type}. Expected package/srv/ServiceName'
                }
            import importlib
            srv_module = importlib.import_module(f'{module_name}.srv')
            srv_class = getattr(srv_module, srv_name)
            srv_req_class = getattr(srv_module, f'{srv_name}_Request')
            srv_resp_class = getattr(srv_module, f'{srv_name}_Response')

            # Create client if not exists
            if service_name not in self._service_clients:
                self._service_clients[service_name] = self._node.create_client(
                    srv_class, service_name
                )
                logger.info(f'Created service client for {service_name}')

            client = self._service_clients[service_name]

            # Wait for service to be available
            if not client.wait_for_service(timeout_sec=timeout):
                return {
                    'success': False,
                    'error': f'Service {service_name} not available within {timeout}s'
                }

            # Create request
            request = srv_req_class()
            for key, value in request_dict.items():
                if hasattr(request, key):
                    setattr(request, key, value)

            # Call service asynchronously
            future = client.call_async(request)
            done_event = threading.Event()
            future.add_done_callback(lambda _: done_event.set())

            # Wait for response. Do NOT spin here: when running under MCP the node is
            # already being spun by _spin_ros in another thread; spinning here causes
            # "Executor is already spinning" and service call failure.
            if not done_event.wait(timeout=timeout):
                return {
                    'success': False,
                    'error': f'Service call timed out after {timeout}s'
                }

            response = future.result()
            if response is None:
                return {
                    'success': False,
                    'error': 'Service call returned None'
                }

            # Convert response to dict
            response_dict = {}
            for slot in response.__slots__:
                val = getattr(response, slot)
                # Handle basic types
                if isinstance(val, (str, int, float, bool, list, dict, type(None))):
                    response_dict[slot] = val
                else:
                    response_dict[slot] = str(val)

            return {
                'success': True,
                'service': service_name,
                'response': response_dict
            }

        except ImportError as e:
            logger.error(f'Failed to import service type {service_type}: {e}')
            return {
                'success': False,
                'error': f'Cannot import service type {service_type}: {e}'
            }
        except Exception as e:
            logger.error(f'Service call failed: {e}')
            return {
                'success': False,
                'error': str(e)
            }

    # =========================================================================
    # Action Methods
    # =========================================================================

    def list_actions(self) -> List[Dict[str, Any]]:
        """List available action servers.

        Returns:
            List of action server information
        """
        try:
            # Get action names from graph
            action_names = []
            for name in self._node.get_action_names():
                action_names.append({
                    'name': name,
                    'type': 'unknown'  # Type discovery would need service calls
                })
            return action_names
        except Exception as e:
            logger.error(f'Failed to list actions: {e}')
            return []

    def get_action_status(self, action_name: str) -> Dict[str, Any]:
        """Get status of an action server.

        Args:
            action_name: Full action name (e.g., '/navigate_to_pose')

        Returns:
            Dictionary with action status
        """
        status_topic = f'{action_name}/_action/status'

        try:
            msg = self.wait_for_message(
                GoalStatus, status_topic, timeout=2.0
            )
            if msg is None:
                return {
                    'action_name': action_name,
                    'active_goals': [],
                    'goal_count': 0,
                    'note': 'No status message received'
                }

            status_map = {
                GoalStatus.STATUS_UNKNOWN: 'UNKNOWN',
                GoalStatus.STATUS_ACCEPTED: 'ACCEPTED',
                GoalStatus.STATUS_EXECUTING: 'EXECUTING',
                GoalStatus.STATUS_CANCELING: 'CANCELING',
                GoalStatus.STATUS_SUCCEEDED: 'SUCCEEDED',
                GoalStatus.STATUS_CANCELED: 'CANCELED',
                GoalStatus.STATUS_ABORTED: 'ABORTED',
            }

            return {
                'action_name': action_name,
                'status_code': msg.status,
                'status_text': status_map.get(msg.status, 'UNKNOWN'),
                'goal_id': str(msg.goal_info.goal_id.uuid) if hasattr(msg, 'goal_info') else 'unknown'
            }
        except Exception as e:
            logger.error(f'Failed to get action status: {e}')
            return {
                'action_name': action_name,
                'error': str(e)
            }

    def send_action_goal(
        self,
        action_name: str,
        action_type: str,
        goal_dict: Dict[str, Any],
        feedback_callback: Optional[Callable] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """Send an action goal.

        Args:
            action_name: Full action name (e.g., '/navigate_to_pose')
            action_type: Action type (e.g., 'nav2_msgs/action/NavigateToPose')
            goal_dict: Dictionary with goal fields
            feedback_callback: Optional callback for feedback
            timeout: Timeout in seconds

        Returns:
            Dictionary with goal result
        """
        try:
            # Import action type dynamically.
            # Supports both "package/ActionName" and "package/action/ActionName" formats.
            import importlib
            parts = action_type.split('/')
            if len(parts) == 3 and parts[1] == 'action':
                module_name, _, act_name = parts
            elif len(parts) == 2:
                module_name, act_name = parts
            else:
                return {
                    'success': False,
                    'error': (
                        f'Invalid action type format: {action_type}. '
                        'Expected package/action/ActionName or package/ActionName'
                    ),
                }
            act_module = importlib.import_module(f'{module_name}.action')
            act_class = getattr(act_module, act_name)
            goal_class = getattr(act_module, f'{act_name}_Goal')

            # Create action client if not exists
            if action_name not in self._action_clients:
                self._action_clients[action_name] = ActionClient(
                    self._node, act_class, action_name
                )
                logger.info(f'Created action client for {action_name}')

            client = self._action_clients[action_name]

            # Wait for action server
            if not client.wait_for_server(timeout_sec=5.0):
                return {
                    'success': False,
                    'error': f'Action server {action_name} not available'
                }

            # Create goal
            goal_msg = goal_class()

            # Set goal fields from dictionary
            self._set_message_fields(goal_msg, goal_dict)

            # Generate goal ID
            goal_id = f'goal_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}'

            # Store goal info
            self._active_goals[goal_id] = {
                'action_name': action_name,
                'action_type': action_type,
                'status': 'PENDING',
                'start_time': time.time(),
                'feedback': []
            }

            # Send goal
            send_goal_future = client.send_goal_async(
                goal_msg,
                feedback_callback=lambda fb: self._feedback_callback(goal_id, fb, feedback_callback)
            )
            send_goal_future.add_done_callback(
                lambda future: self._goal_response_callback(goal_id, future)
            )

            # Wait for goal to be accepted/rejected
            start_time = time.time()
            while time.time() - start_time < timeout:
                if goal_id in self._active_goals:
                    status = self._active_goals[goal_id]['status']
                    if status in ['ACCEPTED', 'EXECUTING', 'SUCCEEDED', 'ABORTED', 'CANCELED']:
                        break
                rclpy.spin_once(self._node, timeout_sec=0.1)

            return {
                'success': True,
                'goal_id': goal_id,
                'action_name': action_name,
                'action_type': action_type,
                'status': self._active_goals.get(goal_id, {}).get('status', 'UNKNOWN'),
                'note': f'Goal sent. Use get_action_result to check completion.'
            }

        except ImportError as e:
            logger.error(f'Failed to import action type {action_type}: {e}')
            return {
                'success': False,
                'error': f'Cannot import action type {action_type}: {e}'
            }
        except Exception as e:
            logger.error(f'Action goal failed: {e}')
            return {
                'success': False,
                'error': str(e)
            }

    def cancel_action_goal(self, goal_id: str) -> Dict[str, Any]:
        """Cancel an active action goal.

        Args:
            goal_id: Goal ID to cancel

        Returns:
            Dictionary with cancellation result
        """
        if goal_id not in self._active_goals:
            return {
                'success': False,
                'error': f'Goal {goal_id} not found in active goals'
            }

        goal_info = self._active_goals[goal_id]
        action_name = goal_info['action_name']

        try:
            client = self._action_clients.get(action_name)
            if not client:
                return {
                    'success': False,
                    'error': f'Action client for {action_name} not found'
                }

            # Cancel goal
            cancel_future = client.cancel_goal_async(goal_info.get('goal_handle'))
            rclpy.spin_once(self._node, timeout_sec=1.0)

            goal_info['status'] = 'CANCELING'

            return {
                'success': True,
                'goal_id': goal_id,
                'action_name': action_name,
                'status': 'CANCELING',
                'note': 'Cancel request sent'
            }

        except Exception as e:
            logger.error(f'Cancel goal failed: {e}')
            return {
                'success': False,
                'error': str(e)
            }

    def get_action_result(self, goal_id: str, timeout: float = 10.0) -> Dict[str, Any]:
        """Get result of an action goal.

        Args:
            goal_id: Goal ID to get result for
            timeout: Timeout to wait for result

        Returns:
            Dictionary with action result
        """
        if goal_id not in self._active_goals:
            return {
                'success': False,
                'error': f'Goal {goal_id} not found'
            }

        goal_info = self._active_goals[goal_id]

        # Wait for result if still active
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = goal_info.get('status')
            if status in ['SUCCEEDED', 'ABORTED', 'CANCELED']:
                break
            rclpy.spin_once(self._node, timeout_sec=0.1)

        result = {
            'success': True,
            'goal_id': goal_id,
            'action_name': goal_info['action_name'],
            'action_type': goal_info['action_type'],
            'status': goal_info.get('status', 'UNKNOWN'),
            'elapsed_time': time.time() - goal_info.get('start_time', 0),
            'feedback_count': len(goal_info.get('feedback', [])),
        }

        if 'result' in goal_info:
            result['result'] = goal_info['result']

        return result

    def _goal_response_callback(self, goal_id: str, future):
        """Handle goal response."""
        goal_handle = future.result()
        if not goal_handle.accepted:
            logger.warning(f'Goal {goal_id} was rejected')
            if goal_id in self._active_goals:
                self._active_goals[goal_id]['status'] = 'REJECTED'
            return

        logger.info(f'Goal {goal_id} accepted')
        if goal_id in self._active_goals:
            self._active_goals[goal_id]['status'] = 'ACCEPTED'
            self._active_goals[goal_id]['goal_handle'] = goal_handle

        # Get result asynchronously
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda future: self._get_result_callback(goal_id, future)
        )

    def _get_result_callback(self, goal_id: str, future):
        """Handle result callback."""
        try:
            result = future.result()
            if goal_id in self._active_goals:
                self._active_goals[goal_id]['status'] = 'SUCCEEDED'
                # Convert result to dict
                result_msg = result.result
                result_dict = {}
                for slot in result_msg.__slots__:
                    val = getattr(result_msg, slot)
                    if isinstance(val, (str, int, float, bool, list, dict, type(None))):
                        result_dict[slot] = val
                    else:
                        result_dict[slot] = str(val)
                self._active_goals[goal_id]['result'] = result_dict
                logger.info(f'Goal {goal_id} completed with result')
        except Exception as e:
            logger.error(f'Goal {goal_id} failed: {e}')
            if goal_id in self._active_goals:
                self._active_goals[goal_id]['status'] = 'ABORTED'
                self._active_goals[goal_id]['error'] = str(e)

    def _feedback_callback(self, goal_id: str, feedback_msg, user_callback=None):
        """Handle feedback."""
        if goal_id in self._active_goals:
            self._active_goals[goal_id]['status'] = 'EXECUTING'
            # Convert feedback to dict
            feedback_dict = {}
            fb_msg = feedback_msg.feedback
            for slot in fb_msg.__slots__:
                val = getattr(fb_msg, slot)
                if isinstance(val, (str, int, float, bool, list, dict, type(None))):
                    feedback_dict[slot] = val
                else:
                    feedback_dict[slot] = str(val)

            self._active_goals[goal_id]['feedback'].append({
                'timestamp': time.time(),
                'data': feedback_dict
            })

            if user_callback:
                try:
                    user_callback(feedback_dict)
                except Exception as e:
                    logger.error(f'Feedback callback error: {e}')

    def _set_message_fields(self, msg: Any, data: Dict[str, Any]):
        """Set message fields from dictionary."""
        for key, value in data.items():
            if hasattr(msg, key):
                attr = getattr(msg, key)
                # Handle nested messages
                if hasattr(attr, '__slots__'):
                    self._set_message_fields(attr, value)
                else:
                    setattr(msg, key, value)

    def get_active_goals(self) -> List[Dict[str, Any]]:
        """Get list of active goals.

        Returns:
            List of active goal information
        """
        active = []
        for goal_id, info in self._active_goals.items():
            if info['status'] in ['PENDING', 'ACCEPTED', 'EXECUTING', 'CANCELING']:
                active.append({
                    'goal_id': goal_id,
                    'action_name': info['action_name'],
                    'action_type': info['action_type'],
                    'status': info['status'],
                    'elapsed_time': time.time() - info.get('start_time', 0)
                })
        return active

    # =========================================================================
    # Generic Topic Publisher
    # =========================================================================

    def publish_topic(
        self,
        topic: str,
        msg_type_str: str,
        data: Dict[str, Any],
        qos_depth: int = 10,
    ) -> Dict[str, Any]:
        """Publish a message to any ROS topic (fire-and-forget).

        Dynamically imports the message class, caches one publisher per topic,
        and populates fields recursively from a dict — same pattern as call_service.

        Args:
            topic: Full topic name (e.g. '/orbibot/exploration/command').
            msg_type_str: Message type string in any of these formats:
                'std_msgs/msg/String', 'std_msgs/String', 'std_msgs.msg.String'.
            data: Dict of message fields. Nested messages use nested dicts.
            qos_depth: Publisher QoS history depth (default 10).

        Returns:
            Status dict with 'success' and 'topic'.
        """
        try:
            import importlib
            # Normalise type string: accept '/', '.', mixed
            # Support: 'pkg/msg/Type', 'pkg/Type', 'pkg.msg.Type'
            parts = msg_type_str.replace('.', '/').split('/')
            if len(parts) == 3 and parts[1] == 'msg':
                pkg, _, cls_name = parts
            elif len(parts) == 2:
                pkg, cls_name = parts
            else:
                return {'success': False,
                        'error': f'Invalid msg_type format: {msg_type_str}'}

            mod = importlib.import_module(f'{pkg}.msg')
            msg_class = getattr(mod, cls_name)

            if topic not in self._topic_publishers:
                self._topic_publishers[topic] = self._node.create_publisher(
                    msg_class, topic, qos_depth
                )
                logger.info(f'Created publisher for {topic} ({msg_type_str})')

            pub = self._topic_publishers[topic]
            msg = msg_class()
            self._set_message_fields(msg, data)
            pub.publish(msg)
            logger.info(f'Published to {topic}: {data}')
            return {'success': True, 'topic': topic, 'msg_type': msg_type_str}

        except ImportError as e:
            logger.error(f'Cannot import {msg_type_str}: {e}')
            return {'success': False, 'error': f'Cannot import {msg_type_str}: {e}'}
        except Exception as e:
            logger.error(f'publish_topic failed: {e}')
            return {'success': False, 'error': str(e)}

    # =========================================================================
    # SLAM Methods
    # =========================================================================

    def slam_save_map(self, path: str) -> Dict[str, Any]:
        """Save the current SLAM map (pose graph + nav2 pgm/yaml).

        Calls /slam_toolbox/save_map with the correct nested field structure.
        The slam_toolbox node saves both <path>.posegraph/.data and
        triggers map_saver to write <path>.pgm + <path>.yaml.

        Args:
            path: Absolute path without extension (e.g. '/home/orbibot/maps/my_map').

        Returns:
            Service response dict.
        """
        return self.call_service(
            '/slam_toolbox/save_map',
            'slam_toolbox/srv/SaveMap',
            {'name': {'data': str(path)}},
            timeout=10.0,
        )

    def slam_serialize_map(self, path: str) -> Dict[str, Any]:
        """Serialize the SLAM pose graph to disk for later localization-mode reload.

        Args:
            path: Absolute path without extension.

        Returns:
            Service response dict.
        """
        return self.call_service(
            '/slam_toolbox/serialize_map',
            'slam_toolbox/srv/SerializePoseGraph',
            {'filename': {'data': str(path)}},
            timeout=10.0,
        )

    def slam_get_map_info(self) -> Optional[Dict[str, Any]]:
        """Get current map dimensions, resolution, and exploration coverage.

        Returns:
            Dict with width_cells, height_cells, resolution_m, origin_x, origin_y,
            total_cells, free_cells, occupied_cells, unknown_cells, explored_pct.
        """
        try:
            map_qos = QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                depth=1,
            )
            msg = self.wait_for_message(OccupancyGrid, '/map', timeout=5.0, qos=map_qos)
            if msg is None:
                return None

            width = msg.info.width
            height = msg.info.height
            resolution = msg.info.resolution
            data = msg.data

            total = len(data)
            free = sum(1 for v in data if v == 0)
            occupied = sum(1 for v in data if v > 0)
            unknown = sum(1 for v in data if v < 0)
            explored_pct = round((free + occupied) / max(total, 1) * 100, 1)

            return {
                'width_cells': width,
                'height_cells': height,
                'width_m': round(width * resolution, 2),
                'height_m': round(height * resolution, 2),
                'resolution_m': round(resolution, 4),
                'origin': {
                    'x': round(msg.info.origin.position.x, 3),
                    'y': round(msg.info.origin.position.y, 3),
                },
                'total_cells': total,
                'free_cells': free,
                'occupied_cells': occupied,
                'unknown_cells': unknown,
                'explored_pct': explored_pct,
            }
        except Exception as e:
            logger.error(f'slam_get_map_info failed: {e}')
            return None

    # =========================================================================
    # Navigation / AMCL Methods
    # =========================================================================

    @staticmethod
    def _yaw_to_quaternion(yaw_deg: float) -> Dict[str, float]:
        """Convert yaw in degrees to a quaternion dict (z-axis rotation only)."""
        yaw = math.radians(yaw_deg)
        return {
            'x': 0.0,
            'y': 0.0,
            'z': round(math.sin(yaw / 2.0), 6),
            'w': round(math.cos(yaw / 2.0), 6),
        }

    def set_initial_pose(
        self,
        x: float,
        y: float,
        yaw_deg: float = 0.0,
        frame_id: str = 'map',
    ) -> Dict[str, Any]:
        """Set the AMCL initial pose estimate.

        Publishes a PoseWithCovarianceStamped to /initialpose so AMCL
        re-centres its particle filter. Use when you know roughly where
        the robot is on the map (e.g. after moving it manually).

        Args:
            x: X position in map frame (metres).
            y: Y position in map frame (metres).
            yaw_deg: Heading in degrees (0 = facing +X).
            frame_id: Coordinate frame (default 'map').

        Returns:
            Status dict.
        """
        q = self._yaw_to_quaternion(yaw_deg)
        # 5 cm position covariance diagonal, 0.069 rad² yaw covariance (~15 deg)
        cov = [0.0] * 36
        cov[0] = 0.25    # x variance
        cov[7] = 0.25    # y variance
        cov[35] = 0.069  # yaw variance

        result = self.publish_topic(
            '/initialpose',
            'geometry_msgs/msg/PoseWithCovarianceStamped',
            {
                'header': {'frame_id': frame_id},
                'pose': {
                    'pose': {
                        'position': {'x': float(x), 'y': float(y), 'z': 0.0},
                        'orientation': q,
                    },
                    'covariance': cov,
                },
            },
        )
        if result.get('success'):
            logger.info(f'Published initial pose: x={x}, y={y}, yaw={yaw_deg}°')
        return result

    def navigate_to_pose(
        self,
        x: float,
        y: float,
        yaw_deg: float = 0.0,
        frame_id: str = 'map',
        timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Send a navigation goal to Nav2 NavigateToPose action.

        Constructs the full nested PoseStamped goal structure and dispatches
        via send_action_goal. Returns immediately with goal_id; use
        ros2_action_request_result to poll for completion.

        Args:
            x: Target X in map frame (metres).
            y: Target Y in map frame (metres).
            yaw_deg: Target heading in degrees (0 = facing +X).
            frame_id: Coordinate frame (default 'map').
            timeout: Seconds to wait for goal acceptance (default 120).

        Returns:
            Dict with goal_id and status.
        """
        q = self._yaw_to_quaternion(yaw_deg)
        goal = {
            'pose': {
                'header': {'frame_id': frame_id},
                'pose': {
                    'position': {'x': float(x), 'y': float(y), 'z': 0.0},
                    'orientation': q,
                },
            }
        }
        return self.send_action_goal(
            '/navigate_to_pose',
            'nav2_msgs/action/NavigateToPose',
            goal,
            timeout=timeout,
        )

    def navigate_through_poses(
        self,
        poses: List[Dict[str, float]],
        frame_id: str = 'map',
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """Navigate through an ordered list of poses.

        Args:
            poses: List of dicts with 'x', 'y', and optional 'yaw_deg' (default 0).
            frame_id: Coordinate frame (default 'map').
            timeout: Seconds to wait for goal acceptance.

        Returns:
            Dict with goal_id and status.
        """
        pose_list = []
        for p in poses:
            q = self._yaw_to_quaternion(float(p.get('yaw_deg', 0.0)))
            pose_list.append({
                'header': {'frame_id': frame_id},
                'pose': {
                    'position': {'x': float(p['x']), 'y': float(p['y']), 'z': 0.0},
                    'orientation': q,
                },
            })
        return self.send_action_goal(
            '/navigate_through_poses',
            'nav2_msgs/action/NavigateThroughPoses',
            {'poses': pose_list},
            timeout=timeout,
        )

    def follow_waypoints(
        self,
        waypoints: List[Dict[str, float]],
        frame_id: str = 'map',
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """Follow an ordered list of waypoints sequentially.

        The robot visits each waypoint in order. If one is unreachable the
        Nav2 behaviour tree will try the next one.

        Args:
            waypoints: List of dicts with 'x', 'y', optional 'yaw_deg' (default 0).
            frame_id: Coordinate frame (default 'map').
            timeout: Seconds to wait for goal acceptance.

        Returns:
            Dict with goal_id and status.
        """
        pose_list = []
        for wp in waypoints:
            q = self._yaw_to_quaternion(float(wp.get('yaw_deg', 0.0)))
            pose_list.append({
                'header': {'frame_id': frame_id},
                'pose': {
                    'position': {'x': float(wp['x']), 'y': float(wp['y']), 'z': 0.0},
                    'orientation': q,
                },
            })
        return self.send_action_goal(
            '/follow_waypoints',
            'nav2_msgs/action/FollowWaypoints',
            {'poses': pose_list},
            timeout=timeout,
        )

    def nav_cancel(self) -> Dict[str, Any]:
        """Cancel all active Nav2 navigation goals.

        Returns:
            Status dict.
        """
        result = self.call_service(
            '/navigate_to_pose/_action/cancel_all_goals',
            'action_msgs/srv/CancelGoal',
            {},
            timeout=5.0,
        )
        # Also cancel any tracked goals in our registry
        for goal_id, info in list(self._active_goals.items()):
            if info['status'] in ('PENDING', 'ACCEPTED', 'EXECUTING'):
                self.cancel_action_goal(goal_id)
        return result

    def nav_clear_costmaps(self, which: str = 'both') -> Dict[str, Any]:
        """Clear Nav2 local and/or global costmaps.

        Args:
            which: 'local', 'global', or 'both' (default 'both').

        Returns:
            Combined result dict.
        """
        results = {}
        which = which.lower()

        if which in ('local', 'both'):
            results['local'] = self.call_service(
                '/local_costmap/clear_entirely_local_costmap',
                'nav2_msgs/srv/ClearEntireCostmap',
                {},
                timeout=5.0,
            )

        if which in ('global', 'both'):
            results['global'] = self.call_service(
                '/global_costmap/clear_entirely_global_costmap',
                'nav2_msgs/srv/ClearEntireCostmap',
                {},
                timeout=5.0,
            )

        all_ok = all(r.get('success') for r in results.values())
        return {'success': all_ok, 'cleared': which, 'details': results}

    def nav_get_plan(self) -> Optional[Dict[str, Any]]:
        """Get the current Nav2 planned path from /plan topic.

        Returns:
            Dict with waypoint count, start and end coordinates, or None.
        """
        try:
            msg = self.wait_for_message(Path, '/plan', timeout=3.0)
            if msg is None or not msg.poses:
                return {'waypoint_count': 0, 'note': 'No active plan'}

            start = msg.poses[0].pose.position
            end = msg.poses[-1].pose.position
            return {
                'waypoint_count': len(msg.poses),
                'frame_id': msg.header.frame_id,
                'start': {'x': round(start.x, 3), 'y': round(start.y, 3)},
                'end': {'x': round(end.x, 3), 'y': round(end.y, 3)},
            }
        except Exception as e:
            logger.error(f'nav_get_plan failed: {e}')
            return None

    def amcl_reinitialize(self) -> Dict[str, Any]:
        """Trigger global AMCL relocalization (scatter particles across whole map).

        Use when the robot is completely lost and you want AMCL to search
        the entire map. After calling, drive the robot a bit so particles converge.

        Returns:
            Service response dict.
        """
        return self.call_service(
            '/amcl/reinitialize_global_localization',
            'std_srvs/srv/Empty',
            {},
            timeout=5.0,
        )

    def nav_spin(
        self,
        angle_rad: float,
        time_allowance_sec: float = 10.0,
    ) -> Dict[str, Any]:
        """In-place rotation recovery using Nav2 Spin action.

        Args:
            angle_rad: Target rotation in radians (positive = CCW).
            time_allowance_sec: Time budget for the spin (default 10 s).

        Returns:
            Dict with goal_id and status.
        """
        return self.send_action_goal(
            '/spin',
            'nav2_msgs/action/Spin',
            {
                'target_yaw': float(angle_rad),
                'time_allowance': {'sec': int(time_allowance_sec), 'nanosec': 0},
            },
            timeout=time_allowance_sec + 5.0,
        )

    def nav_backup(
        self,
        distance_m: float = 0.15,
        speed_mps: float = 0.025,
        time_allowance_sec: float = 10.0,
    ) -> Dict[str, Any]:
        """Drive backward a short distance using Nav2 BackUp action.

        Args:
            distance_m: Distance to reverse in metres (default 0.15).
            speed_mps: Backup speed in m/s (default 0.025).
            time_allowance_sec: Time budget (default 10 s).

        Returns:
            Dict with goal_id and status.
        """
        return self.send_action_goal(
            '/backup',
            'nav2_msgs/action/BackUp',
            {
                'target': {'x': float(distance_m), 'y': 0.0, 'z': 0.0},
                'speed': float(speed_mps),
                'time_allowance': {'sec': int(time_allowance_sec), 'nanosec': 0},
            },
            timeout=time_allowance_sec + 5.0,
        )

    # =========================================================================
    # Exploration Methods
    # =========================================================================

    def exploration_command(self, cmd: str) -> Dict[str, Any]:
        """Send a command to the frontier exploration node.

        Args:
            cmd: One of 'start', 'stop', 'pause', 'resume'.

        Returns:
            Status dict.
        """
        valid = {'start', 'stop', 'pause', 'resume'}
        cmd = cmd.strip().lower()
        if cmd not in valid:
            return {
                'success': False,
                'error': f'Invalid command "{cmd}". Valid: {sorted(valid)}',
            }
        return self.publish_topic(
            '/orbibot/exploration/command',
            'std_msgs/msg/String',
            {'data': cmd},
        )

    def get_exploration_status(self) -> Optional[Dict[str, Any]]:
        """Get the current exploration state.

        Returns:
            Dict with status string, or None if unavailable.
        """
        try:
            msg = self.wait_for_message(String, '/orbibot/exploration/status', timeout=3.0)
            if msg is None:
                return None
            return {'status': msg.data}
        except Exception as e:
            logger.error(f'get_exploration_status failed: {e}')
            return None

    def get_exploration_frontiers(self) -> Optional[Dict[str, Any]]:
        """Get the current frontier list from the exploration node.

        Returns:
            Dict with frontier count and list of {x, y} centroids, or None.
        """
        try:
            msg = self.wait_for_message(
                MarkerArray, '/orbibot/exploration/frontiers', timeout=3.0
            )
            if msg is None:
                return None

            centroids = []
            for marker in msg.markers:
                if marker.type == 8:  # POINTS marker (frontier cells)
                    continue
                # SPHERE markers (id >= 1000) are centroids
                centroids.append({
                    'x': round(marker.pose.position.x, 3),
                    'y': round(marker.pose.position.y, 3),
                })

            return {
                'frontier_count': len(centroids),
                'frontiers': centroids,
                'note': 'Each frontier is an unexplored region centroid in map frame',
            }
        except Exception as e:
            logger.error(f'get_exploration_frontiers failed: {e}')
            return None