#!/usr/bin/env python3
"""
Report IMU orientation in **base_link**, not in the sensor's own frame.

`/imu/data_filtered` carries `frame_id: imu_link`, and Madgwick reports
orientation in that frame. If the sensor is mounted rotated — on this robot it
is, by 90° about Z — then the roll and pitch on that topic are the *sensor's*,
not the robot's, and reading them directly gets the two swapped.

Consumers that resolve TF (robot_localization does) see the corrected values.
Consumers that read the topic straight (a dashboard, a tilt check, a human with
`ros2 topic echo`) do not. This script does what the former does, so the fix can
be **verified** rather than asserted: tilt the camera end up, and base-frame
pitch should rise while base-frame roll stays put.

It reads the rotation from TF rather than hard-coding 90°, so it checks the
URDF's value rather than repeating an assumption about it.

Usage:
    python3 .claude/scripts/imu_base_frame.py -d 20 -l "camera end held up"
"""

import argparse
import math
import sys
import time

import rclpy
import tf2_ros
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu

RAD_TO_DEG = 180.0 / math.pi
TILT_DEADBAND_DEG = 3.0
BASE_FRAME = 'base_link'


def quaternion_multiply(a, b):
    """Hamilton product of two (x, y, z, w) quaternions."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def quaternion_conjugate(q):
    x, y, z, w = q
    return (-x, -y, -z, w)


def quaternion_to_rpy(q):
    """Roll, pitch, yaw in radians from an (x, y, z, w) quaternion."""
    x, y, z, w = q
    roll = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
    sin_pitch = max(-1.0, min(1.0, 2.0 * (w * y - z * x)))
    pitch = math.asin(sin_pitch)
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    return roll, pitch, yaw


class BaseFrameOrientation(Node):
    """Composes the IMU's reported orientation with the fixed sensor→base rotation."""

    def __init__(self, duration: float):
        super().__init__('imu_base_frame')
        self._duration = duration
        self._start = time.time()
        self._sensor = []       # (roll, pitch) as the topic reports them
        self._base = []         # (roll, pitch) after resolving TF
        self._imu_frame = None
        self._q_base_from_imu = None

        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)
        self.create_subscription(
            Imu, '/imu/data_filtered', self._callback, qos_profile_sensor_data)

    def done(self) -> bool:
        return (time.time() - self._start) >= self._duration

    def _lookup(self, imu_frame: str):
        """Fetch base_link ← imu_link once; it is a fixed joint, so it cannot change."""
        if self._q_base_from_imu is not None:
            return True
        try:
            tf = self._tf_buffer.lookup_transform(
                BASE_FRAME, imu_frame, rclpy.time.Time())
        except (tf2_ros.LookupException, tf2_ros.ConnectivityException,
                tf2_ros.ExtrapolationException):
            return False
        r = tf.transform.rotation
        self._q_base_from_imu = (r.x, r.y, r.z, r.w)
        self._imu_frame = imu_frame
        _, _, yaw = quaternion_to_rpy(self._q_base_from_imu)
        self.get_logger().info(
            f'TF {BASE_FRAME} <- {imu_frame}: yaw {yaw * RAD_TO_DEG:+.2f}°')
        return True

    def _callback(self, msg: Imu) -> None:
        if self.done() or not self._lookup(msg.header.frame_id):
            return

        q_imu = (msg.orientation.x, msg.orientation.y,
                 msg.orientation.z, msg.orientation.w)
        sensor_roll, sensor_pitch, _ = quaternion_to_rpy(q_imu)

        # orientation of base_link = orientation of imu_link ∘ (imu → base)
        q_base = quaternion_multiply(
            q_imu, quaternion_conjugate(self._q_base_from_imu))
        base_roll, base_pitch, _ = quaternion_to_rpy(q_base)

        self._sensor.append((sensor_roll * RAD_TO_DEG, sensor_pitch * RAD_TO_DEG))
        self._base.append((base_roll * RAD_TO_DEG, base_pitch * RAD_TO_DEG))

    def report(self, label: str) -> int:
        if not self._base:
            print('NO DATA — is the stack up, and does TF have base_link ← imu_link?')
            return 1

        n = len(self._base)
        s_roll = sum(r for r, _ in self._sensor) / n
        s_pitch = sum(p for _, p in self._sensor) / n
        b_roll = sum(r for r, _ in self._base) / n
        b_pitch = sum(p for _, p in self._base) / n

        def lean(roll, pitch):
            if abs(roll) < TILT_DEADBAND_DEG and abs(pitch) < TILT_DEADBAND_DEG:
                return 'level'
            if abs(pitch) >= abs(roll):
                return 'NOSE UP' if pitch > 0 else 'NOSE DOWN'
            return 'LEFT side up' if roll > 0 else 'RIGHT side up'

        print(f'\n=== {label} ===   {n} samples over {self._duration:.0f} s')
        print(f'  as published on the topic ({self._imu_frame}):')
        print(f'      roll {s_roll:+8.2f}°   pitch {s_pitch:+8.2f}°   '
              f'→ {lean(s_roll, s_pitch)}')
        print(f'  resolved into {BASE_FRAME} — what a TF-aware consumer sees:')
        print(f'      roll {b_roll:+8.2f}°   pitch {b_pitch:+8.2f}°   '
              f'→ {lean(b_roll, b_pitch)}')
        print()
        if abs(b_roll - s_roll) < 0.5 and abs(b_pitch - s_pitch) < 0.5:
            print('  The two agree, so TF says the sensor is aligned with the robot.')
        else:
            print('  The two differ, so the sensor is mounted rotated and TF is')
            print('  correcting it. Reading the topic directly would get this wrong.')
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='Report IMU orientation resolved into base_link')
    parser.add_argument('--duration', '-d', type=float, default=15.0)
    parser.add_argument('--label', '-l', default='snapshot')
    args = parser.parse_args()

    rclpy.init()
    node = BaseFrameOrientation(args.duration)
    while rclpy.ok() and not node.done():
        rclpy.spin_once(node, timeout_sec=0.05)
    status = node.report(args.label)
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    return status


if __name__ == '__main__':
    sys.exit(main())
