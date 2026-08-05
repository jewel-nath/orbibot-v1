#!/usr/bin/env python3
"""
Drive a fixed manoeuvre profile and attribute the battery sag to each manoeuvre.

`battery_sag_log.py` answers *how far did the rail dip*. It cannot say *during
what*, because the driving happens in someone else's hands. This script owns
both ends: it commands the motion and records the voltage, so every phase gets
its own minimum and the worst manoeuvre is named rather than guessed.

**A voltage log alone can be silently meaningless.** If the motors never turned
— disabled, mux outranked, a stale command timeout — the rail obviously does
not sag, and the run reads as a pass. So wheel motion is recorded alongside the
voltage and printed per phase. A phase that commanded motion and measured none
is reported as INVALID, not as a pass.

Motion is read from the **wheel positions** in `/joint_states`, per wheel, not
from `/odom`. Two reasons. Odometry is a fused average, so one dead motor still
leaves the robot moving and the average non-zero; four separate encoder deltas
cannot hide that. And `/joint_states.velocity` is published empty by
`hardware_node` — only `position` is filled — so a velocity check silently
measures nothing at all. It read zero through a run in which the robot visibly
drove, 2026-08-05.

Manoeuvres are ordered by how hard they pull, gentlest first:

  forward/back   all four wheels drive along their rolling direction
  strafe         mecanum sideways — the rollers slip, so the same ground speed
                 costs noticeably more current than driving forward
  rotate         all four wheels fight each other about the centre
  reversal       forward straight into backward with no pause; the motors brake
                 the robot's inertia before reaccelerating, which is the largest
                 current transient this robot can produce at a safe speed

Speeds stay low on purpose (`.claude/rules/robot-safety.md`): 0.15 m/s is
enough to measure almost anything. That bounds what the result proves — see the
warning printed at the end. Commands go to `cmd_vel_agent`, so the dashboard's
e-stop and teleop both outrank this script while it runs.

Usage:
    python3 .claude/scripts/drive_profile.py --profile gentle
    python3 .claude/scripts/drive_profile.py --profile full -n "P-3, on ground"
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState

from orbibot_msgs.srv import SetMotorEnable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from battery_sag_log import (  # noqa: E402  — thresholds and the ADC calibration
    BMS_CUTOFF_V,
    CALIBRATION_NOTE,
    CONVERTER_MIN_V,
    FIRMWARE_OFFSET_V,
    FIRMWARE_QUANTUM_V,
    GATE_P3_V,
    STATUS_TOPIC,
    WARNING_V,
)
from orbibot_msgs.msg import SystemStatus  # noqa: E402

CMD_TOPIC = '/cmd_vel_agent'      # priority 100 — e-stop, joystick and web outrank it
CMD_RATE_HZ = 20.0                # well inside cmd_vel_agent's 1.0 s mux timeout
SETTLE_S = 0.4                    # zeros held after the profile before disabling

# A phase is (label, vx m/s, vy m/s, wz rad/s, seconds).
GENTLE_PROFILE = [
    ('baseline (still)', 0.00, 0.00, 0.0, 3.0),
    ('forward', 0.15, 0.00, 0.0, 2.0),
    ('rest', 0.00, 0.00, 0.0, 2.0),
    ('backward', -0.15, 0.00, 0.0, 2.0),
    ('rest', 0.00, 0.00, 0.0, 3.0),
]

FULL_PROFILE = [
    ('baseline (still)', 0.00, 0.00, 0.00, 3.0),
    ('forward', 0.15, 0.00, 0.00, 2.0),
    ('rest', 0.00, 0.00, 0.00, 2.0),
    ('backward', -0.15, 0.00, 0.00, 2.0),
    ('rest', 0.00, 0.00, 0.00, 2.0),
    ('strafe left', 0.00, 0.15, 0.00, 2.0),
    ('rest', 0.00, 0.00, 0.00, 2.0),
    ('strafe right', 0.00, -0.15, 0.00, 2.0),
    ('rest', 0.00, 0.00, 0.00, 2.0),
    ('rotate CCW', 0.00, 0.00, 0.60, 2.0),
    ('rest', 0.00, 0.00, 0.00, 2.0),
    ('reversal fwd', 0.15, 0.00, 0.00, 1.5),
    ('reversal back', -0.15, 0.00, 0.00, 1.5),
    ('rest', 0.00, 0.00, 0.00, 3.0),
]


def _speed_profile(speed: float, run_s: float, spin: float) -> list:
    """
    Build the `full` shape at an arbitrary speed.

    Speed is what the quantisation floor forced. At 0.15 m/s the sag sat under
    the firmware's 0.1 V step, so the run said "clear" without saying by how
    much. Current rises with speed and much faster with acceleration, so the
    same manoeuvres are simply repeated harder.

    Every forward leg is followed by its mirror, so the robot works around its
    starting point instead of walking away from it.

    Args:
        speed: Linear speed in m/s for both the straight and strafe legs.
        run_s: Seconds per driving leg. Floor needed ahead is speed * run_s.
        spin: Rotation rate in rad/s for the in-place turn.

    Returns:
        A profile: a list of (label, vx, vy, wz, seconds).
    """
    s = f'{speed:.2f}'
    return [
        ('baseline (still)', 0.00, 0.00, 0.00, 3.0),
        (f'forward {s}', speed, 0.00, 0.00, run_s),
        ('rest', 0.00, 0.00, 0.00, 2.0),
        (f'backward {s}', -speed, 0.00, 0.00, run_s),
        ('rest', 0.00, 0.00, 0.00, 2.0),
        (f'strafe left {s}', 0.00, speed, 0.00, run_s),
        ('rest', 0.00, 0.00, 0.00, 2.0),
        (f'strafe right {s}', 0.00, -speed, 0.00, run_s),
        ('rest', 0.00, 0.00, 0.00, 2.0),
        (f'rotate {spin:.1f}', 0.00, 0.00, spin, 2.0),
        ('rest', 0.00, 0.00, 0.00, 2.0),
        (f'reversal fwd {s}', speed, 0.00, 0.00, run_s),
        (f'reversal back {s}', -speed, 0.00, 0.00, run_s),
        ('rest', 0.00, 0.00, 0.00, 3.0),
    ]


PROFILES = {
    'gentle': GENTLE_PROFILE,                        # ~0.3 m of floor
    'full': FULL_PROFILE,                            # ~0.3 m of floor
    'stress': _speed_profile(0.30, 3.0, 1.20),       # ~0.9 m ahead
    # Shorter legs, so more speed costs no more floor than `stress`. Current
    # draw follows speed and the acceleration step, not how long the leg runs,
    # so nothing is given up by keeping the distance down. 1.5 s at 0.45 m/s
    # covers ~0.6 m, which must stay comfortably inside `--budget` — at 2.0 s
    # it covered 0.9 m and every outward leg hit the 0.8 m limit.
    'sprint': _speed_profile(0.45, 1.5, 1.80),       # ~0.6 m ahead
}

# A wheel turning this little over a whole phase has not driven. The slowest
# commanded phase turns each wheel ~6 rad (0.15 m/s for 2 s at r = 50 mm), so
# this sits an order of magnitude below any real motion and far above encoder
# noise — a 1320 CPR encoder resolves 0.005 rad.
WHEEL_TURNED_RAD = 0.50
WHEEL_RADIUS_M = 0.05

WHEEL_LABELS = ('FL', 'BL', 'FR', 'BR')

# A rest phase begins with the motors still decelerating and the pack still
# recovering, so only its tail is a fair sample of the unloaded rail.
BASELINE_TAIL_S = 1.0

# Floor-budget guard: how often to re-judge whether an out-of-bounds phase is
# heading home, and how much closer it must have got to count as heading home.
# The interval bounds the overshoot — at 0.45 m/s, 0.25 s is ~11 cm past the
# budget before the leg is cut, which is why the budget sits inside the floor.
BOUND_INTERVAL_S = 0.25
BOUND_PROGRESS_M = 0.01


class DriveProfile(Node):
    """Commands the profile while recording battery voltage and wheel motion."""

    def __init__(self):
        super().__init__('drive_profile')
        self._cmd_pub = self.create_publisher(Twist, CMD_TOPIC, 10)
        self.create_subscription(SystemStatus, STATUS_TOPIC, self._status_cb, 20)
        self.create_subscription(JointState, '/joint_states', self._joint_cb, 20)
        self.create_subscription(Odometry, '/odom', self._odom_cb, 20)
        self._enable_client = self.create_client(
            SetMotorEnable, '/orbibot/set_motor_enable')

        self._volts = []          # (elapsed_s, raw_volts)
        self._wheels = []         # (elapsed_s, (FL, BL, FR, BR) radians)
        self._odom = None         # latest (x, y) — position only
        self._origin = None       # (x, y) when the profile began
        self._profile = []        # phases as driven, for the coverage note
        self._budget_m = None     # metres from origin the robot may wander
        self._truncated = False   # this phase hit the budget; reset per phase
        self._bound_mark = None   # (time, separation) the guard judges progress from
        self._start = time.time()

    # -- callbacks ---------------------------------------------------------

    def _status_cb(self, msg: SystemStatus) -> None:
        self._volts.append((self._elapsed(), msg.battery_voltage))

    def _joint_cb(self, msg: JointState) -> None:
        # velocity[] is published empty by hardware_node; position[] is the
        # only field carrying motion, so accumulate it and difference later.
        if len(msg.position) == len(WHEEL_LABELS):
            self._wheels.append((self._elapsed(), tuple(msg.position)))

    def _odom_cb(self, msg: Odometry) -> None:
        p = msg.pose.pose.position
        self._odom = (p.x, p.y)

    def _elapsed(self) -> float:
        return time.time() - self._start

    # -- driving -----------------------------------------------------------

    def set_motors(self, enable: bool, timeout: float = 5.0) -> bool:
        """
        Enable or disable the motors and wait for the board to answer.

        Args:
            enable: True to arm the motors, False to disable them.
            timeout: Seconds to wait for the service and its response.

        Returns:
            True if the board confirmed the request.
        """
        if not self._enable_client.wait_for_service(timeout_sec=timeout):
            self.get_logger().error('/orbibot/set_motor_enable is not available')
            return False
        request = SetMotorEnable.Request()
        request.enable = enable
        future = self._enable_client.call_async(request)
        rclpy.spin_until_future_complete(self, future, timeout_sec=timeout)
        response = future.result()
        if response is None:
            self.get_logger().error('set_motor_enable did not answer')
            return False
        if not response.success:
            self.get_logger().error(f'set_motor_enable refused: {response.message}')
        return response.success

    def publish_zero(self, seconds: float) -> None:
        """Hold a zero command for `seconds`, spinning so callbacks still run."""
        self._run_phase('', 0.0, 0.0, 0.0, seconds)

    def run_profile(self, profile, budget_m=None) -> list:
        """
        Drive every phase in order.

        Args:
            profile: A list of (label, vx, vy, wz, seconds).
            budget_m: Metres the robot may wander from its start before the
                profile aborts. None disables the check.

        Returns:
            A list of dicts, one per phase, carrying its time window and the
            distance the robot covered during it.
        """
        results = []
        self._origin = self._odom
        self._profile = list(profile)
        self._budget_m = budget_m
        for label, vx, vy, wz, duration in profile:
            commanded = (vx, vy, wz) != (0.0, 0.0, 0.0)
            print(f'  {self._elapsed():5.1f}s  {label:<18} '
                  f'vx={vx:+.2f} vy={vy:+.2f} wz={wz:+.2f}  for {duration:.1f}s',
                  flush=True)
            start_t = self._elapsed()
            start_pos = self._odom
            self._truncated = False
            self._bound_mark = None
            self._run_phase(label, vx, vy, wz, duration)
            end_t = self._elapsed()
            results.append({
                'label': label,
                'commanded': commanded,
                'start': start_t,
                'end': end_t,
                'distance': _separation(start_pos, self._odom),
                'truncated': self._truncated,
            })
        return results

    def _run_phase(self, label, vx, vy, wz, duration) -> None:
        cmd = Twist()
        cmd.linear.x, cmd.linear.y, cmd.angular.z = vx, vy, wz
        deadline = time.time() + duration
        period = 1.0 / CMD_RATE_HZ
        while rclpy.ok() and time.time() < deadline:
            if self._out_of_bounds():
                return
            self._cmd_pub.publish(cmd)
            rclpy.spin_once(self, timeout_sec=period)

    def _out_of_bounds(self) -> bool:
        """
        Stop the profile if the robot has wandered past its floor budget.

        Legs are mirrored, so in principle the robot finishes where it began.
        In practice it does not: slip left it 12-20 cm out per run, and across
        four runs on 2026-08-05 that accumulated until it reached a wall — with
        the profile still driving, and the voltage log still recording a number
        that no longer meant anything.

        Distance alone is the wrong test, and two attempts got it wrong the
        same way. Cutting the run at the boundary, then cutting every phase at
        the boundary, both strand the robot outside it: the leg that would
        bring it home is exactly the leg being cancelled, so the remaining
        profile collapses and the robot sits where it stopped.

        The rule that works is about direction, not position. Outside the
        budget a phase may keep running **while the distance from the origin is
        falling** — a homeward leg is allowed, an outward one is cut. Progress
        is judged over a short interval so that a leg starting from rest is not
        cut before it has moved.

        NOT YET VERIFIED ON HARDWARE. The two earlier versions were, and both
        failed; this one is reasoned, not measured. Watch the first run.

        Position comes from wheel odometry, which is the only estimate
        available and drifts on its own, so keep the budget well inside the
        floor that is actually clear.
        """
        if self._budget_m is None or self._origin is None:
            return False
        separation = _separation(self._origin, self._odom)
        now = time.time()

        if separation <= self._budget_m:
            self._bound_mark = None
            return False

        # Outside the budget. Sample the distance every BOUND_INTERVAL_S and
        # keep going only while it is dropping.
        if self._bound_mark is None:
            self._bound_mark = (now, separation)
            return False
        marked_at, marked_sep = self._bound_mark
        if now - marked_at < BOUND_INTERVAL_S:
            return False
        if separation < marked_sep - BOUND_PROGRESS_M:
            self._bound_mark = (now, separation)
            return False

        if not self._truncated:
            self._truncated = True
            print(f'         ⛔ cut short — {separation:.2f} m from the start, past '
                  f'the {self._budget_m:.2f} m budget and not heading back',
                  flush=True)
        return True

    # -- reporting ---------------------------------------------------------

    def report(self, phases, note, out_path) -> int:
        """Print the per-phase table and the P-3 verdict; write the raw CSV."""
        if not self._volts:
            print(f'\nNO DATA on {STATUS_TOPIC} — was the stack running?')
            return 1

        volts = [v for _, v in self._volts]
        low, high = min(volts), max(volts)
        span = self._volts[-1][0] - self._volts[0][0]
        interval = span / max(1, len(self._volts) - 1)
        rest_trend = self._rest_trend(phases)
        baseline = rest_trend[0][1] if rest_trend else None

        self._write_csv(out_path, note)

        print(f'\n=== DRIVE PROFILE — {note or "no note"} ===')
        print(f'  {len(volts)} voltage samples over {span:.1f} s '
              f'({1.0 / interval:.1f} Hz, {interval * 1000:.0f} ms apart)')
        print(f'  calibration: firmware reads {FIRMWARE_OFFSET_V:.2f} V low '
              f'({CALIBRATION_NOTE})')
        print(f'  resolution:  {FIRMWARE_QUANTUM_V:.1f} V steps — a smaller sag is '
              'invisible at any sample rate\n')

        header = (f'  {"phase":<18} {"min V":>7} {"mean V":>8} {"Δmean":>7} '
                  f'{"odom":>8}   {"wheel travel FL/BL/FR/BR (cm)":<30}')
        print(header)
        print(f'  {"-" * (len(header) - 2)}')
        invalid = []
        loads = []
        for phase in phases:
            window = self._window(self._volts, phase)
            if not window:
                continue
            p_min, p_mean = min(window), _mean(window)
            local = _interpolate(rest_trend, 0.5 * (phase['start'] + phase['end']))
            drop = None if local is None else p_mean - local
            turns = self._wheel_travel(phase)
            rim_cm = ' '.join(f'{t * WHEEL_RADIUS_M * 100:6.1f}' for t in turns)
            # A truncated leg is a partial one, not a failed one: it is too
            # short to judge for stopped wheels and too short to compare
            # against the others, so it is marked and left out of both.
            flag = ' ✂' if phase.get('truncated') else ''
            if phase['commanded'] and not flag:
                if min(turns) < WHEEL_TURNED_RAD:
                    flag = ' ❌'
                    invalid.append(phase['label'])
                elif drop is not None:
                    loads.append((drop, phase['label']))
            print(f'  {phase["label"]:<18} {p_min:7.2f} {p_mean:8.3f} '
                  f'{"" if drop is None else f"{drop:+.3f}":>7} '
                  f'{phase["distance"] * 100:6.1f}cm   {rim_cm}{flag}')

        print('\n  wheel travel is path length at the rim, so a reversal counts both')
        print('  directions. Every wheel must turn; one lagging the others by more')
        print('  than a few percent is a motor to look at, not a rounding difference.')

        if rest_trend:
            drift = rest_trend[-1][1] - rest_trend[0][1]
            print(f'\n  rest-voltage trend across the run: {drift:+.3f} V '
                  f'over {rest_trend[-1][0] - rest_trend[0][0]:.0f} s')
            if abs(drift) >= FIRMWARE_QUANTUM_V / 2:
                print('  The unloaded rail is moving on its own — a pack recovering from')
                print('  an earlier run, or discharging under a long one. Δmean above is')
                print('  measured against this trend, not against the first phase; doing')
                print('  it the other way ranked the heaviest manoeuvre as a rise.')

        if loads:
            print('\n  Load ranking by Δmean, detrended — heaviest first. The firmware')
            print(f'  quantises to {FIRMWARE_QUANTUM_V:.1f} V, so no single sample resolves a smaller')
            print('  sag; the reading dithers across the code boundary, which makes the')
            print('  MEAN a sub-quantum estimator. This ordering is the result, not min V.')
            for drop, label in sorted(loads):
                print(f'    {label:<18} {drop:+.3f} V')

        print(f'\n  worst dip   {low:.3f} V raw   (true ~{low + FIRMWARE_OFFSET_V:.2f} V)')
        if baseline is not None:
            print(f'  baseline    {baseline:.3f} V raw   '
                  f'→ total sag {low - baseline:+.3f} V')
        print(f'  highest     {high:.3f} V raw')

        # Every forward leg is undone by a backward leg, so the robot should
        # finish near where it began. It will not finish exactly there — the
        # gap is accumulated slip plus odometry error, and it says how much
        # floor the next, longer run actually needs.
        drift = _separation(self._origin, self._odom)
        print(f'\n  ended {drift * 100:.1f} cm from where the profile started '
              '(slip + odometry error)')

        print('\n  Thresholds compare against the RAW firmware value, because that')
        print('  is what the firmware\'s own cutoff logic uses.')
        for label, limit in (('P-3 gate', GATE_P3_V),
                             ('low warning', WARNING_V),
                             ('BMS cutoff', BMS_CUTOFF_V),
                             ('converter minimum', CONVERTER_MIN_V)):
            mark = '✅ clear' if low > limit else '❌ BREACHED'
            print(f'  {label:<20} {limit:5.1f} V   {mark}  '
                  f'(margin {low - limit:+.3f} V)')

        print()
        if invalid:
            print(f'  ❌ INVALID — commanded motion, but at least one wheel did not '
                  f'turn: {", ".join(invalid)}')
            print('     The rail cannot sag under a load that was never applied, so')
            print('     a clear voltage here proves nothing. If every wheel read zero,')
            print('     check motors_enabled, the twist_mux source and cmd_timeout; if')
            print('     one wheel read zero, that is a motor or an encoder.')
            return 1
        if low > GATE_P3_V:
            top = max(max(abs(p[1]), abs(p[2])) for p in self._profile)
            print('  P-3 passes for THIS profile. What that does and does not cover:')
            print(f'    covered      the manoeuvres above, up to {top:.2f} m/s, at this')
            print(f'                 pack state ({high:.2f} V raw at rest)')
            print('    NOT covered  a carpet or a ramp, and a part-discharged pack —')
            print('                 sag grows as the pack falls, and this run started')
            print('                 near the top of it.')
        else:
            print('  P-3 does NOT pass on this run. State the margin, do not round it')
            print('  up to a failure of the robot: check the charger was disconnected.')
        print(f'\n  CSV: {out_path}')
        return 0

    def _window(self, series, phase) -> list:
        return [v for t, v in series if phase['start'] <= t < phase['end']]

    def _rest_trend(self, phases) -> list:
        """
        Sample the unloaded rail once per rest phase, to detrend against.

        The pack does not sit still between manoeuvres: it recovers after an
        earlier run and falls under a long one. Measured 2026-08-05, the rest
        voltage climbed 0.071 V across a 36 s profile — larger than the sag
        being measured, which ranked the heaviest manoeuvre as a *rise* when
        every phase was compared to the first one.

        Only the tail of each rest is used; the start of a rest still contains
        the motors decelerating and the pack recovering.

        Args:
            phases: Every phase, in order.

        Returns:
            (midpoint_time, mean_volts) per usable rest phase, in time order.
        """
        points = []
        for phase in phases:
            if phase['commanded']:
                continue
            start = max(phase['start'], phase['end'] - BASELINE_TAIL_S)
            tail = [v for t, v in self._volts if start <= t < phase['end']]
            if tail:
                points.append((0.5 * (start + phase['end']), _mean(tail)))
        return points

    def _wheel_travel(self, phase) -> tuple:
        """
        Radians of path each wheel turned through during a phase.

        Path length, not net displacement. A reversal phase drives forward and
        then backward, so `last - first` very nearly cancels and reports a
        turning wheel as stopped — which it did, 2026-08-05, flagging the one
        phase that loads the motors hardest as if the motors were dead.

        Args:
            phase: A phase dict carrying its `start` and `end` elapsed times.

        Returns:
            Unsigned (FL, BL, FR, BR) path lengths, or zeros if the phase saw
            fewer than two joint_states messages.
        """
        window = self._window(self._wheels, phase)
        if len(window) < 2:
            return (0.0,) * len(WHEEL_LABELS)
        travel = [0.0] * len(WHEEL_LABELS)
        for previous, current in zip(window, window[1:]):
            for i in range(len(WHEEL_LABELS)):
                travel[i] += abs(current[i] - previous[i])
        return tuple(travel)

    def _write_csv(self, out_path, note) -> None:
        with open(out_path, 'w', newline='') as handle:
            handle.write('# P-3 drive profile — battery under commanded load\n')
            handle.write(f'# started: {datetime.now().isoformat(timespec="seconds")}\n')
            handle.write(f'# note: {note}\n')
            writer = csv.writer(handle)
            writer.writerow(['elapsed_s', 'battery_v_raw'])
            writer.writerows((round(t, 3), round(v, 3)) for t, v in self._volts)


def _mean(values):
    return sum(values) / len(values) if values else 0.0


def _interpolate(points, when):
    """
    Read a value off the rest-voltage trend at an arbitrary time.

    Args:
        points: (time, value) pairs in time order.
        when: The time to evaluate at.

    Returns:
        The linearly interpolated value, held flat outside the range, or None
        if there are no points.
    """
    if not points:
        return None
    if when <= points[0][0]:
        return points[0][1]
    if when >= points[-1][0]:
        return points[-1][1]
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if t0 <= when <= t1:
            return v0 + (v1 - v0) * (when - t0) / (t1 - t0)
    return points[-1][1]


def _separation(a, b) -> float:
    """Straight-line distance between two (x, y) odometry positions."""
    if a is None or b is None:
        return 0.0
    return ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5


def main():
    parser = argparse.ArgumentParser(
        description='Drive a fixed profile and attribute the battery sag to it')
    parser.add_argument('--profile', '-p', choices=sorted(PROFILES), default='gentle',
                        help='gentle: forward and back at 0.15 m/s, ~0.3 m of floor. '
                             'full: adds strafe, rotation and a reversal, same speed. '
                             'stress: 0.30 m/s, ~0.9 m ahead. sprint: 0.45 m/s, '
                             '~1.4 m ahead')
    parser.add_argument('--note', '-n', default='',
                        help='Conditions — on the ground? charger disconnected?')
    parser.add_argument('--out', '-o', default=None, help='CSV path')
    parser.add_argument('--budget', '-b', type=float, default=0.8,
                        help='Metres the robot may wander from its start before '
                             'the profile aborts (default 0.8). Position is wheel '
                             'odometry, so keep this inside the clear floor. 0 '
                             'disables the check')
    args = parser.parse_args()

    profile = PROFILES[args.profile]
    out_path = args.out or os.path.join(
        'logs', f'p3-drive-{args.profile}-'
                f'{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv')
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    rclpy.init()
    node = DriveProfile()

    print(f'Profile "{args.profile}", '
          f'{sum(p[4] for p in profile):.0f} s. Ctrl+C stops it.')
    print('Waiting for the first battery sample and odometry...')
    for _ in range(100):
        rclpy.spin_once(node, timeout_sec=0.05)
        if node._volts and node._odom is not None:
            break

    status = 1
    armed = False
    try:
        armed = node.set_motors(True)
        if not armed:
            print('Motors could not be enabled — nothing was driven.')
        else:
            phases = node.run_profile(profile, args.budget or None)
            status = node.report(phases, args.note, out_path)
    except KeyboardInterrupt:
        print('\nInterrupted — stopping.')
    finally:
        # Zeros first, then disable: a disable while a command is still in
        # flight leaves the driver holding a non-zero setpoint for next time.
        try:
            node.publish_zero(SETTLE_S)
        except Exception:
            pass
        if armed:
            node.set_motors(False)
            print('Motors disabled.')
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
    return status


if __name__ == '__main__':
    sys.exit(main())
