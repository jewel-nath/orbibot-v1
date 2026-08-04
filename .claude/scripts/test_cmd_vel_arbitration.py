#!/usr/bin/env python3
"""
Phase 2 acceptance tests — docs/architecture/command-pipeline.md.

Pure topic arbitration: this publishes to twist_mux's INPUT topics and watches
its OUTPUT. Motors are disabled throughout and nothing is ever sent to the
driver that the mux did not itself decide on, so the robot cannot move.

Distinct speeds per source so the winner is unambiguous in the output.
"""

import time

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node

NAV, WEB, AGENT, ESTOP, JOY = 0.31, 0.22, 0.13, 0.0, 0.44
RATE = 20.0


class MuxTest(Node):
    def __init__(self):
        super().__init__('mux_test')
        self.pubs = {
            n: self.create_publisher(Twist, f'/cmd_vel_{n}', 10)
            for n in ('nav_out', 'web', 'agent', 'estop', 'joy')
        }
        self.create_subscription(Twist, '/cmd_vel', self._out, 10)
        self.last = None
        self.results = []

    def _out(self, msg):
        self.last = msg.linear.x

    def spin(self, seconds):
        end = time.time() + seconds
        while time.time() < end and rclpy.ok():
            rclpy.spin_once(self, timeout_sec=0.01)

    def drive(self, sources, seconds):
        """Publish the given {name: vx} at RATE for `seconds`, return last output."""
        end = time.time() + seconds
        period = 1.0 / RATE
        while time.time() < end and rclpy.ok():
            for name, vx in sources.items():
                m = Twist()
                m.linear.x = vx
                self.pubs[name].publish(m)
            self.spin(period)
        return self.last

    def check(self, label, got, want, tol=0.005):
        ok = got is not None and abs(got - want) < tol
        self.results.append(ok)
        got_s = 'None' if got is None else f'{got:.3f}'
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}: /cmd_vel={got_s} want={want:.3f}")
        return ok


def main():
    rclpy.init()
    n = MuxTest()
    n.spin(2.0)
    print('=== Phase 2 acceptance — command-pipeline.md ===')

    # 1. Nav2 alone drives.
    n.check('nav alone', n.drive({'nav_out': NAV}, 2.0), NAV)

    # 2. Web beats Nav2 — "the human always wins".
    n.check('web (200) beats nav (50)', n.drive({'nav_out': NAV, 'web': WEB}, 2.0), WEB)

    # 3. Web beats the agent. Phase 8.2's safety property.
    n.check('web (200) beats agent (100)',
            n.drive({'agent': AGENT, 'web': WEB}, 2.0), WEB)

    # 4. Agent beats Nav2 but loses to web.
    n.check('agent (100) beats nav (50)',
            n.drive({'nav_out': NAV, 'agent': AGENT}, 2.0), AGENT)

    # 5. Reserved joystick slot outranks the dashboard.
    n.check('joy (220) beats web (200)', n.drive({'web': WEB, 'joy': JOY}, 2.0), JOY)

    # 6. E-stop beats everything, including the joystick.
    n.check('estop (255) beats all',
            n.drive({'nav_out': NAV, 'web': WEB, 'agent': AGENT,
                     'joy': JOY, 'estop': ESTOP}, 2.0), 0.0)

    # 7. Silence means stop: drop the winning source, the next takes over.
    n.drive({'nav_out': NAV, 'web': WEB}, 1.5)
    fell_back = n.drive({'nav_out': NAV}, 1.5)     # web goes quiet
    n.check('web goes silent -> nav takes over', fell_back, NAV)

    # 8. All sources silent -> the mux publishes zero, measured.
    n.drive({'web': WEB}, 1.5)
    t0 = time.time()
    stopped_at = None
    while time.time() - t0 < 3.0:
        n.spin(0.01)
        if n.last is not None and abs(n.last) < 1e-6:
            stopped_at = time.time() - t0
            break
    if stopped_at is None:
        print(f"  [FAIL] all silent -> stop: still {n.last} after 3.0 s")
        n.results.append(False)
    else:
        # 0.3 s timeout plus the mux's own tick; anything under 0.5 s is correct
        ok = stopped_at < 0.5
        n.results.append(ok)
        print(f"  [{'PASS' if ok else 'FAIL'}] all silent -> stop in "
              f"{stopped_at*1000:.0f} ms (web timeout 0.3 s)")

    print(f"\n  {sum(n.results)}/{len(n.results)} passed")
    n.destroy_node()
    rclpy.shutdown()
    return 0 if all(n.results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
