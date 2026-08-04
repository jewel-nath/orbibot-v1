#!/usr/bin/env python3
"""
HW-BUG-8 — log ROS topic rates against the *node's* uptime, not the board's.

Companion to `rate_decay_log.py`, which measures the same decay one layer down.
Run that one first: it talks to the ROSMaster board with no ROS stack up, so it
says what the firmware actually put on the wire. On 2026-08-04 it read
**49.98 Hz on all five report types at 2 h 41 min of board uptime** — while the
ROS stack, nine minutes earlier and at the same board uptime, was publishing
`/imu/data_raw` at 39.0 Hz.

That exonerates the firmware and moves HW-BUG-8 onto the host: the 50 Hz timer
in `orbibot_hardware`'s node, or the executor it runs on, is falling behind. So
the clock that matters is **how long the node has been running**, not how long
the board has been powered.

This script logs, per window:

* the measured rate of each topic
* the CPU and **RSS** of the node that publishes them — a memory curve that
  climbs alongside a rate that falls is the whole diagnosis in one CSV

Nobody has to be present, and nothing moves. Motors are never armed.

Usage:
    # start the stack, then start this — t=0 is the node's start, not the board's
    ros2 launch orbibot_bringup robot.launch.py &
    python3 .claude/scripts/topic_rate_log.py --note "charger connected"

    # accelerated: if the decay tracks callbacks rather than wall time, 200 Hz
    # reaches the same callback count 4x sooner. See --help on sensor_rate below.
    ros2 param set /orbibot_hardware rates.sensor_rate 200.0
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy

DEFAULT_TOPICS = ['/imu/data_raw', '/joint_states', '/scan', '/odometry/filtered']
DEFAULT_WINDOW_S = 60.0
DEFAULT_DURATION_S = 3 * 60 * 60
DEFAULT_WATCH_PROCESS = 'hardware_node'
SPIN_TIMEOUT_S = 0.05
BYTES_PER_MIB = 1024 * 1024


# A shell that merely mentions the node in its command line is not the node.
# Matching on the whole command line finds `bash -c "ros2 launch ... hardware_node"`,
# reports it as the process, and then measures 0.0 % CPU forever. This project has
# now been bitten by that three times — see field-notes.md, *Tools that lie*.
_NOT_A_NODE = {'bash', 'sh', 'dash', 'zsh', 'nohup', 'timeout', 'pgrep', 'ps', 'grep'}


def find_process(pattern: str):
    """Return (pid, argv) of the first *real* process whose argv contains `pattern`.

    Reads /proc rather than shelling out to pgrep, and rejects both this process
    and any shell wrapper, judged by argv[0] rather than the full command line.
    """
    for entry in os.listdir('/proc'):
        if not entry.isdigit() or entry == str(os.getpid()):
            continue
        try:
            with open(f'/proc/{entry}/cmdline', 'rb') as handle:
                raw = handle.read().decode('utf-8', 'replace')
        except OSError:
            continue
        argv = raw.replace('\0', ' ').strip()
        if pattern not in argv:
            continue
        if os.path.basename(raw.split('\0')[0]) in _NOT_A_NODE:
            continue
        return int(entry), argv
    return None, None


class ProcessSampler:
    """Samples one process's CPU share and resident memory from /proc."""

    def __init__(self, pattern: str):
        self.pattern = pattern
        self.pid, self.argv = find_process(pattern)
        self._last_ticks = None
        self._last_time = None
        self._clock_ticks = os.sysconf('SC_CLK_TCK')
        self._page_size = os.sysconf('SC_PAGE_SIZE')

    def sample(self):
        """Return (cpu_percent, rss_mib), or ('', '') if the process is gone."""
        if self.pid is None:
            self.pid, self.argv = find_process(self.pattern)
        if self.pid is None:
            return '', ''
        try:
            with open(f'/proc/{self.pid}/stat') as handle:
                fields = handle.read().rsplit(') ', 1)[-1].split()
            # utime and stime are fields 14 and 15 of stat, i.e. 12 and 13 here.
            ticks = int(fields[11]) + int(fields[12])
            with open(f'/proc/{self.pid}/statm') as handle:
                rss_pages = int(handle.read().split()[1])
        except (OSError, IndexError, ValueError):
            self.pid = None
            return '', ''

        now = time.time()
        cpu = ''
        if self._last_ticks is not None and now > self._last_time:
            delta_s = (ticks - self._last_ticks) / self._clock_ticks
            cpu = round(100.0 * delta_s / (now - self._last_time), 2)
        self._last_ticks, self._last_time = ticks, now
        return cpu, round(rss_pages * self._page_size / BYTES_PER_MIB, 2)


