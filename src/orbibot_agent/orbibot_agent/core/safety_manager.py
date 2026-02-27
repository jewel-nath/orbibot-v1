"""Safety manager for OrbiBot Agent.

Enforces velocity limits, duration caps, and emergency stop functionality.
All robot movements go through safety validation.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class SafetyManager:
    """Manages safety constraints for robot operations."""

    # Default safety limits
    DEFAULT_MAX_LINEAR_VEL = 0.5  # m/s
    DEFAULT_MAX_ANGULAR_VEL = 2.0  # rad/s
    DEFAULT_MAX_DURATION = 10.0  # seconds
    DEFAULT_SENSOR_TIMEOUT = 3.0  # seconds

    def __init__(
        self,
        max_linear_vel: Optional[float] = None,
        max_angular_vel: Optional[float] = None,
        max_duration: Optional[float] = None,
        sensor_timeout: Optional[float] = None,
    ):
        """Initialize safety manager with configurable limits.

        Args:
            max_linear_vel: Maximum linear velocity in m/s
            max_angular_vel: Maximum angular velocity in rad/s
            max_duration: Maximum movement duration in seconds
            sensor_timeout: Timeout for sensor reads in seconds
        """
        self.max_linear_vel = max_linear_vel or self.DEFAULT_MAX_LINEAR_VEL
        self.max_angular_vel = max_angular_vel or self.DEFAULT_MAX_ANGULAR_VEL
        self.max_duration = max_duration or self.DEFAULT_MAX_DURATION
        self.sensor_timeout = sensor_timeout or self.DEFAULT_SENSOR_TIMEOUT

        self._emergency_stop_active = False

        logger.info(
            'SafetyManager initialized with limits: '
            f'linear={self.max_linear_vel}m/s, '
            f'angular={self.max_angular_vel}rad/s, '
            f'duration={self.max_duration}s'
        )

    def validate_velocity(
        self, vx: float, vy: float, wz: float
    ) -> Tuple[float, float, float]:
        """Validate and clamp velocity commands.

        Args:
            vx: Forward/backward velocity
            vy: Left/right velocity (for mecanum)
            wz: Angular velocity

        Returns:
            Tuple of clamped (vx, vy, wz)
        """
        vx = max(-self.max_linear_vel, min(self.max_linear_vel, float(vx)))
        vy = max(-self.max_linear_vel, min(self.max_linear_vel, float(vy)))
        wz = max(-self.max_angular_vel, min(self.max_angular_vel, float(wz)))

        return vx, vy, wz

    def validate_duration(self, duration: float) -> float:
        """Validate and clamp movement duration.

        Args:
            duration: Requested duration in seconds

        Returns:
            Clamped duration
        """
        return max(0.1, min(self.max_duration, float(duration)))

    def check_emergency_stop(self) -> bool:
        """Check if emergency stop is active.

        Returns:
            True if emergency stop is active
        """
        return self._emergency_stop_active

    def activate_emergency_stop(self) -> None:
        """Activate emergency stop."""
        self._emergency_stop_active = True
        logger.warning('EMERGENCY STOP ACTIVATED')

    def reset_emergency_stop(self) -> None:
        """Reset emergency stop."""
        self._emergency_stop_active = False
        logger.info('Emergency stop reset')

    def get_safety_status(self) -> dict:
        """Get current safety status.

        Returns:
            Dictionary with safety information
        """
        return {
            'emergency_stop_active': self._emergency_stop_active,
            'max_linear_vel': self.max_linear_vel,
            'max_angular_vel': self.max_angular_vel,
            'max_duration': self.max_duration,
            'sensor_timeout': self.sensor_timeout,
        }