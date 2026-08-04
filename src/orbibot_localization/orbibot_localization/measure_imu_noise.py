#!/usr/bin/env python3
"""
Stationary IMU characterisation for OrbiBot — noise, bias and yaw drift.

Subscribes to `/imu/data_raw`, `/imu/data_filtered` and `/odom` while the robot
sits still, and reports the three numbers Phase 4 needs:

* **Per-axis variance** — what goes in `hardware_params.yaml` as the IMU
  covariance the EKF weights the sensor by.
* **Gyro bias** — the mean angular rate of a robot that is not turning. With
  `use_mag: false` this is the single number that decides how fast heading
  rots, and it is what Madgwick's `zeta` exists to chase. The tool used to
  compute this mean and never print it.
* **Yaw drift** — measured on `/imu/data_filtered`, in degrees per minute, over
  the whole run. This is the number that replaced the magnetometer
  (roadmap 1.3), and a bias figure alone cannot predict it because Madgwick's
  accelerometer correction fights the bias in roll and pitch but not in yaw.

`/odom` is watched too: a stationary robot should report zero twist, and any
residual is encoder noise that the EKF will otherwise integrate.

Usage:
  1. Put the robot somewhere flat and still — it does not need to be elevated,
     and no motion is commanded. Motors are never armed.
  2. `ros2 run orbibot_localization measure_imu_noise --ros-args -p duration:=600.0`
  3. Do not touch, bump or lean on the robot until it finishes.
  4. Paste the printed block into `hardware_params.yaml`, and the summary into
     `test-report.md` with the date and the robot's state.

Why per-axis: ICM-20948 axes differ through manufacturing tolerance and PCB
mounting, so one shared variance over-trusts the noisy axis and under-trusts
the quiet one.

**Ten minutes beats thirty seconds.** The covariances this replaced were taken
from 212 samples in 2026-03-24 — before the IMU register misconfiguration was
found and before the magnetometer was removed. Bias and drift are slow effects;
a 30 s window cannot see them at all.
"""

import math
import signal
import sys
from datetime import datetime

import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu

DEFAULT_DURATION_S = 600.0
MIN_USEFUL_SAMPLES = 50
PROGRESS_INTERVAL_S = 30.0
RAD_TO_DEG = 180.0 / math.pi
GRAVITY = 9.80665


class WelfordAccumulator:
    """Single-pass mean and variance using Welford's algorithm."""

    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0

    def update(self, value: float) -> None:
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (value - self.mean)

    @property
    def variance(self) -> float:
        return self.m2 / self.n if self.n > 1 else 0.0

    @property
    def stddev(self) -> float:
        return math.sqrt(self.variance)


class YawTracker:
    """Accumulates unwrapped yaw so drift past ±180° still reads correctly."""

    def __init__(self):
        self.first = None
        self.last = None
        self.unwrapped = 0.0
        self._previous = None
        self.n = 0

    def update(self, yaw: float) -> None:
        """Add one yaw sample in radians, unwrapping across the ±π seam."""
        self.n += 1
        if self._previous is None:
            self.first = yaw
            self.unwrapped = yaw
        else:
            delta = yaw - self._previous
            # A real robot standing still never turns half a circle between two
            # samples at 50 Hz, so a jump that large is the seam, not motion.
            if delta > math.pi:
                delta -= 2.0 * math.pi
            elif delta < -math.pi:
                delta += 2.0 * math.pi
            self.unwrapped += delta
        self._previous = yaw
        self.last = yaw

    @property
    def total_drift_rad(self) -> float:
        if self.first is None:
            return 0.0
        return self.unwrapped - self.first


