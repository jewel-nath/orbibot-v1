#!/usr/bin/env python3
"""
IMU Noise Variance Measurement for OrbiBot

Subscribes to /imu/data_raw for N seconds while the robot is stationary,
computes per-axis variance for accelerometer and gyroscope, and prints
values ready to paste into hardware_params.yaml.

Usage:
  1. Place robot on a flat, still surface
  2. ros2 run orbibot_localization measure_imu_noise
  3. Wait 30 seconds (default) — do NOT touch the robot
  4. Copy printed values into hardware_params.yaml (imu section)

Why per-axis?
  ICM-20948 axes have slightly different noise characteristics due to
  manufacturing tolerances and PCB mounting. lgdxrobot2 firmware measures
  per-axis variance at startup; this script does the same on the ROS2 side.
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu
import math
import signal
import sys


# Welford's online algorithm for numerically stable variance computation
class WelfordAccumulator:
    """Single-pass variance using Welford's algorithm (no large arrays needed)."""

    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0

    def update(self, value):
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        delta2 = value - self.mean
        self.m2 += delta * delta2

    @property
    def variance(self):
        return self.m2 / self.n if self.n > 1 else 0.0

    @property
    def stddev(self):
        return math.sqrt(self.variance)


class ImuNoiseMeasurer(Node):
    def __init__(self):
        super().__init__('imu_noise_measurer')

        self.declare_parameter('duration', 30.0)
        self._duration = self.get_parameter('duration').value

        # Per-axis accumulators
        self._accel = [WelfordAccumulator() for _ in range(3)]
        self._gyro = [WelfordAccumulator() for _ in range(3)]

        self._sub = self.create_subscription(
            Imu, '/imu/data_raw', self._imu_callback, qos_profile_sensor_data
        )

        self._timer = self.create_timer(2.0, self._print_progress)
        self._start_time = self.get_clock().now()

        self.get_logger().info('=' * 60)
        self.get_logger().info('IMU Noise Variance Measurement')
        self.get_logger().info(f'Duration: {self._duration:.0f}s — keep robot STILL and LEVEL')
        self.get_logger().info('Press Ctrl+C to stop early')
        self.get_logger().info('=' * 60)

    def _imu_callback(self, msg: Imu):
        elapsed = (self.get_clock().now() - self._start_time).nanoseconds / 1e9
        if elapsed > self._duration:
            self._finish()
            return

        self._accel[0].update(msg.linear_acceleration.x)
        self._accel[1].update(msg.linear_acceleration.y)
        self._accel[2].update(msg.linear_acceleration.z)
        self._gyro[0].update(msg.angular_velocity.x)
        self._gyro[1].update(msg.angular_velocity.y)
        self._gyro[2].update(msg.angular_velocity.z)

    def _print_progress(self):
        n = self._accel[0].n
        elapsed = (self.get_clock().now() - self._start_time).nanoseconds / 1e9
        remaining = max(0, self._duration - elapsed)
        if n < 10:
            self.get_logger().info(f'Waiting for data... ({n} samples)')
        else:
            self.get_logger().info(
                f'Samples: {n} | '
                f'Accel var: [{self._accel[0].variance:.6f}, {self._accel[1].variance:.6f}, {self._accel[2].variance:.6f}] | '
                f'{remaining:.0f}s left'
            )

    def _finish(self):
        self.print_result()
        raise SystemExit(0)

    def print_result(self):
        n = self._accel[0].n
        if n < 50:
            self.get_logger().warn(f'Only {n} samples — not enough. Run longer or check /imu/data_raw.')
            return

        # Compute per-axis variances
        accel_var = [a.variance for a in self._accel]
        gyro_var = [g.variance for g in self._gyro]

        print('\n' + '=' * 60)
        print('IMU NOISE MEASUREMENT RESULT')
        print('=' * 60)
        print(f'Total samples: {n}')
        print()
        print('Accelerometer variance (m/s²)²:')
        print(f'  X: {accel_var[0]:.6f}  (stddev: {self._accel[0].stddev:.4f} m/s²)')
        print(f'  Y: {accel_var[1]:.6f}  (stddev: {self._accel[1].stddev:.4f} m/s²)')
        print(f'  Z: {accel_var[2]:.6f}  (stddev: {self._accel[2].stddev:.4f} m/s²)')
        print()
        print('Gyroscope variance (rad/s)²:')
        print(f'  X: {gyro_var[0]:.6f}  (stddev: {self._gyro[0].stddev:.4f} rad/s)')
        print(f'  Y: {gyro_var[1]:.6f}  (stddev: {self._gyro[1].stddev:.4f} rad/s)')
        print(f'  Z: {gyro_var[2]:.6f}  (stddev: {self._gyro[2].stddev:.4f} rad/s)')
        print()
        print('Accel mean (sanity check — X,Y~0, Z~9.81):')
        print(f'  X: {self._accel[0].mean:.4f}  Y: {self._accel[1].mean:.4f}  Z: {self._accel[2].mean:.4f}')
        print()
        print('Copy to hardware_params.yaml (imu section):')
        print(f'      accel_covariance_x: {accel_var[0]:.6f}')
        print(f'      accel_covariance_y: {accel_var[1]:.6f}')
        print(f'      accel_covariance_z: {accel_var[2]:.6f}')
        print(f'      gyro_covariance_x: {gyro_var[0]:.6f}')
        print(f'      gyro_covariance_y: {gyro_var[1]:.6f}')
        print(f'      gyro_covariance_z: {gyro_var[2]:.6f}')
        print('=' * 60)


def main():
    rclpy.init()
    node = ImuNoiseMeasurer()

    def shutdown(sig, frame):
        node.print_result()
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == '__main__':
    main()
