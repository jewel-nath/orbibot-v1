#!/usr/bin/env python3
"""
HW-BUG-8 — log the firmware's auto-report rate against board uptime.

The serial-derived ROS topics (/imu/data_raw, /joint_states) read 50 Hz about
ten minutes after the ROSMaster board is powered on, and 39-44 Hz about two and
a half hours later. /scan is unaffected, the machine is 95 % idle, and there are
no serial errors: the link is not breaking, it is slowing down.

Two questions have to be answered before anything can be tuned on top of it:

    1. **Where** does the rate decay — in the firmware, or in the ROS driver?
    2. **What shape** is the decay — a step, a straight line, or an asymptote?

This script answers both at once. It talks to the board directly, with no ROS
stack running, so whatever it measures is what the firmware actually put on the
wire. It bins packets by wall clock and writes one CSV row per window, flushed
immediately, so a kill or a power loss still leaves every row up to that point.

It also logs battery voltage, which comes free in the speed report. That tests
the cheapest hypothesis — a sagging rail slowing the board — without a second
run, and it is the reason running with the charger connected is *useful* here
rather than a problem: hold the voltage flat, and if the rate still decays, the
battery is not the cause.

**No motion.** Motors are never armed. Nobody has to be present.

Usage:
    # ask for a board power cycle FIRST, then start at t=0
    python3 .claude/scripts/rate_decay_log.py --note "charger connected"

    # shorter run, finer bins
    python3 .claude/scripts/rate_decay_log.py --duration 3600 --window 30

Read the result with:
    column -s, -t < <csv>            # or plot uptime_min against imu_raw_hz
"""

import argparse
import csv
import os
import signal
import sys
import time
from datetime import datetime

# The protocol helpers live with the firmware tests, not on the Python path.
TESTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'src', 'orbibot_rosmaster_firmware', 'tests')
sys.path.insert(0, os.path.abspath(TESTS_DIR))

from rosmaster_protocol import FuncCode, ROSMasterProtocol  # noqa: E402

DEFAULT_PORT = '/dev/motordriver'
DEFAULT_WINDOW_S = 60.0
DEFAULT_DURATION_S = 3 * 60 * 60
READ_TIMEOUT_S = 0.1

# The five auto-report types, in the order they are written to the CSV.
REPORT_TYPES = (
    ('imu_raw', FuncCode.REPORT_IMU_RAW),
    ('encoder', FuncCode.REPORT_ENCODER),
    ('speed', FuncCode.REPORT_SPEED),
    ('imu_att', FuncCode.REPORT_IMU_ATTITUDE),
    ('odom', FuncCode.REPORT_ODOM),
)

CSV_FIELDS = (
    ['iso_time', 'uptime_s', 'uptime_min', 'window_s', 'packets', 'bytes',
     'total_hz', 'bytes_per_s']
    + [f'{name}_hz' for name, _ in REPORT_TYPES]
    + ['battery_v']
)

_stop = False


def _request_stop(signum, frame):
    """Let the current window finish, then exit — never lose a partial row."""
    global _stop
    _stop = True


class WindowCounter:
    """Counts packets per function code inside one time window."""

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self.counts = {}
        self.byte_count = 0
        self.packet_count = 0
        self.battery_sum = 0.0
        self.battery_samples = 0

    def add(self, func_code: int, payload: bytes) -> None:
        self.packet_count += 1
        self.byte_count += len(payload) + 5   # HEAD, ID, LEN, FUNC, CHECKSUM
        self.counts[func_code] = self.counts.get(func_code, 0) + 1

    def add_battery(self, volts: float) -> None:
        self.battery_sum += volts
        self.battery_samples += 1

    def rate(self, func_code: int, window_s: float) -> float:
        return self.counts.get(func_code, 0) / window_s if window_s > 0 else 0.0

    @property
    def battery_v(self):
        if self.battery_samples == 0:
            return ''
        return round(self.battery_sum / self.battery_samples, 2)