def quaternion_to_yaw(q) -> float:
    """Yaw in radians from a geometry_msgs Quaternion (ROS ENU convention)."""
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class ImuNoiseMeasurer(Node):
    """Collects stationary IMU statistics and prints a paste-ready block."""

    def __init__(self):
        super().__init__('imu_noise_measurer')

        self.declare_parameter('duration', DEFAULT_DURATION_S)
        self.declare_parameter('output', '')
        self._duration = self.get_parameter('duration').value
        self._output_path = self.get_parameter('output').value

        self._accel = [WelfordAccumulator() for _ in range(3)]
        self._gyro = [WelfordAccumulator() for _ in range(3)]
        self._odom_twist = [WelfordAccumulator() for _ in range(3)]
        self._yaw = YawTracker()
        self._finished = False

        self.create_subscription(
            Imu, '/imu/data_raw', self._imu_raw_callback, qos_profile_sensor_data)
        self.create_subscription(
            Imu, '/imu/data_filtered', self._imu_filtered_callback,
            qos_profile_sensor_data)
        self.create_subscription(Odometry, '/odom', self._odom_callback, 10)

        self.create_timer(PROGRESS_INTERVAL_S, self._print_progress)
        self._start_time = self.get_clock().now()
        self._started_wall = datetime.now()

        self.get_logger().info('=' * 64)
        self.get_logger().info('[Localization] Stationary IMU characterisation — '
                               f'noise, bias, yaw drift over {self._duration:.0f} s')
        self.get_logger().info('Keep the robot STILL and LEVEL. No motion is commanded.')
        self.get_logger().info('Ctrl+C stops early and still reports what it has.')
        self.get_logger().info('=' * 64)

    def _elapsed(self) -> float:
        return (self.get_clock().now() - self._start_time).nanoseconds / 1e9

    def _imu_raw_callback(self, msg: Imu) -> None:
        if self._elapsed() > self._duration:
            self._finish()
            return
        self._accel[0].update(msg.linear_acceleration.x)
        self._accel[1].update(msg.linear_acceleration.y)
        self._accel[2].update(msg.linear_acceleration.z)
        self._gyro[0].update(msg.angular_velocity.x)
        self._gyro[1].update(msg.angular_velocity.y)
        self._gyro[2].update(msg.angular_velocity.z)

    def _imu_filtered_callback(self, msg: Imu) -> None:
        if self._elapsed() > self._duration:
            return
        self._yaw.update(quaternion_to_yaw(msg.orientation))

    def _odom_callback(self, msg: Odometry) -> None:
        if self._elapsed() > self._duration:
            return
        self._odom_twist[0].update(msg.twist.twist.linear.x)
        self._odom_twist[1].update(msg.twist.twist.linear.y)
        self._odom_twist[2].update(msg.twist.twist.angular.z)

    def _print_progress(self) -> None:
        n = self._accel[0].n
        remaining = max(0.0, self._duration - self._elapsed())
        if n < 10:
            self.get_logger().warn(
                f'Only {n} samples — is /imu/data_raw publishing?')
            return
        drift_deg = self._yaw.total_drift_rad * RAD_TO_DEG
        self.get_logger().info(
            f'{n} samples | gyro Z bias {self._gyro[2].mean * RAD_TO_DEG:+.4f} °/s | '
            f'yaw drift {drift_deg:+.2f}° | {remaining / 60.0:.1f} min left')

    def _finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        self.report()
        raise SystemExit(0)

    def report(self) -> None:
        """Print the full result, and write it to a file if one was asked for."""
        n = self._accel[0].n
        if n < MIN_USEFUL_SAMPLES:
            self.get_logger().warn(
                f'Only {n} samples — not enough to report. Is /imu/data_raw up?')
            return

        text = self._format_report(n)
        print(text)

        if self._output_path:
            try:
                with open(self._output_path, 'w') as handle:
                    handle.write(text)
                print(f'\nWritten to {self._output_path}')
            except OSError as exc:
                print(f'\nCould not write {self._output_path}: {exc}')

    def _format_report(self, n: int) -> str:
        elapsed = self._elapsed()
        accel_var = [a.variance for a in self._accel]
        gyro_var = [g.variance for g in self._gyro]
        magnitude = math.sqrt(sum(a.mean ** 2 for a in self._accel))

        drift_rad = self._yaw.total_drift_rad
        drift_deg = drift_rad * RAD_TO_DEG
        drift_per_min = drift_deg / (elapsed / 60.0) if elapsed > 0 else 0.0

        axes = ('X', 'Y', 'Z')
        lines = [
            '',
            '=' * 64,
            'STATIONARY IMU CHARACTERISATION',
            '=' * 64,
            f'Started      {self._started_wall.isoformat(timespec="seconds")}',
            f'Duration     {elapsed:.1f} s ({elapsed / 60.0:.1f} min)',
            f'Samples      {n} raw, {self._yaw.n} filtered, '
            f'{self._odom_twist[0].n} odom',
            '',
            '-- Accelerometer ---------------------------------------------',
            'axis        mean (m/s²)     stddev        variance (m/s²)²',
        ]
        for i, axis in enumerate(axes):
            lines.append(f'  {axis}     {self._accel[i].mean:+12.5f}  '
                         f'{self._accel[i].stddev:11.5f}   {accel_var[i]:.6e}')
        lines += [
            f'  |a| = {magnitude:.4f} m/s²   ratio to g = {magnitude / GRAVITY:.4f}',
            '  (X and Y near 0 and Z near +9.81 means the robot is level.',
            '   A ratio far from 1.000 is a scale error, not noise — CC-2.)',
            '',
            '-- Gyroscope -------------------------------------------------',
            'axis     bias (rad/s)     bias (°/s)     stddev (rad/s)   variance',
        ]
        for i, axis in enumerate(axes):
            lines.append(
                f'  {axis}   {self._gyro[i].mean:+13.6f}  '
                f'{self._gyro[i].mean * RAD_TO_DEG:+12.5f}   '
                f'{self._gyro[i].stddev:13.6f}   {gyro_var[i]:.6e}')

        lines += [
            '',
            '  Gyro Z bias is the one that matters: with use_mag=false nothing',
            '  observes heading, so this bias integrates into yaw drift.',
            f'  Predicted from bias alone: '
            f'{self._gyro[2].mean * RAD_TO_DEG * 60.0:+.3f} °/min',
            '',
            '-- Yaw drift, measured on /imu/data_filtered -----------------',
        ]
        if self._yaw.n < MIN_USEFUL_SAMPLES:
            lines.append('  NOT MEASURED — /imu/data_filtered had no data. Is the '
                         'Madgwick filter running?')
        else:
            lines += [
                f'  total drift over {elapsed / 60.0:.1f} min : {drift_deg:+.3f}°',
                f'  drift rate                : {drift_per_min:+.3f} °/min',
                '',
                '  Compare against the bias prediction above. Close agreement',
                '  means Madgwick is not correcting yaw at all (expected with',
                '  zeta: 0.0). A much smaller measured drift means zeta or the',
                '  accelerometer correction is doing more than assumed.',
            ]

        lines += [
            '',
            '-- /odom while stationary ------------------------------------',
        ]
        if self._odom_twist[0].n < 5:
            lines.append('  NOT MEASURED — no /odom messages.')
        else:
            for i, name in enumerate(('vx (m/s)  ', 'vy (m/s)  ', 'vyaw (rad/s)')):
                lines.append(
                    f'  {name}  mean {self._odom_twist[i].mean:+.6f}   '
                    f'stddev {self._odom_twist[i].stddev:.6f}')
            lines.append('  A stationary robot should read zero. Anything here is '
                         'encoder noise the EKF integrates.')

        lines += [
            '',
            '-- Paste into hardware_params.yaml, imu: ---------------------',
            f'      accel_covariance_x: {accel_var[0]:.6e}  # measured '
            f'{self._started_wall.date().isoformat()}, {n} samples, stationary',
            f'      accel_covariance_y: {accel_var[1]:.6e}',
            f'      accel_covariance_z: {accel_var[2]:.6e}',
            f'      gyro_covariance_x: {gyro_var[0]:.6e}',
            f'      gyro_covariance_y: {gyro_var[1]:.6e}',
            f'      gyro_covariance_z: {gyro_var[2]:.6e}',
            '',
            'Scientific notation is deliberate: the previous values were written',
            'to six decimal places, where a gyro variance of 1e-7 and one of',
            '1.4e-6 both print as 0.000001.',
            '=' * 64,
            '',
        ]
        return '\n'.join(lines)


def main():
    rclpy.init()
    node = ImuNoiseMeasurer()

    def shutdown(signum, frame):
        node.report()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    sys.exit(0)


if __name__ == '__main__':
    main()
