#!/usr/bin/env python3
"""
Idle velocity source — makes "silence means stop" true.

`twist_mux` is purely event driven: it re-evaluates priorities and publishes
only when one of its inputs receives a message. When *every* input goes silent
it publishes nothing at all, so the last commanded velocity simply remains the
newest message on `/cmd_vel` and nothing ever commands a stop.

Measured 2026-08-04: after the last input message, **zero** messages appeared on
`/cmd_vel` in the following 3 s. The robot still stopped, but only because the
driver's `cmd_timeout` and the firmware's 2 s timeout are backstops — which is
the 2 s worst case that `docs/architecture/command-pipeline.md` set out to
shorten.

This node publishes a zero Twist at a steady rate into the mux's lowest-priority
input. Any real source outranks it, so it changes nothing while the robot is
being driven. The moment every real source goes stale, the next idle message
makes the mux fall through and publish zero — at the timeout of the source that
went quiet, not at the driver's backstop.

Stop latency becomes: that source's timeout + at most one idle period.
For the dashboard that is 0.3 s + 50 ms.
"""

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

DEFAULT_PUBLISH_RATE_HZ = 20.0
DEFAULT_TOPIC = 'cmd_vel_idle'


class CmdVelIdle(Node):
    """Publishes a zero velocity continuously as the mux's fallback input."""

    def __init__(self):
        super().__init__('cmd_vel_idle')

        self.declare_parameter('publish_rate', DEFAULT_PUBLISH_RATE_HZ)
        self.declare_parameter('topic', DEFAULT_TOPIC)

        rate = self.get_parameter('publish_rate').value
        topic = self.get_parameter('topic').value

        if rate <= 0.0:
            self.get_logger().warn(
                f'Invalid publish_rate ({rate}), using {DEFAULT_PUBLISH_RATE_HZ}')
            rate = DEFAULT_PUBLISH_RATE_HZ

        # A single reused message: it is always zero, so there is nothing to set
        # per tick and nothing that can drift.
        self._zero = Twist()

        self._publisher = self.create_publisher(Twist, topic, 10)
        self._timer = self.create_timer(1.0 / rate, self._publish_zero)

        self.get_logger().info(
            f'[Bringup] Idle velocity source — topic: {topic}, rate: {rate:.0f} Hz. '
            'Lowest mux priority; every real source outranks it.')

    def _publish_zero(self) -> None:
        """Publish the zero velocity that the mux falls back to."""
        self._publisher.publish(self._zero)


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelIdle()
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
