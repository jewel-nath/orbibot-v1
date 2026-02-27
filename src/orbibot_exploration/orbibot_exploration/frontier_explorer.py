#!/usr/bin/env python3
"""
frontier_explorer.py - Autonomous frontier-based exploration node for OrbiBot

Main exploration node that:
1. Subscribes to /map for occupancy grid
2. Uses TF2 to get robot pose
3. Detects frontiers using BFS algorithm (from m-explore-ros2)
4. Sends goals to Nav2 via navigate_to_pose action
5. Blacklists unreachable frontiers
6. Tracks progress and times out stuck goals
7. Returns to initial position when exploration complete

Topics Published:
    /orbibot/exploration/status (std_msgs/String): Current exploration state
    /orbibot/exploration/frontiers (visualization_msgs/MarkerArray): Frontier visualization

Topics Subscribed:
    /map (nav_msgs/OccupancyGrid): SLAM map
    /orbibot/exploration/command (std_msgs/String): Control commands (start/stop/pause)

Actions Used:
    navigate_to_pose (nav2_msgs/NavigateToPose): Navigation goals
"""

import math
from typing import List, Optional, Tuple

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.time import Time

from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import Point, Pose, PoseStamped
from std_msgs.msg import String, ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray
from nav2_msgs.action import NavigateToPose

from action_msgs.msg import GoalStatus
import tf2_ros
from tf2_ros import TransformException

from orbibot_exploration.utils.frontier_detection import (
    search_frontiers,
    Frontier,
)


# Exploration states
STATE_IDLE = "idle"
STATE_EXPLORING = "exploring"
STATE_NAVIGATING = "navigating"
STATE_RETURNING = "returning"
STATE_COMPLETE = "complete"
STATE_STOPPED = "stopped"


