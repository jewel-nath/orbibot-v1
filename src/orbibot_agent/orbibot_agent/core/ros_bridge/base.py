"""ROS bridge core — shared state, message waiting, and utility methods."""

import logging
import math
import threading
from typing import Any, Dict, Optional

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data

logger = logging.getLogger(__name__)


class RosBridgeBase:
    """Core infrastructure shared by all bridge mixins.

    Holds the ROS node reference, safety manager, caches for subscriptions,
    service clients, action clients, and publishers. Also provides the
    wait_for_message pattern and message-field utilities.
    """

    def __init__(self, node: Node):
        self._node = node
        self._safety_manager = None

        # Caches (created on demand by mixins)
        self._subscriptions: Dict[str, Any] = {}
        self._latest_messages: Dict[str, Any] = {}
        self._action_clients: Dict[str, ActionClient] = {}
        self._active_goals: Dict[str, Dict] = {}
        self._service_clients: Dict[str, Any] = {}
        self._topic_publishers: Dict[str, Any] = {}

        logger.info('RosBridge initialized')

    def set_safety_manager(self, safety_manager) -> None:
        self._safety_manager = safety_manager

    # -- Message waiting --

    def wait_for_message(
        self,
        msg_type: type,
        topic: str,
        timeout: Optional[float] = None,
        qos=None,
    ) -> Optional[Any]:
        """Block until one message arrives on a topic, then return it."""
        timeout = timeout or (self._safety_manager.sensor_timeout if self._safety_manager else 3.0)

        result = [None]
        event = threading.Event()

        def _callback(msg):
            result[0] = msg
            event.set()

        profile = qos or qos_profile_sensor_data
        sub = self._node.create_subscription(msg_type, topic, _callback, profile)

        event.wait(timeout=timeout)
        self._node.destroy_subscription(sub)

        if result[0] is None:
            logger.warning(f'Timeout waiting for message on {topic}')

        return result[0]

    # -- Quaternion / yaw utilities --

    @staticmethod
    def _quat_to_yaw(q) -> float:
        """Convert quaternion to yaw in degrees."""
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        return math.degrees(math.atan2(siny_cosp, cosy_cosp))

    @staticmethod
    def _yaw_to_quaternion(yaw_deg: float) -> Dict[str, float]:
        """Convert yaw in degrees to a quaternion dict (z-axis rotation only)."""
        yaw = math.radians(yaw_deg)
        return {
            'x': 0.0,
            'y': 0.0,
            'z': round(math.sin(yaw / 2.0), 6),
            'w': round(math.cos(yaw / 2.0), 6),
        }

    # -- Message field setter (recursive) --

    def _set_message_fields(self, msg: Any, data: Dict[str, Any]):
        """Set ROS message fields from a nested dictionary."""
        for key, value in data.items():
            if hasattr(msg, key):
                attr = getattr(msg, key)
                if hasattr(attr, '__slots__'):
                    self._set_message_fields(attr, value)
                else:
                    setattr(msg, key, value)
