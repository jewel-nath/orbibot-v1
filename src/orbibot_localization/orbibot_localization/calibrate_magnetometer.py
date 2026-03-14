#!/usr/bin/env python3
"""
Magnetometer Hard-Iron Calibration for OrbiBot (ICM-20948)

Usage:
  1. ros2 run orbibot_localization calibrate_magnetometer
  2. Slowly rotate the robot 2-3 full 360° turns (manually or via teleop)
  3. Press Ctrl+C when done
  4. Copy the printed bias values into localization.launch.py

Hard-iron bias = center of the magnetometer ellipse, caused by
nearby permanent magnets (motors, electronics, battery).
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import MagneticField
import sys
import signal


class MagCalibrator(Node):
    def __init__(self):
        super().__init__('mag_calibrator')

        self.min_x = float('inf')
        self.max_x = float('-inf')
        self.min_y = float('inf')
        self.max_y = float('-inf')
        self.min_z = float('inf')
        self.max_z = float('-inf')
        self.count = 0

        self.sub = self.create_subscription(
            MagneticField,
            '/imu/mag',
            self.mag_callback,
            10
        )

        self.timer = self.create_timer(2.0, self.print_status)
        self.get_logger().info('=' * 55)
        self.get_logger().info('Magnetometer Calibration Started')
        self.get_logger().info('Slowly rotate the robot 2-3 full 360° turns')
        self.get_logger().info('Press Ctrl+C when done')
        self.get_logger().info('=' * 55)

    def mag_callback(self, msg: MagneticField):
        x = msg.magnetic_field.x
        y = msg.magnetic_field.y
        z = msg.magnetic_field.z

        # Skip zero/NaN readings
        if x == 0.0 and y == 0.0 and z == 0.0:
            return

        self.min_x = min(self.min_x, x)
        self.max_x = max(self.max_x, x)
        self.min_y = min(self.min_y, y)
        self.max_y = max(self.max_y, y)
        self.min_z = min(self.min_z, z)
        self.max_z = max(self.max_z, z)
        self.count += 1

    def print_status(self):
        if self.count < 10:
            self.get_logger().info(f'Waiting for data... ({self.count} samples)')
            return

        bias_x = (self.max_x + self.min_x) / 2.0
        bias_y = (self.max_y + self.min_y) / 2.0
        bias_z = (self.max_z + self.min_z) / 2.0
        span_x = self.max_x - self.min_x
        span_y = self.max_y - self.min_y

        self.get_logger().info(
            f'Samples: {self.count} | '
            f'Span X:{span_x:.4f} Y:{span_y:.4f} | '
            f'Bias X:{bias_x:.4f} Y:{bias_y:.4f} Z:{bias_z:.4f}'
        )

    def print_result(self):
        if self.count < 50:
            self.get_logger().warn('Too few samples! Rotate more and retry.')
            return

        bias_x = (self.max_x + self.min_x) / 2.0
        bias_y = (self.max_y + self.min_y) / 2.0
        bias_z = (self.max_z + self.min_z) / 2.0
        span_x = self.max_x - self.min_x
        span_y = self.max_y - self.min_y

        print('\n' + '=' * 55)
        print('CALIBRATION RESULT')
        print('=' * 55)
        print(f'Total samples: {self.count}')
        print(f'X range: [{self.min_x:.4f}, {self.max_x:.4f}] span={span_x:.4f}')
        print(f'Y range: [{self.min_y:.4f}, {self.max_y:.4f}] span={span_y:.4f}')
        print(f'Z range: [{self.min_z:.4f}, {self.max_z:.4f}]')
        print()
        print('Hard-iron bias values:')
        print(f'  bias_x = {bias_x:.6f}')
        print(f'  bias_y = {bias_y:.6f}')
        print(f'  bias_z = {bias_z:.6f}')
        print()
        print('Apply in localization.launch.py:')
        print(f"  'mag_bias_x': {bias_x:.6f},")
        print(f"  'mag_bias_y': {bias_y:.6f},")
        print(f"  'mag_bias_z': {bias_z:.6f},")
        print('=' * 55)

        # Quality check
        if span_x < 0.0001 or span_y < 0.0001:
            print('WARNING: Very small span — robot may not have rotated enough.')
        elif abs(span_x - span_y) / max(span_x, span_y) > 0.5:
            print('WARNING: X/Y spans very different — soft-iron distortion may exist.')
            print('         Consider using full 3D calibration tool for better accuracy.')
        else:
            print('Quality: OK — biases look reasonable.')


def main():
    rclpy.init()
    node = MagCalibrator()

    def shutdown(sig, frame):
        node.print_result()
        node.destroy_node()
        rclpy.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
