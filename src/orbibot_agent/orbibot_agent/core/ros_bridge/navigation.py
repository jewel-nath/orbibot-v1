"""Navigation, SLAM, and exploration — high-level Nav2 wrappers."""

import logging
import math
from typing import Any, Dict, List, Optional

from nav_msgs.msg import OccupancyGrid, Path
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import String
from visualization_msgs.msg import MarkerArray

logger = logging.getLogger(__name__)


class NavigationMixin:
    """High-level Nav2, SLAM, and exploration wrappers.

    Uses send_action_goal / call_service / publish_topic from other mixins.
    """

    # -- SLAM --

    def slam_save_map(self, path: str) -> Dict[str, Any]:
        """Save the current SLAM map (pose graph + pgm/yaml)."""
        return self.call_service(
            '/slam_toolbox/save_map', 'slam_toolbox/srv/SaveMap',
            {'name': {'data': str(path)}}, timeout=10.0)

    def slam_serialize_map(self, path: str) -> Dict[str, Any]:
        """Serialize the SLAM pose graph only (for localization-mode reload)."""
        return self.call_service(
            '/slam_toolbox/serialize_map', 'slam_toolbox/srv/SerializePoseGraph',
            {'filename': {'data': str(path)}}, timeout=10.0)

    def slam_get_map_info(self) -> Optional[Dict[str, Any]]:
        """Get map dimensions, resolution, and exploration coverage."""
        try:
            map_qos = QoSProfile(
                reliability=ReliabilityPolicy.RELIABLE,
                durability=DurabilityPolicy.TRANSIENT_LOCAL,
                depth=1,
            )
            msg = self.wait_for_message(OccupancyGrid, '/map', timeout=5.0, qos=map_qos)
            if msg is None:
                return None

            width = msg.info.width
            height = msg.info.height
            resolution = msg.info.resolution
            data = msg.data

            total = len(data)
            free = sum(1 for v in data if v == 0)
            occupied = sum(1 for v in data if v > 0)
            unknown = sum(1 for v in data if v < 0)
            explored_pct = round((free + occupied) / max(total, 1) * 100, 1)

            return {
                'width_cells': width, 'height_cells': height,
                'width_m': round(width * resolution, 2),
                'height_m': round(height * resolution, 2),
                'resolution_m': round(resolution, 4),
                'origin': {
                    'x': round(msg.info.origin.position.x, 3),
                    'y': round(msg.info.origin.position.y, 3),
                },
                'total_cells': total, 'free_cells': free,
                'occupied_cells': occupied, 'unknown_cells': unknown,
                'explored_pct': explored_pct,
            }
        except Exception as e:
            logger.error(f'slam_get_map_info failed: {e}')
            return None

    # -- AMCL --

    def set_initial_pose(
        self, x: float, y: float, yaw_deg: float = 0.0, frame_id: str = 'map',
    ) -> Dict[str, Any]:
        """Publish initial pose estimate to /initialpose for AMCL."""
        q = self._yaw_to_quaternion(yaw_deg)
        cov = [0.0] * 36
        cov[0] = 0.25    # x variance
        cov[7] = 0.25    # y variance
        cov[35] = 0.069  # yaw variance (~15 deg)
        result = self.publish_topic(
            '/initialpose', 'geometry_msgs/msg/PoseWithCovarianceStamped',
            {
                'header': {'frame_id': frame_id},
                'pose': {
                    'pose': {
                        'position': {'x': float(x), 'y': float(y), 'z': 0.0},
                        'orientation': q,
                    },
                    'covariance': cov,
                },
            })
        if result.get('success'):
            logger.info(f'Published initial pose: x={x}, y={y}, yaw={yaw_deg} deg')
        return result

    def amcl_reinitialize(self) -> Dict[str, Any]:
        """Trigger global AMCL relocalization (scatter particles across map)."""
        return self.call_service(
            '/amcl/reinitialize_global_localization', 'std_srvs/srv/Empty', {}, timeout=5.0)

    # -- Nav2 goals --

    def navigate_to_pose(
        self, x: float, y: float, yaw_deg: float = 0.0,
        frame_id: str = 'map', timeout: float = 120.0,
    ) -> Dict[str, Any]:
        """Send a NavigateToPose goal to Nav2."""
        q = self._yaw_to_quaternion(yaw_deg)
        return self.send_action_goal(
            '/navigate_to_pose', 'nav2_msgs/action/NavigateToPose',
            {'pose': {'header': {'frame_id': frame_id},
                      'pose': {'position': {'x': float(x), 'y': float(y), 'z': 0.0},
                               'orientation': q}}},
            timeout=timeout)

    def navigate_through_poses(
        self, poses: List[Dict[str, float]],
        frame_id: str = 'map', timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """Navigate through an ordered list of poses."""
        pose_list = self._build_pose_list(poses, frame_id)
        return self.send_action_goal(
            '/navigate_through_poses', 'nav2_msgs/action/NavigateThroughPoses',
            {'poses': pose_list}, timeout=timeout)

    def follow_waypoints(
        self, waypoints: List[Dict[str, float]],
        frame_id: str = 'map', timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """Follow an ordered list of waypoints using FollowWaypoints action."""
        pose_list = self._build_pose_list(waypoints, frame_id)
        return self.send_action_goal(
            '/follow_waypoints', 'nav2_msgs/action/FollowWaypoints',
            {'poses': pose_list}, timeout=timeout)

    def _build_pose_list(self, points: List[Dict], frame_id: str) -> List[Dict]:
        """Convert [{x, y, yaw_deg?}] to Nav2 PoseStamped list."""
        result = []
        for p in points:
            q = self._yaw_to_quaternion(float(p.get('yaw_deg', 0.0)))
            result.append({
                'header': {'frame_id': frame_id},
                'pose': {
                    'position': {'x': float(p['x']), 'y': float(p['y']), 'z': 0.0},
                    'orientation': q,
                },
            })
        return result

    # -- Nav2 utilities --

    def nav_cancel(self) -> Dict[str, Any]:
        """Cancel all active Nav2 navigation goals."""
        result = self.call_service(
            '/navigate_to_pose/_action/cancel_all_goals',
            'action_msgs/srv/CancelGoal', {}, timeout=5.0)
        for goal_id, info in list(self._active_goals.items()):
            if info['status'] in ('PENDING', 'ACCEPTED', 'EXECUTING'):
                self.cancel_action_goal(goal_id)
        return result

    def nav_clear_costmaps(self, which: str = 'both') -> Dict[str, Any]:
        """Clear Nav2 local, global, or both costmaps."""
        results = {}
        which = which.lower()
        if which in ('local', 'both'):
            results['local'] = self.call_service(
                '/local_costmap/clear_entirely_local_costmap',
                'nav2_msgs/srv/ClearEntireCostmap', {}, timeout=5.0)
        if which in ('global', 'both'):
            results['global'] = self.call_service(
                '/global_costmap/clear_entirely_global_costmap',
                'nav2_msgs/srv/ClearEntireCostmap', {}, timeout=5.0)
        return {'success': all(r.get('success') for r in results.values()),
                'cleared': which, 'details': results}

    def nav_spin(self, angle_rad: float, time_allowance_sec: float = 10.0) -> Dict[str, Any]:
        """In-place rotation recovery using Nav2 Spin action."""
        return self.send_action_goal(
            '/spin', 'nav2_msgs/action/Spin',
            {'target_yaw': float(angle_rad),
             'time_allowance': {'sec': int(time_allowance_sec), 'nanosec': 0}},
            timeout=time_allowance_sec + 5.0)

    def nav_backup(
        self, distance_m: float = 0.15, speed_mps: float = 0.025,
        time_allowance_sec: float = 10.0,
    ) -> Dict[str, Any]:
        """Drive backward using Nav2 BackUp action."""
        return self.send_action_goal(
            '/backup', 'nav2_msgs/action/BackUp',
            {'target': {'x': float(distance_m), 'y': 0.0, 'z': 0.0},
             'speed': float(speed_mps),
             'time_allowance': {'sec': int(time_allowance_sec), 'nanosec': 0}},
            timeout=time_allowance_sec + 5.0)

    def nav_get_plan(self) -> Optional[Dict[str, Any]]:
        """Get the current Nav2 planned path from /plan topic."""
        try:
            msg = self.wait_for_message(Path, '/plan', timeout=3.0)
            if msg is None or not msg.poses:
                return {'waypoint_count': 0, 'note': 'No active plan'}
            start = msg.poses[0].pose.position
            end = msg.poses[-1].pose.position
            return {
                'waypoint_count': len(msg.poses),
                'frame_id': msg.header.frame_id,
                'start': {'x': round(start.x, 3), 'y': round(start.y, 3)},
                'end': {'x': round(end.x, 3), 'y': round(end.y, 3)},
            }
        except Exception as e:
            logger.error(f'nav_get_plan failed: {e}')
            return None

    # -- Exploration --

    def exploration_command(self, cmd: str) -> Dict[str, Any]:
        """Send a command to the frontier exploration node (start/stop/pause/resume)."""
        valid = {'start', 'stop', 'pause', 'resume'}
        cmd = cmd.strip().lower()
        if cmd not in valid:
            return {'success': False, 'error': f'Invalid command "{cmd}". Valid: {sorted(valid)}'}
        return self.publish_topic('/orbibot/exploration/command', 'std_msgs/msg/String', {'data': cmd})

    def get_exploration_status(self) -> Optional[Dict[str, Any]]:
        """Get the current exploration state."""
        try:
            msg = self.wait_for_message(String, '/orbibot/exploration/status', timeout=3.0)
            return {'status': msg.data} if msg else None
        except Exception as e:
            logger.error(f'get_exploration_status failed: {e}')
            return None

    def get_exploration_frontiers(self) -> Optional[Dict[str, Any]]:
        """Get frontier list from the exploration node."""
        try:
            msg = self.wait_for_message(MarkerArray, '/orbibot/exploration/frontiers', timeout=3.0)
            if msg is None:
                return None
            centroids = []
            for marker in msg.markers:
                if marker.type == 8:  # POINTS marker (frontier cells) — skip
                    continue
                centroids.append({
                    'x': round(marker.pose.position.x, 3),
                    'y': round(marker.pose.position.y, 3),
                })
            return {
                'frontier_count': len(centroids),
                'frontiers': centroids,
                'note': 'Each frontier is an unexplored region centroid in map frame',
            }
        except Exception as e:
            logger.error(f'get_exploration_frontiers failed: {e}')
            return None
