#!/usr/bin/env python3
"""
obstacle_detector.py - LiDAR-based obstacle detection node for OrbiBot

Monitors the /scan topic and publishes obstacle warnings for safety.
Provides sector-based detection for full 360° awareness.

Topics Published:
  - /orbibot/obstacle_detected (std_msgs/Bool): True if obstacle in any warning zone
  - /orbibot/emergency_stop (std_msgs/Bool): True if obstacle in any emergency zone
  - /orbibot/min_obstacle_distance (std_msgs/Float32): Minimum distance to obstacle
  - /orbibot/obstacle_sectors (std_msgs/Float32MultiArray): Distance per sector [8 values]

Topics Subscribed:
  - /scan (sensor_msgs/LaserScan): LiDAR scan data

Sector Layout (8 sectors, 45° each):
       Front (0)
    FL (1)   FR (7)
   Left (2)   Right (6)
    BL (3)   BR (5)
       Back (4)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import LaserScan
from std_msgs.msg import Bool, Float32, Float32MultiArray
import numpy as np
import math

# Number of sectors (8 = 45° each)
NUM_SECTORS = 8
SECTOR_ANGLE = 2 * math.pi / NUM_SECTORS  # 45 degrees in radians

# Sector names for logging
SECTOR_NAMES = [
    'FRONT', 'FRONT_LEFT', 'LEFT', 'BACK_LEFT',
    'BACK', 'BACK_RIGHT', 'RIGHT', 'FRONT_RIGHT'
]

# Sector indices
SECTOR_FRONT = 0
SECTOR_FRONT_LEFT = 1
SECTOR_LEFT = 2
SECTOR_BACK_LEFT = 3
SECTOR_BACK = 4
SECTOR_BACK_RIGHT = 5
SECTOR_RIGHT = 6
SECTOR_FRONT_RIGHT = 7

# Distance thresholds (meters)
DEFAULT_EMERGENCY_DISTANCE = 0.25   # Trigger emergency stop
DEFAULT_WARNING_DISTANCE = 0.5      # Trigger warning

# Hysteresis to prevent rapid toggling
HYSTERESIS = 0.05


class ObstacleDetector(Node):
    """Detect obstacles from LiDAR with 8-sector awareness."""

    def __init__(self):
        super().__init__('obstacle_detector')

        # Declare and get parameters
        self.declare_parameter('emergency_distance', DEFAULT_EMERGENCY_DISTANCE)
        self.declare_parameter('warning_distance', DEFAULT_WARNING_DISTANCE)
        self.declare_parameter('scan_topic', '/scan')

        self.emergency_distance = self.get_parameter('emergency_distance').value
        self.warning_distance = self.get_parameter('warning_distance').value
        scan_topic = self.get_parameter('scan_topic').value

        # State tracking
        self._obstacle_detected = False
        self._emergency_stop = False
        self._min_distance = float('inf')
        self._sector_distances = [float('inf')] * NUM_SECTORS
        self._sector_warnings = [False] * NUM_SECTORS
        self._sector_emergencies = [False] * NUM_SECTORS

        # QoS for sensor data — depth=1 ensures we always process the freshest scan
        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            depth=1
        )

        # Subscriber
        self.scan_sub = self.create_subscription(
            LaserScan,
            scan_topic,
            self.scan_callback,
            sensor_qos
        )

        # Publishers
        self.obstacle_pub = self.create_publisher(
            Bool, '/orbibot/obstacle_detected', 10
        )
        self.emergency_pub = self.create_publisher(
            Bool, '/orbibot/emergency_stop', 10
        )
        self.distance_pub = self.create_publisher(
            Float32, '/orbibot/min_obstacle_distance', 10
        )
        self.sectors_pub = self.create_publisher(
            Float32MultiArray, '/orbibot/obstacle_sectors', 10
        )

        self.get_logger().info(
            f'Obstacle detector started (8-sector mode). '
            f'Emergency: {self.emergency_distance}m, Warning: {self.warning_distance}m'
        )

    def _angle_to_sector(self, angle: float) -> int:
        """Convert angle (radians, 0=front, CCW positive) to sector index.

        Sector layout:
        - Sector 0 (Front): -22.5° to +22.5°
        - Sector 1 (Front-Left): +22.5° to +67.5°
        - ... and so on CCW
        """
        # Normalize angle to [0, 2*pi)
        norm_angle = angle % (2 * math.pi)

        # Shift by half sector so front is centered on sector 0
        shifted = (norm_angle + SECTOR_ANGLE / 2) % (2 * math.pi)

        return int(shifted / SECTOR_ANGLE)

    def scan_callback(self, msg: LaserScan):
        """Process laser scan for obstacles in all sectors."""
        ranges = np.array(msg.ranges)
        num_readings = len(ranges)

        if num_readings == 0:
            return

        # Generate angle array
        angles = np.linspace(msg.angle_min, msg.angle_max, num_readings)

        # Initialize sector min distances
        sector_min = [float('inf')] * NUM_SECTORS

        # Process each reading
        for i, (angle, distance) in enumerate(zip(angles, ranges)):
            # Skip invalid readings
            if not np.isfinite(distance):
                continue
            if distance < msg.range_min or distance > msg.range_max:
                continue

            # Determine sector for this angle
            sector = self._angle_to_sector(angle)

            # Update sector minimum
            if distance < sector_min[sector]:
                sector_min[sector] = distance

        # Apply hysteresis and determine states per sector
        any_warning = False
        any_emergency = False

        for s in range(NUM_SECTORS):
            distance = sector_min[s]

            # Hysteresis thresholds
            emergency_threshold = (
                self.emergency_distance + HYSTERESIS
                if self._sector_emergencies[s]
                else self.emergency_distance
            )
            warning_threshold = (
                self.warning_distance + HYSTERESIS
                if self._sector_warnings[s]
                else self.warning_distance
            )

            # Determine states
            new_emergency = distance < emergency_threshold
            new_warning = distance < warning_threshold

            # Log state changes
            if new_emergency and not self._sector_emergencies[s]:
                self.get_logger().warn(
                    f'EMERGENCY in {SECTOR_NAMES[s]}: {distance:.2f}m'
                )
            elif not new_emergency and self._sector_emergencies[s]:
                self.get_logger().info(f'{SECTOR_NAMES[s]} emergency cleared')

            if new_warning and not self._sector_warnings[s] and not new_emergency:
                self.get_logger().debug(f'Warning in {SECTOR_NAMES[s]}: {distance:.2f}m')

            # Update sector states
            self._sector_emergencies[s] = new_emergency
            self._sector_warnings[s] = new_warning
            self._sector_distances[s] = distance

            if new_emergency:
                any_emergency = True
            if new_warning:
                any_warning = True

        # Overall minimum distance
        min_distance = min(sector_min)

        # Log overall state changes
        if any_emergency != self._emergency_stop:
            if any_emergency:
                self.get_logger().warn(f'EMERGENCY STOP: Obstacle at {min_distance:.2f}m')
            else:
                self.get_logger().info('All sectors clear of emergency')

        # Update overall states
        self._emergency_stop = any_emergency
        self._obstacle_detected = any_warning
        self._min_distance = min_distance

        # Publish states
        self.obstacle_pub.publish(Bool(data=self._obstacle_detected))
        self.emergency_pub.publish(Bool(data=self._emergency_stop))
        self.distance_pub.publish(Float32(data=float(min_distance)))

        # Publish sector distances
        sectors_msg = Float32MultiArray()
        sectors_msg.data = [float(d) for d in self._sector_distances]
        self.sectors_pub.publish(sectors_msg)

    def get_sector_distance(self, sector: int) -> float:
        """Get minimum distance for a specific sector."""
        if 0 <= sector < NUM_SECTORS:
            return self._sector_distances[sector]
        return float('inf')

    def is_front_clear(self, threshold: float = None) -> bool:
        """Check if front sectors are clear."""
        if threshold is None:
            threshold = self.warning_distance
        front_sectors = [SECTOR_FRONT, SECTOR_FRONT_LEFT, SECTOR_FRONT_RIGHT]
        return all(self._sector_distances[s] > threshold for s in front_sectors)

    def is_back_clear(self, threshold: float = None) -> bool:
        """Check if back sectors are clear."""
        if threshold is None:
            threshold = self.warning_distance
        back_sectors = [SECTOR_BACK, SECTOR_BACK_LEFT, SECTOR_BACK_RIGHT]
        return all(self._sector_distances[s] > threshold for s in back_sectors)


def main(args=None):
    """Main entry point."""
    rclpy.init(args=args)

    node = ObstacleDetector()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
