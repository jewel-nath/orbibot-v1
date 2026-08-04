#!/usr/bin/env python3
"""
Live orientation snapshot — for checking axis and sign conventions with a human.

Reads `/imu/data_raw` and `/imu/data_filtered` for a few seconds and says, in
words, which way the robot is leaning and which way it turned. Built for the
loop where the operator physically moves the robot and the sensor is asked
whether it agrees:

    "Lift the left side and hold it."   →   roll should read clearly POSITIVE

That loop is the only way to verify the whole convention chain end to end —
firmware axis order, driver pass-through, Madgwick, the URDF's `rpy`, and ROS's
right-hand rule. Every one of those can be individually wrong while every
number still looks plausible, and a robot that is always level never exercises
any of them.

Sign conventions this checks (ROS: +X forward, +Y left, +Z up):

| Action | Expected |
|---|---|
| **Left** side lifted | roll **positive**, `a_y` positive |
| **Right** side lifted | roll **negative**, `a_y` negative |
| **Front** lifted (nose up) | pitch **positive**, `a_x` negative |
| **Rear** lifted (nose down) | pitch **negative**, `a_x` positive |
| Turned **left** / CCW seen from above | gyro Z **positive**, yaw increases |
| Turned **right** / CW | gyro Z **negative**, yaw decreases |

Usage:
    python3 .claude/scripts/imu_orientation.py -d 5 -l "left side lifted"
"""

import argparse
import math
import sys
import time

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu

RAD_TO_DEG = 180.0 / math.pi
GRAVITY = 9.80665
# Below this the robot is level enough that the sign is noise, not a lean.
LEVEL_DEADBAND_DEG = 0.5
# Below this nothing turned; hand-held wobble alone reaches a few deg/s.
TURN_DEADBAND_DEG = 2.0


def quaternion_to_yaw(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


class OrientationSnapshot(Node):
    """Averages accel for tilt, tracks gyro peaks and yaw change over a window."""

    def __init__(self, duration: float):
        super().__init__('imu_orientation')
        self._duration = duration
        self._accel_sum = [0.0, 0.0, 0.0]
        self._n = 0
        self._gyro_peak = [0.0, 0.0, 0.0]      # signed, largest magnitude
        self._yaw_first = None
        self._yaw_unwrapped = 0.0
        self._yaw_prev = None
        self._start = time.time()

        self.create_subscription(
            Imu, '/imu/data_raw', self._raw_callback, qos_profile_sensor_data)
        self.create_subscription(
            Imu, '/imu/data_filtered', self._filtered_callback, qos_profile_sensor_data)

    def done(self) -> bool:
        return (time.time() - self._start) >= self._duration

    def _raw_callback(self, msg: Imu) -> None:
        if self.done():
            return
        self._accel_sum[0] += msg.linear_acceleration.x
        self._accel_sum[1] += msg.linear_acceleration.y
        self._accel_sum[2] += msg.linear_acceleration.z
        self._n += 1
        for i, rate in enumerate((msg.angular_velocity.x,
                                  msg.angular_velocity.y,
                                  msg.angular_velocity.z)):
            if abs(rate) > abs(self._gyro_peak[i]):
                self._gyro_peak[i] = rate

    def _filtered_callback(self, msg: Imu) -> None:
        if self.done():
            return
        yaw = quaternion_to_yaw(msg.orientation)
        if self._yaw_prev is None:
            self._yaw_first = yaw
            self._yaw_unwrapped = yaw
        else:
            delta = yaw - self._yaw_prev
            if delta > math.pi:
                delta -= 2.0 * math.pi
            elif delta < -math.pi:
                delta += 2.0 * math.pi
            self._yaw_unwrapped += delta
        self._yaw_prev = yaw

    def report(self, label: str) -> int:
        if self._n == 0:
            print('NO IMU DATA — is the stack running?')
            return 1

        ax, ay, az = (s / self._n for s in self._accel_sum)
        roll = math.degrees(math.atan2(ay, az))
        pitch = math.degrees(math.atan2(-ax, math.hypot(ay, az)))
        magnitude = math.sqrt(ax * ax + ay * ay + az * az)
        yaw_change = math.degrees(self._yaw_unwrapped - self._yaw_first) \
            if self._yaw_first is not None else 0.0

        def side(value, positive, negative):
            if abs(value) < LEVEL_DEADBAND_DEG:
                return 'level'
            return positive if value > 0 else negative

        print(f'\n=== {label} ===   {self._n} samples over {self._duration:.0f} s')
        print(f'  roll   {roll:+8.2f}°   (a_y = {ay:+7.3f})   '
              f'→ {side(roll, "LEFT side UP", "RIGHT side UP")}')
        print(f'  pitch  {pitch:+8.2f}°   (a_x = {ax:+7.3f})   '
              f'→ {side(pitch, "FRONT up / nose up", "REAR up / nose down")}')
        print(f'  |a| = {magnitude:.4f} m/s²   ratio to g = {magnitude / GRAVITY:.4f}')
        print(f'  gyro peak (°/s)   X {self._gyro_peak[0] * RAD_TO_DEG:+7.2f}   '
              f'Y {self._gyro_peak[1] * RAD_TO_DEG:+7.2f}   '
              f'Z {self._gyro_peak[2] * RAD_TO_DEG:+7.2f}')

        turned = 'no turn' if abs(yaw_change) < TURN_DEADBAND_DEG else (
            'turned LEFT / CCW' if yaw_change > 0 else 'turned RIGHT / CW')
        print(f'  yaw change {yaw_change:+8.2f}°   → {turned}  (within this window)')

        # Absolute heading, so two snapshots taken either side of a rotation can
        # be differenced. Madgwick's zero is wherever it started, which is fine
        # as long as the node is not restarted between the two readings.
        if self._yaw_prev is not None:
            print(f'  YAW NOW  {math.degrees(self._yaw_prev):+8.2f}°   '
                  '(Madgwick reference — compare between snapshots)')
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='Snapshot IMU orientation while a human moves the robot')
    parser.add_argument('--duration', '-d', type=float, default=5.0,
                        help='Seconds to average over (default 5)')
    parser.add_argument('--label', '-l', default='snapshot',
                        help='What the operator was asked to do')
    args = parser.parse_args()

    rclpy.init()
    node = OrientationSnapshot(args.duration)
    while rclpy.ok() and not node.done():
        rclpy.spin_once(node, timeout_sec=0.05)
    status = node.report(args.label)
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    return status


if __name__ == '__main__':
    sys.exit(main())
