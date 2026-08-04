"""Motion control — velocity publishing, move_for_duration, stop."""

import logging
import time
from typing import Any, Callable, Dict, Optional

from geometry_msgs.msg import Twist

logger = logging.getLogger(__name__)


class MotionMixin:
    """Velocity command publishing and timed movement."""

    def _init_motion(self):
        """Create motion publishers. Called by RosBridge.__init__."""
        # Arbitrated by twist_mux at priority 100 — below the dashboard, so an
        # operator's stick always preempts the agent. Never publish /cmd_vel
        # directly: see docs/architecture/command-pipeline.md.
        self._cmd_vel_pub = self._node.create_publisher(
            Twist, '/cmd_vel_agent', 10)

    def publish_cmd_vel(self, vx: float, vy: float, wz: float) -> None:
        """Publish a velocity command, clamped by safety limits."""
        if self._safety_manager:
            vx, vy, wz = self._safety_manager.validate_velocity(vx, vy, wz)
            if self._safety_manager.check_emergency_stop():
                logger.warning('Emergency stop active — blocking cmd_vel')
                vx, vy, wz = 0.0, 0.0, 0.0

        msg = Twist()
        msg.linear.x = float(vx)
        msg.linear.y = float(vy)
        msg.angular.z = float(wz)
        self._cmd_vel_pub.publish(msg)

    def publish_stop(self) -> None:
        """Publish zero velocity (emergency stop)."""
        self.publish_cmd_vel(0.0, 0.0, 0.0)
        logger.info('Published stop command')

    def move_for_duration(
        self,
        vx: float,
        vy: float,
        wz: float,
        duration: float,
        callback: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Move the robot at constant velocity for a given duration."""
        if self._safety_manager:
            vx, vy, wz = self._safety_manager.validate_velocity(vx, vy, wz)
            duration = self._safety_manager.validate_duration(duration)

        hz = 10
        steps = int(duration * hz)

        logger.info(f'Moving: vx={vx}, vy={vy}, wz={wz} for {duration}s')

        for i in range(steps):
            if self._safety_manager and self._safety_manager.check_emergency_stop():
                logger.warning('Emergency stop during movement')
                break
            self.publish_cmd_vel(vx, vy, wz)
            time.sleep(1.0 / hz)
            if callback:
                callback(i / steps)

        self.publish_stop()
        return {'status': 'completed', 'vx': vx, 'vy': vy, 'wz': wz, 'duration': duration}
