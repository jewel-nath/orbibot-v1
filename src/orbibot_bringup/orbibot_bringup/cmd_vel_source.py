#!/usr/bin/env python3
"""
Publishes which command source is currently driving the robot.

Roadmap 2.5. The operator should never have to guess who has control, and
"who is driving?" should be answerable without reading a launch file.

`twist_mux` already knows, but only exposes it inside a `DiagnosticArray` on
`/diagnostics`, one entry per input, each reading either

    ' masked (listening to cmd_vel_web @ 0.300000s with priority #200)'
    ' unmasked (listening to cmd_vel_idle @ 0.500000s with priority #1)'

**unmasked** is the one currently winning; everything else is masked by it. That
is a fine internal representation and a poor thing to ask a browser to parse, so
this node distils it to a single string on `/orbibot/cmd_vel_source`.

Values are the input names from `config/twist_mux.yaml` — `estop`, `joystick`,
`web`, `agent`, `navigation`, `idle` — or `none` if twist_mux has not reported
yet. `idle` means nothing is commanding motion, which is not the same as the
robot being unable to move, and the dashboard should show the difference.
"""

import re

import rclpy
from diagnostic_msgs.msg import DiagnosticArray
from rclpy.node import Node
from rclpy.qos import QoSDurabilityPolicy, QoSHistoryPolicy, QoSProfile, QoSReliabilityPolicy
from std_msgs.msg import String

SOURCE_TOPIC = '/orbibot/cmd_vel_source'
DIAGNOSTIC_NAME_FRAGMENT = 'twist_mux'
KEY_PREFIX = 'velocity topics.'
NO_SOURCE = 'none'

# ' unmasked (listening to cmd_vel_web @ 0.3s with priority #200)'
# Anchored on the word boundary because 'masked' is a substring of 'unmasked'.
_STATE_RE = re.compile(r'^\s*(un)?masked\b')
_PRIORITY_RE = re.compile(r'priority\s+#(\d+)')


class CmdVelSource(Node):
    """Distils twist_mux's diagnostics into one topic naming the active source."""

    def __init__(self):
        super().__init__('cmd_vel_source')

        # Latched: a dashboard connecting late must learn who is driving without
        # waiting for the next diagnostics tick.
        latched = QoSProfile(
            depth=1,
            history=QoSHistoryPolicy.KEEP_LAST,
            reliability=QoSReliabilityPolicy.RELIABLE,
            durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
        )
        self._publisher = self.create_publisher(String, SOURCE_TOPIC, latched)
        self.create_subscription(
            DiagnosticArray, '/diagnostics', self._diagnostics_callback, 10)

        self._last_source = None
        self._publish(NO_SOURCE)

        self.get_logger().info(
            f'[Bringup] Active command source published on {SOURCE_TOPIC}')

    def _diagnostics_callback(self, msg: DiagnosticArray) -> None:
        """Find the unmasked twist_mux input and publish its name."""
        for status in msg.status:
            if DIAGNOSTIC_NAME_FRAGMENT not in status.name:
                continue

            active, best_priority = NO_SOURCE, -1
            for entry in status.values:
                if not entry.key.startswith(KEY_PREFIX):
                    continue
                state = _STATE_RE.match(entry.value)
                if not state or not state.group(1):     # group(1) == 'un'
                    continue
                priority = _PRIORITY_RE.search(entry.value)
                priority = int(priority.group(1)) if priority else 0
                # More than one input can read unmasked in the moment a source
                # times out. The highest priority is the one actually driving.
                if priority > best_priority:
                    active, best_priority = entry.key[len(KEY_PREFIX):], priority

            self._publish(active)
            return

    def _publish(self, source: str) -> None:
        """Publish on change only — this is for display, not a control signal."""
        if source == self._last_source:
            return
        self._last_source = source
        self._publisher.publish(String(data=source))
        self.get_logger().info(f'Command source: {source}')


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelSource()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
