#!/usr/bin/env python3
"""
Magnetometer Hard-Iron + Soft-Iron Calibration for OrbiBot (ICM-20948 / AK09916)

Usage:
  1. ros2 run orbibot_localization calibrate_magnetometer
  2. Slowly rotate the robot 2-3 full 360° turns (manually or via teleop)
  3. Press Ctrl+C when done
  4. Copy the printed values into hardware_params.yaml (imu section)

Hard-iron bias  = constant offset caused by nearby permanent magnets (motors, battery).
Soft-iron scale = axis-dependent scaling caused by ferromagnetic material distortion.

Both corrections are applied in hardware_node before publishing /imu/mag.
The Madgwick filter receives pre-corrected data (mag_bias_x/y/z should be 0.0 in launch).
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import MagneticField
import sys
import signal

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class MagCalibrator(Node):
    def __init__(self):
        super().__init__('mag_calibrator')

        self._min_x = float('inf')
        self._max_x = float('-inf')
        self._min_y = float('inf')
        self._max_y = float('-inf')
        self._min_z = float('inf')
        self._max_z = float('-inf')
        self._count = 0

        # Store all samples for quality checks (numpy path)
        self._samples_x = []
        self._samples_y = []

        self.sub = self.create_subscription(
            MagneticField,
            '/imu/mag',
            self._mag_callback,
            10
        )

        self.timer = self.create_timer(2.0, self._print_status)
        self.get_logger().info('=' * 60)
        self.get_logger().info('Magnetometer Calibration Started')
        self.get_logger().info('Slowly rotate the robot 2-3 full 360° turns')
        self.get_logger().info('Press Ctrl+C when done')
        if not HAS_NUMPY:
            self.get_logger().warn('numpy not found — soft-iron calibration disabled')
        self.get_logger().info('=' * 60)

    def _mag_callback(self, msg: MagneticField):
        x = msg.magnetic_field.x
        y = msg.magnetic_field.y
        z = msg.magnetic_field.z

        # Skip zero/NaN readings (hardware_node already applies hard-iron; raw may still be near 0)
        if x == 0.0 and y == 0.0 and z == 0.0:
            return

        self._min_x = min(self._min_x, x)
        self._max_x = max(self._max_x, x)
        self._min_y = min(self._min_y, y)
        self._max_y = max(self._max_y, y)
        self._min_z = min(self._min_z, z)
        self._max_z = max(self._max_z, z)
        self._count += 1

        if HAS_NUMPY:
            self._samples_x.append(x)
            self._samples_y.append(y)

    def _print_status(self):
        if self._count < 10:
            self.get_logger().info(f'Waiting for data... ({self._count} samples)')
            return

        bias_x = (self._max_x + self._min_x) / 2.0
        bias_y = (self._max_y + self._min_y) / 2.0
        span_x = self._max_x - self._min_x
        span_y = self._max_y - self._min_y

        self.get_logger().info(
            f'Samples: {self._count} | '
            f'Span X:{span_x*1e6:.2f}µT Y:{span_y*1e6:.2f}µT | '
            f'Bias X:{bias_x*1e6:.2f}µT Y:{bias_y*1e6:.2f}µT'
        )

    def _compute_soft_iron_scale(self, bias_x, bias_y, bias_z):
        """Compute soft-iron axis scale factors using min/max span method.

        For a ground robot rotating only in XY plane, we compute scale factors
        that normalize each axis radius to the average radius, restoring a circular
        response from an elliptical one.

        Returns:
            (scale_x, scale_y, scale_z): Dimensionless scale factors (≥1.0 on smaller axis).
        """
        half_x = (self._max_x - self._min_x) / 2.0
        half_y = (self._max_y - self._min_y) / 2.0
        half_z = (self._max_z - self._min_z) / 2.0

        # Average radius of XY (robot rotates in XY, Z data is less reliable)
        avg_r_xy = (half_x + half_y) / 2.0

        if half_x < 1e-9 or half_y < 1e-9:
            return 1.0, 1.0, 1.0  # Not enough rotation

        scale_x = avg_r_xy / half_x
        scale_y = avg_r_xy / half_y
        # Z: use XY average as reference (Z barely changes for flat-ground rotation)
        scale_z = avg_r_xy / half_z if half_z > 1e-9 else 1.0

        return scale_x, scale_y, scale_z

    def print_result(self):
        if self._count < 50:
            self.get_logger().warn('Too few samples! Rotate more and retry.')
            return

        bias_x = (self._max_x + self._min_x) / 2.0
        bias_y = (self._max_y + self._min_y) / 2.0
        bias_z = (self._max_z + self._min_z) / 2.0
        span_x = self._max_x - self._min_x
        span_y = self._max_y - self._min_y

        scale_x, scale_y, scale_z = self._compute_soft_iron_scale(bias_x, bias_y, bias_z)

        print('\n' + '=' * 60)
        print('CALIBRATION RESULT')
        print('=' * 60)
        print(f'Total samples: {self._count}')
        print(f'X range: [{self._min_x*1e6:.2f}, {self._max_x*1e6:.2f}] µT  span={span_x*1e6:.2f}µT')
        print(f'Y range: [{self._min_y*1e6:.2f}, {self._max_y*1e6:.2f}] µT  span={span_y*1e6:.2f}µT')
        print(f'Z range: [{self._min_z*1e6:.2f}, {self._max_z*1e6:.2f}] µT')
        print()
        print('Hard-iron bias (Tesla):')
        print(f'  bias_x = {bias_x:.8f}')
        print(f'  bias_y = {bias_y:.8f}')
        print(f'  bias_z = {bias_z:.8f}')
        print()
        print('Soft-iron scale factors (dimensionless):')
        print(f'  scale_x = {scale_x:.4f}')
        print(f'  scale_y = {scale_y:.4f}')
        print(f'  scale_z = {scale_z:.4f}  (less reliable — robot only rotates in XY)')
        print()
        print('Copy to hardware_params.yaml (imu section):')
        print(f"      mag_hard_iron_x: {bias_x:.8f}")
        print(f"      mag_hard_iron_y: {bias_y:.8f}")
        print(f"      mag_hard_iron_z: {bias_z:.8f}")
        print(f"      mag_soft_iron_scale_x: {scale_x:.4f}")
        print(f"      mag_soft_iron_scale_y: {scale_y:.4f}")
        print(f"      mag_soft_iron_scale_z: 1.0000  # keep 1.0 — Z not calibrated in flat rotation")
        print()
        print('Also verify localization.launch.py has:')
        print("      'mag_bias_x': 0.0,  # bias moved to hardware_node")
        print("      'mag_bias_y': 0.0,")
        print("      'mag_bias_z': 0.0,")
        print('=' * 60)

        # Quality assessment
        print()
        print('Quality assessment:')
        if span_x < 1e-6 or span_y < 1e-6:
            print('  WARNING: Very small span — robot may not have rotated enough.')
        elif abs(span_x - span_y) / max(span_x, span_y) > 0.3:
            ratio = max(scale_x, scale_y) / min(scale_x, scale_y)
            print(f'  SOFT-IRON DISTORTION detected: X/Y spans differ by '
                  f'{abs(span_x - span_y)/max(span_x, span_y)*100:.1f}%')
            print(f'  Scale ratio: {ratio:.3f} — applying soft-iron correction recommended.')
        else:
            print('  OK — X/Y spans well-matched, soft-iron distortion minimal.')
            print('  Hard-iron bias is the main correction needed.')
        print()


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
