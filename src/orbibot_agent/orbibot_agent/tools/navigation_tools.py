"""Navigation, SLAM, and exploration tool definitions."""

from typing import Any, Dict


def register(registry, ros_bridge, safety_manager) -> None:
    """Register SLAM, Nav2, and exploration tools."""

    # -- SLAM --

    registry.register_tool(
        name='slam_save_map',
        description='Save current SLAM map (pose graph + pgm/yaml) to disk.',
        parameters={
            'type': 'object',
            'properties': {
                'path': {'type': 'string', 'description': 'Absolute path without extension'},
            },
            'required': ['path'],
        },
        handler=lambda path: ros_bridge.slam_save_map(path),
    )

    registry.register_tool(
        name='slam_serialize_map',
        description='Serialize SLAM pose graph only (for localization-mode reload).',
        parameters={
            'type': 'object',
            'properties': {'path': {'type': 'string', 'description': 'Absolute path without extension'}},
            'required': ['path'],
        },
        handler=lambda path: ros_bridge.slam_serialize_map(path),
    )

    registry.register_tool(
        name='slam_get_map_info',
        description='Get map dimensions, resolution, origin, and exploration coverage.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.slam_get_map_info(),
    )

    # -- AMCL --

    registry.register_tool(
        name='set_initial_pose',
        description='Set AMCL initial pose estimate on the map.',
        parameters={
            'type': 'object',
            'properties': {
                'x': {'type': 'number', 'description': 'X position in map frame (m)'},
                'y': {'type': 'number', 'description': 'Y position in map frame (m)'},
                'yaw_deg': {'type': 'number', 'description': 'Heading in degrees (default 0)'},
                'frame_id': {'type': 'string', 'description': 'Coordinate frame (default "map")'},
            },
            'required': ['x', 'y'],
        },
        handler=lambda x, y, yaw_deg=0.0, frame_id='map': ros_bridge.set_initial_pose(x, y, yaw_deg, frame_id),
    )

    registry.register_tool(
        name='amcl_reinitialize',
        description='Scatter AMCL particles globally when robot is completely lost.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.amcl_reinitialize(),
    )

    # -- Nav2 goals --

    registry.register_tool(
        name='navigate_to_pose',
        description='Navigate to target x, y, yaw using Nav2 NavigateToPose action.',
        parameters={
            'type': 'object',
            'properties': {
                'x': {'type': 'number', 'description': 'Target X in map frame (m)'},
                'y': {'type': 'number', 'description': 'Target Y in map frame (m)'},
                'yaw_deg': {'type': 'number', 'description': 'Target heading (default 0)'},
                'frame_id': {'type': 'string', 'description': 'Coordinate frame (default "map")'},
                'timeout': {'type': 'number', 'description': 'Goal acceptance timeout (default 120)'},
            },
            'required': ['x', 'y'],
        },
        handler=lambda x, y, yaw_deg=0.0, frame_id='map', timeout=120.0: (
            ros_bridge.navigate_to_pose(x, y, yaw_deg, frame_id, timeout)),
    )

    registry.register_tool(
        name='navigate_through_poses',
        description='Navigate through an ordered list of poses.',
        parameters={
            'type': 'object',
            'properties': {
                'poses': {
                    'type': 'array',
                    'description': 'List of {x, y, yaw_deg?} dicts',
                    'items': {
                        'type': 'object',
                        'properties': {'x': {'type': 'number'}, 'y': {'type': 'number'}, 'yaw_deg': {'type': 'number'}},
                        'required': ['x', 'y'],
                    },
                },
                'frame_id': {'type': 'string', 'description': 'Coordinate frame (default "map")'},
                'timeout': {'type': 'number', 'description': 'Timeout (default 300)'},
            },
            'required': ['poses'],
        },
        handler=lambda poses, frame_id='map', timeout=300.0: (
            ros_bridge.navigate_through_poses(poses, frame_id, timeout)),
    )

    registry.register_tool(
        name='follow_waypoints',
        description='Patrol route through ordered waypoints using FollowWaypoints action.',
        parameters={
            'type': 'object',
            'properties': {
                'waypoints': {
                    'type': 'array',
                    'description': 'List of {x, y, yaw_deg?} dicts',
                    'items': {
                        'type': 'object',
                        'properties': {'x': {'type': 'number'}, 'y': {'type': 'number'}, 'yaw_deg': {'type': 'number'}},
                        'required': ['x', 'y'],
                    },
                },
                'frame_id': {'type': 'string', 'description': 'Coordinate frame (default "map")'},
                'timeout': {'type': 'number', 'description': 'Timeout (default 300)'},
            },
            'required': ['waypoints'],
        },
        handler=lambda waypoints, frame_id='map', timeout=300.0: (
            ros_bridge.follow_waypoints(waypoints, frame_id, timeout)),
    )

    # -- Nav2 utilities --

    registry.register_tool(
        name='nav_cancel',
        description='Cancel all active Nav2 navigation goals.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.nav_cancel(),
    )

    registry.register_tool(
        name='nav_clear_costmaps',
        description='Clear Nav2 local, global, or both costmaps.',
        parameters={
            'type': 'object',
            'properties': {
                'which': {'type': 'string', 'enum': ['local', 'global', 'both'], 'description': 'Which costmap(s) (default "both")'},
            },
        },
        handler=lambda which='both': ros_bridge.nav_clear_costmaps(which),
    )

    registry.register_tool(
        name='nav_spin',
        description='In-place rotation recovery using Nav2 Spin action.',
        parameters={
            'type': 'object',
            'properties': {
                'angle_rad': {'type': 'number', 'description': 'Rotation in radians (positive = CCW)'},
                'time_allowance_sec': {'type': 'number', 'description': 'Time budget (default 10)'},
            },
            'required': ['angle_rad'],
        },
        handler=lambda angle_rad, time_allowance_sec=10.0: ros_bridge.nav_spin(angle_rad, time_allowance_sec),
    )

    registry.register_tool(
        name='nav_backup',
        description='Short reverse recovery using Nav2 BackUp action.',
        parameters={
            'type': 'object',
            'properties': {
                'distance_m': {'type': 'number', 'description': 'Reverse distance (default 0.15)'},
                'speed_mps': {'type': 'number', 'description': 'Backup speed (default 0.025)'},
                'time_allowance_sec': {'type': 'number', 'description': 'Time budget (default 10)'},
            },
        },
        handler=lambda distance_m=0.15, speed_mps=0.025, time_allowance_sec=10.0: (
            ros_bridge.nav_backup(distance_m, speed_mps, time_allowance_sec)),
    )

    registry.register_tool(
        name='nav_get_plan',
        description='Get current Nav2 planned path from /plan topic.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.nav_get_plan(),
    )

    # -- Exploration --

    registry.register_tool(
        name='exploration_start',
        description='Start autonomous frontier exploration.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.exploration_command('start'),
    )

    registry.register_tool(
        name='exploration_stop',
        description='Stop autonomous exploration.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.exploration_command('stop'),
    )

    registry.register_tool(
        name='exploration_pause',
        description='Pause exploration (robot stays in place). Resume with exploration_resume.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.exploration_command('pause'),
    )

    registry.register_tool(
        name='exploration_resume',
        description='Resume exploration after a pause.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.exploration_command('resume'),
    )

    registry.register_tool(
        name='get_exploration_status',
        description='Get current exploration state (idle/exploring/navigating/complete/stopped).',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.get_exploration_status(),
    )

    registry.register_tool(
        name='get_exploration_frontiers',
        description='Get unexplored frontier regions and their positions in map frame.',
        parameters={'type': 'object', 'properties': {}},
        handler=lambda: ros_bridge.get_exploration_frontiers(),
    )
