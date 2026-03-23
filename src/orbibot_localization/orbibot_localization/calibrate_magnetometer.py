#!/usr/bin/env python3
"""
Magnetometer Hard-Iron + Soft-Iron Calibration for OrbiBot (ICM-20948 / AK09916)

Usage:
  1. ros2 run orbibot_localization calibrate_magnetometer
  2. Slowly rotate the robot 2-3 full 360° turns (manually or via teleop)
  3. Press Ctrl+C when done
  4. Copy the printed values into hardware_params.yaml (imu section)

Methods:
  - min/max (default): Simple axis-aligned scaling. Works without numpy.
  - ellipsoid (--method ellipsoid): Least-squares ellipsoid fit for full hard-iron
    center + axis-aligned soft-iron. Requires numpy. Better for significant distortion.

Both corrections are applied in hardware_node before publishing /imu/mag.
The Madgwick filter receives pre-corrected data (mag_bias_x/y/z should be 0.0).
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import MagneticField
import sys
import signal
import argparse

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


def _ellipsoid_fit_aligned(samples):
    """Fit an axis-aligned ellipsoid to 3D magnetometer data using least-squares.

    Solves: x² + y² - 2z² = u0, plus linear terms for center.
    Model: AlignedXYEqual — assumes XY plane symmetry (ground robot rotates in XY).
    Inspired by lgdxrobot2 chassistuner (fit.cpp) which uses Eigen SVD.

    Args:
        samples: Nx3 numpy array of [x, y, z] magnetometer readings.

    Returns:
        (center, radii) where center=[cx,cy,cz] and radii=[rx,ry,rz],
        or None if fitting fails (too few samples, degenerate data).
    """
    if len(samples) < 20:
        return None

    x, y, z = samples[:, 0], samples[:, 1], samples[:, 2]

    # Design matrix for axis-aligned ellipsoid with XY equal constraint:
    #   Ax² + Ay² + Cz² + 2Gx + 2Hy + 2Iz + J = 0, with A+A+C=3
    # Substituting: (A-1)(x²+y²) + (-2A-1)z² + 2Gx + 2Hy + 2Iz + J = x²+y²+z²
    # Unknowns: [u0, G, H, I, J] where u0 = A-1
    D = np.column_stack([
        x**2 + y**2 - 2*z**2,   # u0 coefficient
        2*x,                      # G
        2*y,                      # H
        2*z,                      # I
        np.ones_like(x)           # J
    ])
    d2 = x**2 + y**2 + z**2

    # Solve via least-squares
    try:
        u, residuals, rank, sv = np.linalg.lstsq(D, d2, rcond=None)
    except np.linalg.LinAlgError:
        return None

    # Reconstruct algebraic coefficients: Ax²+By²+Cz²+2Gx+2Hy+2Iz+J=0
    A = u[0] - 1.0    # = B (XY equal)
    B = A
    C = -2.0 * u[0] - 1.0
    G, H, I, J = u[1], u[2], u[3], u[4]

    # Center = -inv(diag(A,B,C)) * [G,H,I]
    if abs(A) < 1e-12 or abs(C) < 1e-12:
        return None  # Degenerate

    cx = -G / A
    cy = -H / B
    cz = -I / C
    center = np.array([cx, cy, cz])

    # Radii: translate to center, solve eigenvalues
    # R(3,3) = A*cx² + B*cy² + C*cz² + 2G*cx + 2H*cy + 2I*cz + J
    R33 = A*cx*cx + B*cy*cy + C*cz*cz + 2*G*cx + 2*H*cy + 2*I*cz + J
    if R33 == 0:
        return None

    # Radii² = -diag(A,B,C) / R33  (must be positive for valid ellipsoid)
    rx2 = -A / R33
    ry2 = -B / R33
    rz2 = -C / R33

    if rx2 <= 0 or ry2 <= 0 or rz2 <= 0:
        return None  # Not a valid ellipsoid (hyperboloid)

    radii = np.array([1.0/np.sqrt(rx2), 1.0/np.sqrt(ry2), 1.0/np.sqrt(rz2)])
    return center, radii


class MagCalibrator(Node):
    def __init__(self, method='minmax'):
        super().__init__('mag_calibrator')

        self._method = method
        self._min_x = float('inf')
        self._max_x = float('-inf')
        self._min_y = float('inf')
        self._max_y = float('-inf')
        self._min_z = float('inf')
        self._max_z = float('-inf')
        self._count = 0

        # Store all 3D samples for ellipsoid fitting
        self._samples = [] if HAS_NUMPY else None

        self.sub = self.create_subscription(
            MagneticField,
            '/imu/mag',
            self._mag_callback,
            10
        )

        self.timer = self.create_timer(2.0, self._print_status)
        self.get_logger().info('=' * 60)
        self.get_logger().info('Magnetometer Calibration Started')
        self.get_logger().info(f'Method: {method}' + (' (requires numpy)' if method == 'ellipsoid' else ''))
        self.get_logger().info('Slowly rotate the robot 2-3 full 360° turns')
        self.get_logger().info('Press Ctrl+C when done')
        if method == 'ellipsoid' and not HAS_NUMPY:
            self.get_logger().error('numpy required for ellipsoid fitting! Falling back to minmax.')
            self._method = 'minmax'
        self.get_logger().info('=' * 60)

    def _mag_callback(self, msg: MagneticField):
        x = msg.magnetic_field.x
        y = msg.magnetic_field.y
        z = msg.magnetic_field.z

        if x == 0.0 and y == 0.0 and z == 0.0:
            return

        self._min_x = min(self._min_x, x)
        self._max_x = max(self._max_x, x)
        self._min_y = min(self._min_y, y)
        self._max_y = max(self._max_y, y)
        self._min_z = min(self._min_z, z)
        self._max_z = max(self._max_z, z)
        self._count += 1

        if self._samples is not None:
            self._samples.append([x, y, z])

    def _print_status(self):
        if self._count < 10:
            self.get_logger().info(f'Waiting for data... ({self._count} samples)')
            return

        span_x = self._max_x - self._min_x
        span_y = self._max_y - self._min_y
        bias_x = (self._max_x + self._min_x) / 2.0
        bias_y = (self._max_y + self._min_y) / 2.0

        self.get_logger().info(
            f'Samples: {self._count} | '
            f'Span X:{span_x*1e6:.2f}µT Y:{span_y*1e6:.2f}µT | '
            f'Bias X:{bias_x*1e6:.2f}µT Y:{bias_y*1e6:.2f}µT'
        )

    def _compute_soft_iron_scale(self):
        """Min/max span method — diagonal scale factors only."""
        half_x = (self._max_x - self._min_x) / 2.0
        half_y = (self._max_y - self._min_y) / 2.0
        half_z = (self._max_z - self._min_z) / 2.0

        avg_r_xy = (half_x + half_y) / 2.0

        if half_x < 1e-9 or half_y < 1e-9:
            return 1.0, 1.0, 1.0

        scale_x = avg_r_xy / half_x
        scale_y = avg_r_xy / half_y
        scale_z = avg_r_xy / half_z if half_z > 1e-9 else 1.0

        return scale_x, scale_y, scale_z

    def print_result(self):
        if self._count < 50:
            self.get_logger().warn('Too few samples! Rotate more and retry.')
            return

        # Always compute min/max as baseline
        minmax_bias_x = (self._max_x + self._min_x) / 2.0
        minmax_bias_y = (self._max_y + self._min_y) / 2.0
        minmax_bias_z = (self._max_z + self._min_z) / 2.0
        span_x = self._max_x - self._min_x
        span_y = self._max_y - self._min_y

        # Try ellipsoid fitting if requested and numpy available
        ellipsoid_result = None
        if self._method == 'ellipsoid' and self._samples is not None and len(self._samples) >= 50:
            samples = np.array(self._samples)
            ellipsoid_result = _ellipsoid_fit_aligned(samples)

        if ellipsoid_result is not None:
            center, radii = ellipsoid_result
            bias_x, bias_y, bias_z = center[0], center[1], center[2]
            # Scale factors: normalize to average XY radius
            avg_r = (radii[0] + radii[1]) / 2.0
            scale_x = avg_r / radii[0] if radii[0] > 1e-12 else 1.0
            scale_y = avg_r / radii[1] if radii[1] > 1e-12 else 1.0
            scale_z = avg_r / radii[2] if radii[2] > 1e-12 else 1.0
            method_label = 'ELLIPSOID FIT (least-squares)'
        else:
            bias_x, bias_y, bias_z = minmax_bias_x, minmax_bias_y, minmax_bias_z
            scale_x, scale_y, scale_z = self._compute_soft_iron_scale()
            method_label = 'MIN/MAX SPAN'
            if self._method == 'ellipsoid':
                print('\n  ⚠ Ellipsoid fitting failed — falling back to min/max method.')

        print('\n' + '=' * 60)
        print(f'CALIBRATION RESULT — {method_label}')
        print('=' * 60)
        print(f'Total samples: {self._count}')
        print(f'X range: [{self._min_x*1e6:.2f}, {self._max_x*1e6:.2f}] µT  span={span_x*1e6:.2f}µT')
        print(f'Y range: [{self._min_y*1e6:.2f}, {self._max_y*1e6:.2f}] µT  span={span_y*1e6:.2f}µT')
        print(f'Z range: [{self._min_z*1e6:.2f}, {self._max_z*1e6:.2f}] µT')

        if ellipsoid_result is not None:
            print(f'\nEllipsoid center: [{center[0]*1e6:.2f}, {center[1]*1e6:.2f}, {center[2]*1e6:.2f}] µT')
            print(f'Ellipsoid radii:  [{radii[0]*1e6:.2f}, {radii[1]*1e6:.2f}, {radii[2]*1e6:.2f}] µT')
            # Compare with min/max
            print(f'\nMin/max bias for comparison:')
            print(f'  [{minmax_bias_x*1e6:.2f}, {minmax_bias_y*1e6:.2f}, {minmax_bias_z*1e6:.2f}] µT')

        print()
        print('Hard-iron bias (Tesla):')
        print(f'  bias_x = {bias_x:.8f}')
        print(f'  bias_y = {bias_y:.8f}')
        print(f'  bias_z = {bias_z:.8f}')
        print()
        print('Soft-iron scale factors (dimensionless):')
        print(f'  scale_x = {scale_x:.4f}')
        print(f'  scale_y = {scale_y:.4f}')
        print(f'  scale_z = {scale_z:.4f}')
        print()
        print('Copy to hardware_params.yaml (imu section):')
        print(f"      mag_hard_iron_x: {bias_x:.8f}")
        print(f"      mag_hard_iron_y: {bias_y:.8f}")
        print(f"      mag_hard_iron_z: {bias_z:.8f}")
        print(f"      mag_soft_iron_scale_x: {scale_x:.4f}")
        print(f"      mag_soft_iron_scale_y: {scale_y:.4f}")
        print(f"      mag_soft_iron_scale_z: 1.0000  # keep 1.0 — Z not calibrated in flat rotation")
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
            print(f'  Scale ratio: {ratio:.3f}')
            if self._method != 'ellipsoid':
                print('  TIP: Re-run with --method ellipsoid for better correction.')
        else:
            print('  OK — X/Y spans well-matched, soft-iron distortion minimal.')
        print()


def main():
    # Parse --method argument before rclpy.init (which consumes its own args)
    parser = argparse.ArgumentParser(description='OrbiBot magnetometer calibration')
    parser.add_argument('--method', choices=['minmax', 'ellipsoid'], default='minmax',
                        help='Calibration method: minmax (default) or ellipsoid (requires numpy)')
    # Filter out ROS args before argparse
    filtered_args = [a for a in sys.argv[1:] if not a.startswith('--ros-args') and a != '-r']
    args, _ = parser.parse_known_args(filtered_args)

    rclpy.init()
    node = MagCalibrator(method=args.method)

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