def main():
    parser = argparse.ArgumentParser(
        description='Log firmware auto-report rate against board uptime (HW-BUG-8)')
    parser.add_argument('--port', '-p', default=DEFAULT_PORT, help='Serial port')
    parser.add_argument('--window', '-w', type=float, default=DEFAULT_WINDOW_S,
                        help='Seconds per CSV row (default 60)')
    parser.add_argument('--duration', '-d', type=float, default=DEFAULT_DURATION_S,
                        help='Total seconds to log; 0 runs until stopped (default 10800)')
    parser.add_argument('--out', '-o', default=None,
                        help='CSV path (default logs/hw-bug-8-<timestamp>.csv)')
    parser.add_argument('--note', '-n', default='',
                        help='Conditions — charger connected? robot elevated? firmware?')
    args = parser.parse_args()

    if not os.path.exists(args.port):
        print(f'Error: {args.port} is not present — is the board connected and powered?')
        return 1

    out_path = args.out or os.path.join(
        'logs', f'hw-bug-8-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv')
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    proto = ROSMasterProtocol(args.port)
    if not proto.connect(timeout=READ_TIMEOUT_S):
        print(f'Error: could not open {args.port}.')
        print('A running ROS 2 stack holds this port — .claude/scripts/stop.sh first.')
        return 1

    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    started = datetime.now()
    print(f'HW-BUG-8 rate decay log')
    print(f'  port      {args.port}')
    print(f'  window    {args.window:.0f} s')
    print(f'  duration  {"until stopped" if args.duration <= 0 else f"{args.duration/3600:.1f} h"}')
    print(f'  output    {out_path}')
    print(f'  note      {args.note or "(none)"}')
    print()
    print('  This measures the board, not ROS. No motion, motors never armed.')
    print('  Stop early with Ctrl+C — every completed row is already on disk.')
    print()

    handle = open(out_path, 'w', newline='')
    # Conditions belong with the numbers. A CSV without them is a CSV nobody
    # can interpret in a month.
    handle.write(f'# HW-BUG-8 firmware auto-report rate vs board uptime\n')
    handle.write(f'# started: {started.isoformat(timespec="seconds")}\n')
    handle.write(f'# port: {args.port}  window_s: {args.window}\n')
    handle.write(f'# note: {args.note}\n')
    handle.write('# t=0 is when this script started, so power-cycle the board first.\n')
    writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
    writer.writeheader()
    handle.flush()

    header = f'{"uptime":>8} | {"total":>8} | ' + ' | '.join(
        f'{name:>8}' for name, _ in REPORT_TYPES) + f' | {"batt":>6}'
    print(header)
    print('-' * len(header))

    counter = WindowCounter()
    t_start = time.time()
    window_start = t_start
    rows = 0
    status = 0

    try:
        proto.enable_auto_report(True)

        while not _stop:
            if args.duration > 0 and (time.time() - t_start) >= args.duration:
                break

            for func_code, payload in proto.read_packets(timeout=READ_TIMEOUT_S):
                counter.add(func_code, payload)
                if func_code == FuncCode.REPORT_SPEED:
                    speed = proto.parse_speed(payload)
                    if speed:
                        counter.add_battery(speed.battery_v)

            now = time.time()
            elapsed = now - window_start
            if elapsed < args.window:
                continue

            uptime = now - t_start
            row = {
                'iso_time': datetime.now().isoformat(timespec='seconds'),
                'uptime_s': round(uptime, 1),
                'uptime_min': round(uptime / 60.0, 2),
                'window_s': round(elapsed, 2),
                'packets': counter.packet_count,
                'bytes': counter.byte_count,
                'total_hz': round(counter.packet_count / elapsed, 3),
                'bytes_per_s': round(counter.byte_count / elapsed, 1),
                'battery_v': counter.battery_v,
            }
            for name, code in REPORT_TYPES:
                row[f'{name}_hz'] = round(counter.rate(code, elapsed), 3)

            writer.writerow(row)
            handle.flush()
            os.fsync(handle.fileno())
            rows += 1

            print(f'{uptime/60:7.1f}m | {row["total_hz"]:8.2f} | ' + ' | '.join(
                f'{row[f"{name}_hz"]:8.2f}' for name, _ in REPORT_TYPES)
                + f' | {row["battery_v"] or "-":>6}')

            counter.reset()
            window_start = now

    except Exception as exc:                                   # noqa: BLE001
        print(f'\nAborted: {exc}')
        status = 1
    finally:
        try:
            proto.enable_auto_report(False)
        except Exception:                                      # noqa: BLE001
            pass
        proto.disconnect()
        handle.close()

    print()
    print(f'{rows} rows written to {out_path}')
    print('Record the conclusion in src/orbibot_hardware/hardware-issue.md (HW-BUG-8)')
    print('and the "last run" row in docs/operations/test-index.md.')
    return status


if __name__ == '__main__':
    sys.exit(main())