class TopicRateLogger(Node):
    """Counts messages per topic, with no per-message work beyond the count."""

    def __init__(self, topics):
        super().__init__('topic_rate_log')
        self.topics = list(topics)
        self.counts = {topic: 0 for topic in topics}

    def subscribe(self, discovery_timeout_s: float = 10.0) -> list:
        """Subscribe to every topic, waiting for the graph to show up first.

        A node that subscribes in its own constructor sees an empty graph and
        silently logs zeroes for the whole run — the topics exist, discovery
        just has not reached this node yet. Wait for them, then subscribe.

        Returns the topics that never appeared.
        """
        # BEST_EFFORT matches the sensor publishers; a RELIABLE subscriber would
        # simply never connect to them and log a silent zero.
        qos = QoSProfile(depth=10, reliability=ReliabilityPolicy.BEST_EFFORT)

        pending = list(self.topics)
        deadline = time.time() + discovery_timeout_s
        while pending and time.time() < deadline:
            for topic in list(pending):
                msg_type = self._resolve_type(topic)
                if msg_type is None:
                    continue
                self.create_subscription(msg_type, topic, self._make_counter(topic), qos)
                pending.remove(topic)
            if pending:
                rclpy.spin_once(self, timeout_sec=0.2)

        for topic in pending:
            self.get_logger().warn(f'{topic} never appeared — it will log as 0.00')
        return pending

    def _resolve_type(self, topic: str):
        """Look the message type up from the graph, so no topic list is hard-coded."""
        for name, types in self.get_topic_names_and_types():
            if name != topic or not types:
                continue
            package, _, message = types[0].split('/')
            module = __import__(f'{package}.msg', fromlist=[message])
            return getattr(module, message)
        return None

    def _make_counter(self, topic: str):
        def callback(_msg):
            self.counts[topic] += 1
        return callback

    def drain(self):
        """Take and clear the current counts."""
        taken = dict(self.counts)
        for topic in self.counts:
            self.counts[topic] = 0
        return taken


def main():
    parser = argparse.ArgumentParser(
        description='Log ROS topic rates and publisher memory against node uptime (HW-BUG-8)')
    parser.add_argument('--topics', '-t', nargs='+', default=DEFAULT_TOPICS,
                        help=f'Topics to count (default: {" ".join(DEFAULT_TOPICS)})')
    parser.add_argument('--window', '-w', type=float, default=DEFAULT_WINDOW_S,
                        help='Seconds per CSV row (default 60)')
    parser.add_argument('--duration', '-d', type=float, default=DEFAULT_DURATION_S,
                        help='Total seconds; 0 runs until stopped (default 10800)')
    parser.add_argument('--watch', default=DEFAULT_WATCH_PROCESS,
                        help='Process substring whose CPU and RSS to sample')
    parser.add_argument('--out', '-o', default=None, help='CSV path')
    parser.add_argument('--note', '-n', default='',
                        help='Conditions — charger connected? sensor_rate? firmware?')
    args = parser.parse_args()

    out_path = args.out or os.path.join(
        'logs', f'hw-bug-8-topics-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv')
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    rclpy.init()
    node = TopicRateLogger(args.topics)
    missing = node.subscribe()
    sampler = ProcessSampler(args.watch)

    # One CSV column per topic: '/imu/data_raw' -> 'imu_data_raw_hz'
    column_of = {t: f'{t.strip("/").replace("/", "_")}_hz' for t in args.topics}
    fields = (['iso_time', 'uptime_s', 'uptime_min', 'window_s']
              + [column_of[t] for t in args.topics]
              + ['watched_cpu_pct', 'watched_rss_mib'])

    handle = open(out_path, 'w', newline='')
    handle.write('# HW-BUG-8 ROS topic rate vs node uptime\n')
    handle.write(f'# started: {datetime.now().isoformat(timespec="seconds")}\n')
    handle.write(f'# window_s: {args.window}  watching: {args.watch} '
                 f'(pid {sampler.pid})\n')
    handle.write(f'# note: {args.note}\n')
    if missing:
        handle.write(f'# NOT SUBSCRIBED (never appeared): {" ".join(missing)}\n')
    handle.write('# t=0 is when this script started — restart the node first, '
                 'not the board.\n')
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    handle.flush()

    print(f'HW-BUG-8 topic rate log -> {out_path}')
    print(f'  watching {args.watch}: pid {sampler.pid or "not found"}')
    print(f'  topics   {" ".join(args.topics)}')
    print('  No motion. Stop with Ctrl+C — every completed row is already on disk.')
    print()
    header = (f'{"uptime":>8} | ' + ' | '.join(f'{t.split("/")[-1]:>12}' for t in args.topics)
              + f' | {"cpu%":>6} | {"rss MiB":>8}')
    print(header)
    print('-' * len(header))

    sampler.sample()   # prime the CPU delta
    t_start = time.time()
    window_start = t_start
    rows = 0

    try:
        while rclpy.ok():
            if args.duration > 0 and (time.time() - t_start) >= args.duration:
                break
            rclpy.spin_once(node, timeout_sec=SPIN_TIMEOUT_S)

            now = time.time()
            elapsed = now - window_start
            if elapsed < args.window:
                continue

            counts = node.drain()
            cpu, rss = sampler.sample()
            uptime = now - t_start
            row = {
                'iso_time': datetime.now().isoformat(timespec='seconds'),
                'uptime_s': round(uptime, 1),
                'uptime_min': round(uptime / 60.0, 2),
                'window_s': round(elapsed, 2),
                'watched_cpu_pct': cpu,
                'watched_rss_mib': rss,
            }
            for topic in args.topics:
                row[column_of[topic]] = round(counts.get(topic, 0) / elapsed, 3)

            writer.writerow(row)
            handle.flush()
            os.fsync(handle.fileno())
            rows += 1

            print(f'{uptime/60:7.1f}m | '
                  + ' | '.join(f'{row[column_of[t]]:12.2f}' for t in args.topics)
                  + f' | {cpu if cpu != "" else "-":>6} | {rss if rss != "" else "-":>8}')

            window_start = now

    except KeyboardInterrupt:
        pass
    finally:
        handle.close()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

    print()
    print(f'{rows} rows written to {out_path}')
    print('A falling rate with a climbing RSS is an accumulation bug in the node.')
    print('A falling rate with flat RSS points at the executor or the read thread.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
