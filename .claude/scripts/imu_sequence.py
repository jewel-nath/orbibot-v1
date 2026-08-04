#!/usr/bin/env python3
"""
Record a sequence of held poses and report each one — no typing required.

Built for the loop where the operator has the robot **in both hands** and
cannot press a key between steps. Instead of synchronising with a human, this
records continuously and finds the poses afterwards: a *hold* is any stretch
where the gyro goes quiet for long enough, and the movement between holds
separates them automatically.

So the operator just works down a list at their own pace, and the segments come
out in order.

What it is for: verifying axis and sign conventions end to end — firmware axis
order, driver pass-through, Madgwick, the URDF's `rpy`, ROS's right-hand rule.
Each of those can be wrong on its own while every number still looks sensible,
and a robot that never leaves level exercises none of them.

Sign conventions (ROS: +X forward, +Y left, +Z up), stated so the report can be
read without re-deriving them:

| Pose | roll | pitch |
|---|---|---|
| **Left** side lifted | **positive** | ~0 |
| **Right** side lifted | **negative** | ~0 |
| **Front** lifted (nose up) | ~0 | **positive** |
| **Rear** lifted (nose down) | ~0 | **negative** |

Turning **left / CCW** seen from above increases yaw.

Usage:
    python3 .claude/scripts/imu_sequence.py --duration 150 \
        --expect level,roll+,roll-,pitch+,pitch-

`--expect` is optional; with it, each detected hold is checked against the pose
expected in that position and reported PASS or **MISMATCH**.
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

# A hand-held robot is never perfectly still; this is loose enough to tolerate
# a person breathing and tight enough to exclude the move between poses.
STILL_GYRO_DEG_S = 4.0
MIN_HOLD_S = 2.5
# Below this a pose counts as level rather than leaning either way.
TILT_DEADBAND_DEG = 4.0

POSE_LABELS = {
    'level': 'level',
    'roll+': 'LEFT side up',
    'roll-': 'RIGHT side up',
    'pitch+': 'FRONT up (nose up)',
    'pitch-': 'REAR up (nose down)',
}


def quaternion_to_yaw(q) -> float:
    siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
    cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny_cosp, cosy_cosp)


def classify(roll: float, pitch: float) -> str:
    """Name the dominant lean, or 'level' if neither axis is clearly tilted."""
    if abs(roll) < TILT_DEADBAND_DEG and abs(pitch) < TILT_DEADBAND_DEG:
        return 'level'
    if abs(roll) >= abs(pitch):
        return 'roll+' if roll > 0 else 'roll-'
    return 'pitch+' if pitch > 0 else 'pitch-'


class SequenceRecorder(Node):
    """Samples the IMU continuously; poses are found afterwards, not live."""

    def __init__(self, duration: float):
        super().__init__('imu_sequence')
        self._duration = duration
        self._samples = []          # (t, ax, ay, az, gyro_magnitude_deg_s)
        self._yaw = []              # (t, yaw_deg)
        self._start = time.time()

        self.create_subscription(
            Imu, '/imu/data_raw', self._raw_callback, qos_profile_sensor_data)
        self.create_subscription(
            Imu, '/imu/data_filtered', self._filtered_callback, qos_profile_sensor_data)

    def done(self) -> bool:
        return (time.time() - self._start) >= self._duration

    def elapsed(self) -> float:
        return time.time() - self._start

    def _raw_callback(self, msg: Imu) -> None:
        if self.done():
            return
        gyro = math.sqrt(msg.angular_velocity.x ** 2
                         + msg.angular_velocity.y ** 2
                         + msg.angular_velocity.z ** 2) * RAD_TO_DEG
        self._samples.append((self.elapsed(),
                              msg.linear_acceleration.x,
                              msg.linear_acceleration.y,
                              msg.linear_acceleration.z,
                              gyro))

    def _filtered_callback(self, msg: Imu) -> None:
        if self.done():
            return
        self._yaw.append((self.elapsed(),
                          math.degrees(quaternion_to_yaw(msg.orientation))))

    def _yaw_at(self, t: float) -> float:
        """Nearest filtered-yaw sample to time t, or 0 if none."""
        if not self._yaw:
            return 0.0
        return min(self._yaw, key=lambda row: abs(row[0] - t))[1]

    def find_holds(self):
        """Group consecutive still samples into poses held long enough to count."""
        holds, current = [], []
        for sample in self._samples:
            if sample[4] < STILL_GYRO_DEG_S:
                current.append(sample)
                continue
            if current and current[-1][0] - current[0][0] >= MIN_HOLD_S:
                holds.append(current)
            current = []
        if current and current[-1][0] - current[0][0] >= MIN_HOLD_S:
            holds.append(current)
        return holds

    def report(self, expected) -> int:
        if not self._samples:
            print('NO IMU DATA — is the stack running?')
            return 1

        holds = self.find_holds()
        print(f'\n{len(self._samples)} samples over {self._duration:.0f} s — '
              f'{len(holds)} steady pose(s) detected\n')
        if not holds:
            print('No pose was held still for long enough. Hold each one for '
                  f'at least {MIN_HOLD_S:.0f} s, steadier, and re-run.')
            return 1

        header = (f'{"#":>2}  {"t (s)":>11}  {"held":>5}  {"roll":>8}  '
                  f'{"pitch":>8}  {"yaw":>8}  {"|a|/g":>6}  what the sensor says')
        print(header)
        print('-' * (len(header) + 6))

        mismatches = 0
        for i, hold in enumerate(holds):
            n = len(hold)
            ax = sum(s[1] for s in hold) / n
            ay = sum(s[2] for s in hold) / n
            az = sum(s[3] for s in hold) / n
            roll = math.degrees(math.atan2(ay, az))
            pitch = math.degrees(math.atan2(-ax, math.hypot(ay, az)))
            magnitude = math.sqrt(ax * ax + ay * ay + az * az)
            t0, t1 = hold[0][0], hold[-1][0]
            pose = classify(roll, pitch)

            line = (f'{i + 1:>2}  {t0:5.1f}–{t1:5.1f}  {t1 - t0:4.1f}s  '
                    f'{roll:+8.2f}  {pitch:+8.2f}  {self._yaw_at((t0 + t1) / 2):+8.2f}  '
                    f'{magnitude / GRAVITY:6.4f}  {POSE_LABELS[pose]}')

            if expected and i < len(expected):
                want = expected[i]
                if pose == want:
                    line += f'   ✅ as expected'
                else:
                    line += f'   ❌ EXPECTED {POSE_LABELS.get(want, want)}'
                    mismatches += 1
            print(line)

        if expected:
            print()
            if len(holds) != len(expected):
                print(f'⚠️  {len(holds)} poses detected but {len(expected)} expected — '
                      'the pairing above may be offset. Read the angles, not the ticks.')
            elif mismatches == 0:
                print('✅ Every pose matched. Axis and sign conventions verified '
                      'end to end: firmware → driver → Madgwick → URDF → ROS.')
            else:
                print(f'❌ {mismatches} pose(s) disagreed. Before blaming an axis, '
                      'confirm the robot\'s FRONT was pointing AWAY from the '
                      'operator — holding it facing them mirrors left and right.')
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='Record held poses and report each, without needing keypresses')
    parser.add_argument('--duration', '-d', type=float, default=150.0,
                        help='Total seconds to record (default 150)')
    parser.add_argument('--expect', '-e', default='',
                        help='Comma list of expected poses in order: '
                             'level, roll+, roll-, pitch+, pitch-')
    args = parser.parse_args()

    expected = [p.strip() for p in args.expect.split(',') if p.strip()]
    for pose in expected:
        if pose not in POSE_LABELS:
            print(f'Unknown pose "{pose}". Use: {", ".join(POSE_LABELS)}')
            return 2

    rclpy.init()
    node = SequenceRecorder(args.duration)
    print(f'Recording for {args.duration:.0f} s — hold each pose still for '
          f'{MIN_HOLD_S:.0f}s or more; the moves between them separate the poses.')
    while rclpy.ok() and not node.done():
        rclpy.spin_once(node, timeout_sec=0.05)
    status = node.report(expected)
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    return status


if __name__ == '__main__':
    sys.exit(main())
