#!/usr/bin/env python3
"""
Log battery voltage while the motors pull, and report the worst dip (P-3).

A multimeter's needle cannot show a sag: the rail drops and recovers faster
than anyone can read it. The firmware already samples the pack and puts the
voltage in every speed report, so the **minimum** over a motor burst can simply
be recorded — which is the number P-3 actually asks for.

**The ADC has been calibrated, so these readings mean something.** 2026-08-04, a
meter read **12.95 V** against a firmware-reported **12.700 V** — the firmware
reads **0.25 V low**, so every threshold fires *earlier* than its label, which
is the safe direction (`test-report.md` §9.10, `physical-checks.md` C1). Both
raw and corrected values are printed below.

Two things this still cannot do:

* Separate offset from scale — that was one calibration point. The two models
  agree to 0.04 V near the cutoff, so it changes no decision today; a second
  reading on a part-discharged pack would settle it.
* Survive the event it is measuring. If the rail collapses far enough to reset
  the board or the computer, the log dies at exactly the interesting moment. A
  meter with min-hold does not, which is why the first run of a *new* power
  configuration still deserves one.

**Resolution matters and is reported.** Voltage reaches ROS through
`/orbibot/system_status` at `rates.status_rate`, which defaults to **10 Hz** —
100 ms between samples, enough to miss a short dip entirely. For a real P-3 run
raise it first:

    ros2 param set /orbibot_hardware_node rates.status_rate 50.0

That gives 20 ms resolution (measured 51.3 Hz). It only started working on
2026-08-04 — before that the parameter was accepted and ignored, HW-BUG-10, matching what the firmware actually sends. This
script prints the sample interval it achieved so a coarse log is never mistaken
for a clean result.

Usage:
    python3 .claude/scripts/battery_sag_log.py -d 60 -n "P-3, wheels on ground"
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

import rclpy
from rclpy.node import Node

from orbibot_msgs.msg import SystemStatus

# Thresholds this robot is actually specified against.
GATE_P3_V = 11.5          # roadmap Phase 0 gate — rail must stay above this
WARNING_V = 11.0          # hardware_params battery_low_threshold
BMS_CUTOFF_V = 10.5       # battery_critical_voltage — pack disconnects
CONVERTER_MIN_V = 10.0    # RBD-2767 minimum input; below this the Beelink drops

STATUS_TOPIC = '/orbibot/system_status'
COARSE_INTERVAL_S = 0.05  # slower than this cannot be trusted to catch a dip

# Calibration, `test-report.md` §9.10 (2026-08-04): meter 12.95 V against a
# firmware-reported 12.700 V. The firmware reads LOW, so every threshold fires
# earlier than its label — the safe direction. One point only, so offset and
# scale cannot be separated; the two models agree to 0.04 V near the cutoff.
FIRMWARE_OFFSET_V = 0.25
CALIBRATION_NOTE = 'meter 12.95 V vs firmware 12.700 V, 2026-08-04'
# The firmware sends battery voltage in 0.1 V steps, so nothing finer is real.
FIRMWARE_QUANTUM_V = 0.1


class BatterySagLogger(Node):
    """Records every battery sample with a timestamp; the minimum is the answer."""

    def __init__(self, duration: float):
        super().__init__('battery_sag_log')
        self._duration = duration
        self._samples = []      # (elapsed_s, volts)
        self._start = time.time()
        self.create_subscription(
            SystemStatus, STATUS_TOPIC, self._callback, 10)

    def done(self) -> bool:
        return (time.time() - self._start) >= self._duration

    def _callback(self, msg: SystemStatus) -> None:
        if self.done():
            return
        self._samples.append((time.time() - self._start, msg.battery_voltage))

    def report(self, note: str, out_path: str) -> int:
        if not self._samples:
            print(f'NO DATA on {STATUS_TOPIC} — is the stack running?')
            return 1

        volts = [v for _, v in self._samples]
        low = min(volts)
        low_at = next(t for t, v in self._samples if v == low)
        high, mean = max(volts), sum(volts) / len(volts)
        span = self._samples[-1][0] - self._samples[0][0]
        interval = span / max(1, len(self._samples) - 1)

        with open(out_path, 'w', newline='') as handle:
            handle.write('# P-3 battery sag under motor load\n')
            handle.write(f'# started: {datetime.now().isoformat(timespec="seconds")}\n')
            handle.write(f'# note: {note}\n')
            writer = csv.writer(handle)
            writer.writerow(['elapsed_s', 'battery_v'])
            writer.writerows((round(t, 3), round(v, 3)) for t, v in self._samples)

        print(f'\n=== BATTERY UNDER LOAD — {note or "no note"} ===')
        print(f'  {len(volts)} samples over {span:.1f} s '
              f'({1.0 / interval:.1f} Hz, {interval * 1000:.0f} ms apart)')
        if interval > COARSE_INTERVAL_S:
            print(f'  ⚠️  {interval * 1000:.0f} ms between samples is too coarse to '
                  'trust for a dip.')
            print('      ros2 param set /orbibot_hardware_node rates.status_rate 50.0')
        print()
        print(f'  max   {high:.3f} V      (true ~{high + FIRMWARE_OFFSET_V:.2f} V)')
        print(f'  mean  {mean:.3f} V      (true ~{mean + FIRMWARE_OFFSET_V:.2f} V)')
        print(f'  MIN   {low:.3f} V      (true ~{low + FIRMWARE_OFFSET_V:.2f} V)'
              f'   at t = {low_at:.2f} s')
        print(f'  calibration: firmware reads {FIRMWARE_OFFSET_V:.2f} V low '
              f'({CALIBRATION_NOTE})')
        print(f'  resolution:  {FIRMWARE_QUANTUM_V:.1f} V steps — a smaller sag '
              'cannot be seen at any sample rate')
        print()
        print('  Thresholds below compare against the RAW firmware value, because')
        print('  that is what the firmware\'s own cutoff logic uses.')

        for label, limit in (('P-3 gate', GATE_P3_V),
                             ('low warning', WARNING_V),
                             ('BMS cutoff', BMS_CUTOFF_V),
                             ('converter minimum', CONVERTER_MIN_V)):
            mark = '✅ clear' if low > limit else '❌ BREACHED'
            print(f'  {label:<20} {limit:5.1f} V   {mark}  '
                  f'(margin {low - limit:+.3f} V)')

        print()
        if low > GATE_P3_V:
            print('  P-3 passes on this run. Record it in test-report.md with the')
            print('  conditions — wheels on the ground or not, and the battery state.')
        else:
            print('  P-3 does NOT pass on this run. Do not conclude the robot cannot')
            print('  drive — conclude the margin is unmeasured or thin, and say by')
            print('  how much. Check the charger was disconnected before believing it.')
        print(f'\n  CSV: {out_path}')
        return 0


def main():
    parser = argparse.ArgumentParser(
        description='Log battery voltage and report the worst dip (P-3)')
    parser.add_argument('--duration', '-d', type=float, default=60.0,
                        help='Seconds to log (default 60)')
    parser.add_argument('--note', '-n', default='',
                        help='Conditions — wheels on ground? charger disconnected?')
    parser.add_argument('--out', '-o', default=None, help='CSV path')
    args = parser.parse_args()

    out_path = args.out or os.path.join(
        'logs', f'p3-battery-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv')
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    rclpy.init()
    node = BatterySagLogger(args.duration)
    print(f'Logging {STATUS_TOPIC} for {args.duration:.0f} s. '
          'Drive the robot during this window.')
    while rclpy.ok() and not node.done():
        rclpy.spin_once(node, timeout_sec=0.05)
    status = node.report(args.note, out_path)
    node.destroy_node()
    if rclpy.ok():
        rclpy.shutdown()
    return status


if __name__ == '__main__':
    sys.exit(main())
