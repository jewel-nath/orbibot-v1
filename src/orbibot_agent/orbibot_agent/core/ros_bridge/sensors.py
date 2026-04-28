"""Sensor data reading — battery, IMU, encoders, odometry, LiDAR, etc.

Magnetometer support was removed 2026-04-28 — see firmware-changelog.md.
"""

import logging
import math
import threading
import time
from typing import Any, Dict, List, Optional

from nav_msgs.msg import Odometry
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import Imu, JointState, LaserScan
from std_msgs.msg import Int32MultiArray

from orbibot_msgs.msg import SafetyStatus, SystemStatus

logger = logging.getLogger(__name__)


class SensorsMixin:
    """Read-only sensor data from ROS topics."""

    def get_battery_status(self) -> Optional[Dict[str, Any]]:
        """Get battery voltage and level from system_status topic."""
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

            return {'voltage': round(voltage, 2), 'status': level}
        except Exception as e:
            logger.error(f'Failed to get battery status: {e}')
            return None

    def get_imu_data(self) -> Optional[Dict[str, Any]]:
        """Get filtered IMU orientation (roll, pitch, yaw) and angular velocities."""
        try:
            msg = self.wait_for_message(Imu, '/imu/data')
            if msg is None:
                return None

            o = msg.orientation
            yaw = self._quat_to_yaw(o)

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

    def get_imu_raw(self) -> Optional[Dict[str, Any]]:
        """Get raw IMU data (pre-Madgwick) — gyroscope and accelerometer."""
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

    def get_encoder_counts(self) -> Optional[Dict[str, Any]]:
        """Get raw encoder tick counts [FL, BL, FR, BR]."""
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

    def get_joint_states(self) -> Optional[Dict[str, Any]]:
        """Get wheel joint positions (rad) and velocities (rad/s)."""
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

    def get_odometry(self) -> Optional[Dict[str, Any]]:
        """Get robot odometry (position, yaw, velocity)."""
        try:
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

    def get_safety_status(self) -> Optional[Dict[str, Any]]:
        """Get safety system status (e-stop, faults, battery warnings)."""
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
        """Get enriched system status (CPU%, RAM%, temp, disk, battery)."""
        try:
            msg = self.wait_for_message(SystemStatus, '/orbibot/system_status_enriched')
            if msg is None:
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

    def get_lidar_summary(self) -> Optional[Dict[str, Any]]:
        """Get LiDAR scan summary with obstacle detection."""
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

            front_idx = len(msg.ranges) // 2
            front_range = msg.ranges[front_idx] if front_idx < len(msg.ranges) else float('inf')

            obstacles = []
            for i, r in enumerate(msg.ranges):
                if msg.range_min < r < 0.5:
                    angle = msg.angle_min + i * msg.angle_increment
                    obstacles.append({
                        'angle_deg': round(math.degrees(angle), 1),
                        'distance': round(r, 3),
                    })

            return {
                'point_count': len(msg.ranges),
                'valid_points': len(ranges),
                'min_range': round(min(ranges), 3),
                'max_range': round(max(ranges), 3),
                'avg_range': round(sum(ranges) / len(ranges), 3),
                'front_clearance': round(front_range, 3) if front_range < msg.range_max else 'inf',
                'nearby_obstacles': obstacles[:10],
                'obstacle_count': len(obstacles),
            }
        except Exception as e:
            logger.error(f'Failed to get LiDAR data: {e}')
            return None

    def get_system_status(self) -> Dict[str, Any]:
        """Get system status from /proc (CPU load, RAM, temperature)."""
        result = {}
        try:
            with open('/proc/loadavg', 'r') as f:
                result['cpu_load_1min'] = float(f.read().split()[0])
        except Exception:
            result['cpu_load_1min'] = None

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

        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                result['cpu_temp_c'] = round(int(f.read().strip()) / 1000.0, 1)
        except Exception:
            result['cpu_temp_c'] = None

        battery = self.get_battery_status()
        result['battery'] = battery or {'error': 'Unavailable'}
        return result

    def run_pid_test(
        self,
        vx: float,
        vy: float,
        wz: float,
        duration: float = 5.0,
        sample_hz: float = 20.0,
    ) -> Dict[str, Any]:
        """Run PID test: publish cmd_vel and record /odom velocity response."""
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

        sub = self._node.create_subscription(Odometry, '/odom', _odom_cb, odom_qos)

        samples: List[Dict[str, float]] = []
        t0 = time.perf_counter()
        end_time = t0 + duration
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

        # Downsample if too many points
        if len(samples) > 200:
            step = len(samples) / 200
            samples = [samples[int(i * step)] for i in range(200)]

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

        return {
            'target': {'vx': vx, 'vy': vy, 'wz': wz},
            'duration_sec': round(duration, 1),
            'sample_count': len(samples),
            'metrics': {
                'vx': _metrics([s['vx'] for s in samples], vx),
                'vy': _metrics([s['vy'] for s in samples], vy),
                'wz': _metrics([s['wz'] for s in samples], wz),
            },
            'samples': samples,
        }