class FrontierExplorer(Node):
    """Autonomous frontier-based exploration node."""

    def __init__(self):
        super().__init__('frontier_explorer')

        # Declare parameters
        self._declare_parameters()

        # Get parameters
        self._planner_frequency = self.get_parameter('planner_frequency').value
        self._progress_timeout = self.get_parameter('progress_timeout').value
        self._min_frontier_size = self.get_parameter('min_frontier_size').value
        self._goal_tolerance = self.get_parameter('goal_tolerance').value
        self._transform_tolerance = self.get_parameter('transform_tolerance').value
        self._return_to_init = self.get_parameter('return_to_init').value
        self._potential_scale = self.get_parameter('potential_scale').value
        self._gain_scale = self.get_parameter('gain_scale').value
        self._map_frame = self.get_parameter('map_frame').value
        self._robot_base_frame = self.get_parameter('robot_base_frame').value
        self._visualize = self.get_parameter('visualize_frontiers').value
        self._navigate_action = self.get_parameter('navigate_action').value

        # State
        self._state = STATE_IDLE
        self._map_data: Optional[OccupancyGrid] = None
        self._current_goal: Optional[Tuple[float, float]] = None
        self._prev_goal: Optional[Tuple[float, float]] = None
        self._prev_distance = 0.0
        self._last_progress_time: Optional[Time] = None
        self._initial_pose: Optional[Pose] = None
        self._frontier_blacklist: List[Tuple[float, float]] = []
        self._goal_handle = None

        # Callback group for concurrent execution
        self._callback_group = ReentrantCallbackGroup()

        # TF2 buffer and listener
        self._tf_buffer = tf2_ros.Buffer()
        self._tf_listener = tf2_ros.TransformListener(self._tf_buffer, self)

        # QoS for map (latched topic)
        map_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            depth=1
        )

        # Subscribers
        self._map_sub = self.create_subscription(
            OccupancyGrid,
            '/map',
            self._map_callback,
            map_qos
        )

        self._command_sub = self.create_subscription(
            String,
            '/orbibot/exploration/command',
            self._command_callback,
            10
        )

        # Publishers
        self._status_pub = self.create_publisher(
            String,
            '/orbibot/exploration/status',
            10
        )

        if self._visualize:
            self._marker_pub = self.create_publisher(
                MarkerArray,
                '/orbibot/exploration/frontiers',
                10
            )

        # Navigation action client
        self._nav_client = ActionClient(
            self,
            NavigateToPose,
            self._navigate_action,
            callback_group=self._callback_group
        )

        # Planning timer (created when exploration starts)
        self._planning_timer = None

        # Status publishing timer
        self._status_timer = self.create_timer(1.0, self._publish_status)

        self.get_logger().info(
            f'[Exploration] Frontier explorer ready — '
            f'freq: {self._planner_frequency}Hz, '
            f'min_frontier: {self._min_frontier_size}m'
        )
        self.get_logger().info(
            '[Exploration] Send "start" to /orbibot/exploration/command to begin'
        )

    def _declare_parameters(self):
        """Declare all ROS 2 parameters."""
        self.declare_parameter('planner_frequency', 0.5)
        self.declare_parameter('progress_timeout', 30.0)
        self.declare_parameter('min_frontier_size', 0.5)
        self.declare_parameter('goal_tolerance', 0.3)
        self.declare_parameter('transform_tolerance', 1.0)
        self.declare_parameter('return_to_init', True)
        self.declare_parameter('potential_scale', 3.0)
        self.declare_parameter('gain_scale', 1.0)
        self.declare_parameter('map_frame', 'map')
        self.declare_parameter('robot_base_frame', 'base_footprint')
        self.declare_parameter('visualize_frontiers', True)
        self.declare_parameter('navigate_action', 'navigate_to_pose')

    def _map_callback(self, msg: OccupancyGrid):
        """Store the latest map data."""
        self._map_data = msg

    def _command_callback(self, msg: String):
        """Handle exploration commands."""
        command = msg.data.lower().strip()

        if command == 'start':
            self._start_exploration()
        elif command == 'stop':
            self._stop_exploration()
        elif command == 'pause':
            self._pause_exploration()
        elif command == 'resume':
            self._resume_exploration()
        else:
            self.get_logger().warn(f'Unknown command: {command}')

    def _publish_status(self):
        """Publish current exploration status."""
        msg = String()
        msg.data = self._state
        self._status_pub.publish(msg)

    def _get_robot_pose(self) -> Optional[Tuple[float, float, float]]:
        """
        Get robot pose from TF.

        Returns:
            Tuple of (x, y, yaw) or None if transform unavailable
        """
        try:
            transform = self._tf_buffer.lookup_transform(
                self._map_frame,
                self._robot_base_frame,
                rclpy.time.Time(),
                timeout=rclpy.duration.Duration(seconds=self._transform_tolerance)
            )

            x = transform.transform.translation.x
            y = transform.transform.translation.y

            # Extract yaw from quaternion
            q = transform.transform.rotation
            siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
            cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
            yaw = math.atan2(siny_cosp, cosy_cosp)

            return (x, y, yaw)

        except TransformException as ex:
            self.get_logger().warn(f'Could not get robot pose: {ex}')
            return None

    def _start_exploration(self):
        """Start autonomous exploration."""
        if self._state == STATE_EXPLORING or self._state == STATE_NAVIGATING:
            self.get_logger().info('Exploration already running')
            return

        # Wait for action server
        self.get_logger().info('Waiting for navigation action server...')
        if not self._nav_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error('Navigation action server not available!')
            return

        self.get_logger().info('Connected to navigation server')

        # Record initial pose if return_to_init is enabled
        if self._return_to_init:
            pose = self._get_robot_pose()
            if pose:
                self._initial_pose = Pose()
                self._initial_pose.position.x = pose[0]
                self._initial_pose.position.y = pose[1]
                self._initial_pose.orientation.w = 1.0
                self.get_logger().info(
                    f'Initial pose recorded: ({pose[0]:.2f}, {pose[1]:.2f})'
                )

        # Reset state
        self._frontier_blacklist = []
        self._prev_goal = None
        self._prev_distance = 0.0
        self._state = STATE_EXPLORING

        # Start planning timer
        period = 1.0 / self._planner_frequency
        self._planning_timer = self.create_timer(period, self._make_plan)

        self.get_logger().info('Exploration started!')

        # Make first plan immediately
        self._make_plan()

    def _stop_exploration(self):
        """Stop exploration completely."""
        self.get_logger().info('Stopping exploration...')

        # Cancel current goal
        if self._goal_handle:
            self._goal_handle.cancel_goal_async()
            self._goal_handle = None

        # Stop planning timer
        if self._planning_timer:
            self._planning_timer.cancel()
            self._planning_timer = None

        self._state = STATE_STOPPED
        self.get_logger().info('Exploration stopped')

    def _pause_exploration(self):
        """Pause exploration (can be resumed)."""
        if self._state not in [STATE_EXPLORING, STATE_NAVIGATING]:
            return

        # Cancel current goal
        if self._goal_handle:
            self._goal_handle.cancel_goal_async()

        # Stop planning timer
        if self._planning_timer:
            self._planning_timer.cancel()

        self._state = STATE_IDLE
        self.get_logger().info('Exploration paused')

    def _resume_exploration(self):
        """Resume paused exploration."""
        if self._state != STATE_IDLE:
            self.get_logger().info('Cannot resume - not paused')
            return

        self._state = STATE_EXPLORING

        # Restart planning timer
        period = 1.0 / self._planner_frequency
        self._planning_timer = self.create_timer(period, self._make_plan)

        self.get_logger().info('Exploration resumed')
        self._make_plan()

    def _is_goal_blacklisted(self, x: float, y: float) -> bool:
        """Check if a goal is in the blacklist."""
        tolerance = 5 * self._map_data.info.resolution if self._map_data else 0.25

        for bx, by in self._frontier_blacklist:
            if abs(x - bx) < tolerance and abs(y - by) < tolerance:
                return True
        return False

    def _same_goal(self, x: float, y: float) -> bool:
        """Check if this is the same goal as current."""
        if self._prev_goal is None:
            return False
        dx = x - self._prev_goal[0]
        dy = y - self._prev_goal[1]
        return math.sqrt(dx * dx + dy * dy) < 0.1

    def _make_plan(self):
        """Find frontiers and send navigation goal."""
        if self._state not in [STATE_EXPLORING, STATE_NAVIGATING]:
            return

        if self._map_data is None:
            self.get_logger().warn('No map data available')
            return

        # Get robot pose
        pose = self._get_robot_pose()
        if pose is None:
            return

        robot_x, robot_y, _ = pose

        # Search for frontiers
        map_array = np.array(self._map_data.data, dtype=np.int8)
        frontiers = search_frontiers(
            robot_x=robot_x,
            robot_y=robot_y,
            map_data=map_array,
            width=self._map_data.info.width,
            height=self._map_data.info.height,
            resolution=self._map_data.info.resolution,
            origin_x=self._map_data.info.origin.position.x,
            origin_y=self._map_data.info.origin.position.y,
            min_frontier_size=self._min_frontier_size,
            potential_scale=self._potential_scale,
            gain_scale=self._gain_scale
        )

        self.get_logger().debug(f'Found {len(frontiers)} frontiers')

        # Visualize frontiers
        if self._visualize and frontiers:
            self._visualize_frontiers(frontiers)

        # Check if exploration is complete
        if not frontiers:
            self.get_logger().info('No frontiers found - exploration complete!')
            self._exploration_complete()
            return

        # Find first non-blacklisted frontier
        target_frontier = None
        for frontier in frontiers:
            if not self._is_goal_blacklisted(frontier.centroid_x, frontier.centroid_y):
                target_frontier = frontier
                break

        if target_frontier is None:
            self.get_logger().info('All frontiers blacklisted - exploration complete!')
            self._exploration_complete()
            return

        target_x = target_frontier.centroid_x
        target_y = target_frontier.centroid_y

        # Check progress timeout
        same_goal = self._same_goal(target_x, target_y)

        if not same_goal or self._prev_distance > target_frontier.min_distance:
            # Making progress
            self._last_progress_time = self.get_clock().now()
            self._prev_distance = target_frontier.min_distance
        elif self._last_progress_time:
            # Check for timeout
            elapsed = (self.get_clock().now() - self._last_progress_time).nanoseconds / 1e9
            if elapsed > self._progress_timeout:
                self.get_logger().warn(
                    f'No progress for {elapsed:.1f}s, blacklisting frontier'
                )
                self._frontier_blacklist.append((target_x, target_y))
                self._make_plan()  # Try next frontier
                return

        self._prev_goal = (target_x, target_y)

        # Don't resend same goal
        if same_goal and self._state == STATE_NAVIGATING:
            return

        # Send navigation goal
        self._send_goal(target_x, target_y)

    def _send_goal(self, x: float, y: float):
        """Send navigation goal to Nav2."""
        self.get_logger().info(f'Navigating to frontier at ({x:.2f}, {y:.2f})')

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = self._map_frame
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()
        goal_msg.pose.pose.position.x = x
        goal_msg.pose.pose.position.y = y
        goal_msg.pose.pose.orientation.w = 1.0

        self._state = STATE_NAVIGATING
        self._current_goal = (x, y)

        send_goal_future = self._nav_client.send_goal_async(
            goal_msg,
            feedback_callback=self._goal_feedback_callback
        )
        send_goal_future.add_done_callback(self._goal_response_callback)

    def _goal_response_callback(self, future):
        """Handle goal response from Nav2."""
        self._goal_handle = future.result()

        if not self._goal_handle.accepted:
            self.get_logger().warn('Goal rejected by Nav2')
            if self._current_goal:
                self._frontier_blacklist.append(self._current_goal)
            self._state = STATE_EXPLORING
            return

        self.get_logger().debug('Goal accepted')
        result_future = self._goal_handle.get_result_async()
        result_future.add_done_callback(self._goal_result_callback)

    def _goal_feedback_callback(self, feedback_msg):
        """Handle navigation feedback."""

    def _goal_result_callback(self, future):
        """Handle navigation result."""
        result = future.result()
        status = result.status

        if status == GoalStatus.STATUS_SUCCEEDED:
            self.get_logger().info('Reached frontier successfully')
        elif status == GoalStatus.STATUS_CANCELED:
            self.get_logger().info('Navigation canceled')
            return
        elif status == GoalStatus.STATUS_ABORTED:
            self.get_logger().warn('Navigation aborted, blacklisting goal')
            if self._current_goal:
                self._frontier_blacklist.append(self._current_goal)

        self._state = STATE_EXPLORING
        self._goal_handle = None

        # Plan next frontier
        if self._state != STATE_STOPPED:
            self._make_plan()

    def _exploration_complete(self):
        """Handle exploration completion."""
        # Stop planning timer
        if self._planning_timer:
            self._planning_timer.cancel()
            self._planning_timer = None

        if self._return_to_init and self._initial_pose:
            self.get_logger().info('Returning to initial position...')
            self._state = STATE_RETURNING
            self._send_goal(
                self._initial_pose.position.x,
                self._initial_pose.position.y
            )
        else:
            self._state = STATE_COMPLETE
            self.get_logger().info('Exploration complete!')

    def _visualize_frontiers(self, frontiers: List[Frontier]):
        """Publish frontier visualization markers."""
        markers = MarkerArray()

        # Delete old markers
        delete_marker = Marker()
        delete_marker.action = Marker.DELETEALL
        markers.markers.append(delete_marker)

        for i, frontier in enumerate(frontiers):
            # Frontier points marker
            points_marker = Marker()
            points_marker.header.frame_id = self._map_frame
            points_marker.header.stamp = self.get_clock().now().to_msg()
            points_marker.ns = 'frontiers'
            points_marker.id = i * 2
            points_marker.type = Marker.POINTS
            points_marker.action = Marker.ADD
            points_marker.scale.x = 0.1
            points_marker.scale.y = 0.1

            # Color: blue for valid, red for blacklisted
            if self._is_goal_blacklisted(frontier.centroid_x, frontier.centroid_y):
                points_marker.color = ColorRGBA(r=1.0, g=0.0, b=0.0, a=0.8)
            else:
                points_marker.color = ColorRGBA(r=0.0, g=0.0, b=1.0, a=0.8)

            for px, py in frontier.points:
                p = Point()
                p.x = px
                p.y = py
                p.z = 0.05
                points_marker.points.append(p)

            markers.markers.append(points_marker)

            # Centroid marker (sphere)
            centroid_marker = Marker()
            centroid_marker.header.frame_id = self._map_frame
            centroid_marker.header.stamp = self.get_clock().now().to_msg()
            centroid_marker.ns = 'centroids'
            centroid_marker.id = i * 2 + 1
            centroid_marker.type = Marker.SPHERE
            centroid_marker.action = Marker.ADD
            centroid_marker.pose.position.x = frontier.centroid_x
            centroid_marker.pose.position.y = frontier.centroid_y
            centroid_marker.pose.position.z = 0.1
            centroid_marker.scale.x = 0.3
            centroid_marker.scale.y = 0.3
            centroid_marker.scale.z = 0.3
            centroid_marker.color = ColorRGBA(r=0.0, g=1.0, b=0.0, a=0.8)

            markers.markers.append(centroid_marker)

        self._marker_pub.publish(markers)


def main(args=None):
    """Main entry point."""
    rclpy.init(args=args)

    node = FrontierExplorer()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info('Exploration stopped by user')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
