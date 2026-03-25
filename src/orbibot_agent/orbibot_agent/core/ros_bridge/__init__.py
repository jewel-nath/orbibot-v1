"""ROS 2 bridge for OrbiBot Agent.

Composes focused mixins into a single RosBridge class.
Import as: from orbibot_agent.core.ros_bridge import RosBridge
"""

from rclpy.node import Node

from .base import RosBridgeBase
from .motion import MotionMixin
from .sensors import SensorsMixin
from .firmware import FirmwareMixin
from .services import ServicesMixin
from .actions import ActionsMixin
from .navigation import NavigationMixin


class RosBridge(
    RosBridgeBase,
    MotionMixin,
    SensorsMixin,
    FirmwareMixin,
    ServicesMixin,
    ActionsMixin,
    NavigationMixin,
):
    """Unified ROS 2 bridge composing all communication concerns.

    Modules:
      base.py       — shared state, wait_for_message, utilities
      motion.py     — velocity publishing, move_for_duration
      sensors.py    — battery, IMU, encoders, odometry, LiDAR, etc.
      firmware.py   — PID, beep, calibration, reset, firmware version
      services.py   — dynamic service calling, topic listing/publishing
      actions.py    — action client management, goal tracking
      navigation.py — Nav2, SLAM, AMCL, exploration wrappers
    """

    def __init__(self, node: Node):
        super().__init__(node)
        self._init_motion()
        self._init_firmware()
