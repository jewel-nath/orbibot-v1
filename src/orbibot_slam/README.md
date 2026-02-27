# orbibot_slam

SLAM (Simultaneous Localization and Mapping) for OrbiBot using `slam_toolbox`. Supports both mapping (building new maps) and localization (navigating with saved maps).

## Overview

This package wraps `slam_toolbox` with OrbiBot-specific configurations optimized for:
- **RPLidar A1** (360°, 8m range, 10Hz)
- **Raspberry Pi 5** (CPU-efficient parameters)
- **Mecanum wheel odometry** (velocity-only fusion via EKF)

Two modes are supported:
1. **Mapping Mode**: Build a new map while driving the robot
2. **Localization Mode**: Navigate using a previously saved map

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SLAM PIPELINE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌─────────────┐                                                │
│   │   /scan     │  10 Hz                                         │
│   │ (RPLidar A1)│                                                │
│   └──────┬──────┘                                                │
│          │                                                        │
│          ▼                                                        │
│   ┌─────────────────────┐                                        │
│   │  slam_toolbox       │                                        │
│   │  (async or          │                                        │
│   │   localization)     │                                        │
│   │                     │                                        │
│   │  • Scan matching    │                                        │
│   │  • Pose graph       │                                        │
│   │  • Loop closure     │                                        │
│   │  • Map optimization │                                        │
│   └──────────┬──────────┘                                        │
│              │                                                    │
│              ├──► /map (OccupancyGrid)                           │
│              │                                                    │
│              ├──► /slam_pose (PoseWithCovariance)                │
│              │                                                    │
│              └──► TF: map → odom (drift correction)              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### How It Works

1. **Scan Matching**: Each LiDAR scan is matched against the existing map to estimate robot pose
2. **Pose Graph**: Robot poses are stored as nodes in a graph with constraints from odometry and scan matching
3. **Loop Closure**: When the robot revisits a location, the graph is optimized to correct accumulated drift
4. **Map Update**: Occupancy grid is updated with new scan data

---

## Quick Start

### Mapping Mode (Build New Map)

```bash
# Terminal 1: Robot base + localization
ros2 launch orbibot_bringup robot.launch.py
ros2 launch orbibot_localization localization.launch.py

# Terminal 2: SLAM
ros2 launch orbibot_slam slam.launch.py

# Terminal 3: Teleoperation
ros2 launch orbibot_teleop controller.launch.py

# Drive around to build map, then save:
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
  "{name: {data: '/home/orbibot/maps/my_map'}}"
ros2 run nav2_map_server map_saver_cli -f /home/orbibot/maps/my_map
```

### Localization Mode (Use Saved Map)

```bash
# Terminal 1: Robot base + localization
ros2 launch orbibot_bringup robot.launch.py
ros2 launch orbibot_localization localization.launch.py

# Terminal 2: SLAM localization
ros2 launch orbibot_slam slam_localization.launch.py \
  map_file_name:=/home/orbibot/maps/my_map

# Terminal 3: Navigation
ros2 launch orbibot_navigation navigation.launch.py \
  map:=/home/orbibot/maps/my_map.yaml
```

---

## Launch Files

### `slam.launch.py` — Mapping Mode

| Argument | Default | Description |
|----------|---------|-------------|
| `autostart` | `true` | Auto-configure and activate SLAM node |
| `use_lifecycle_manager` | `false` | Use external Nav2 lifecycle manager |
| `slam_params_file` | `config/slam_params.yaml` | Mapping parameters |
| `log_level` | `info` | Log verbosity |

**Node**: `async_slam_toolbox_node` (non-blocking, better for RPi)

### `slam_localization.launch.py` — Localization Mode

| Argument | Default | Description |
|----------|---------|-------------|
| `map_file_name` | **(required)** | Path to saved map (no extension) |
| `autostart` | `true` | Auto-configure and activate SLAM node |
| `use_lifecycle_manager` | `false` | Use external Nav2 lifecycle manager |
| `slam_params_file` | `config/slam_localization_params.yaml` | Localization parameters |
| `log_level` | `info` | Log verbosity |

**Node**: `localization_slam_toolbox_node`

---

## Topics & TF

### Subscribed

| Topic | Type | Source | Description |
|-------|------|--------|-------------|
| `/scan` | `sensor_msgs/LaserScan` | RPLidar A1 | 360° laser scans |
| `/tf` | `tf2_msgs/TFMessage` | EKF | `odom → base_footprint` transform |

### Published

| Topic | Type | Rate | Description |
|-------|------|------|-------------|
| `/map` | `nav_msgs/OccupancyGrid` | 0.5 Hz (localization: 2s) | Occupancy map |
| `/slam_pose` | `geometry_msgs/PoseWithCovarianceStamped` | 50 Hz | Estimated robot pose |
| `/map_metadata` | `nav_msgs/MapMetaData` | Static | Map resolution, origin |

### TF Published

| Transform | Description |
|-----------|-------------|
| `map → odom` | SLAM correction (drift compensation) |

**TF Tree**:
```
map (world frame, fixed)
└── odom (drifts, corrected by SLAM)
    └── base_footprint (robot pose)
        └── base_link → sensors
```

---

## Configuration

### Mapping Parameters (`config/slam_params.yaml`)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `mode` | `mapping` | Build new map |
| `resolution` | 0.05 m | 5cm per grid cell |
| `min_laser_range` | 0.15 m | Ignore readings closer than this |
| `max_laser_range` | 8.0 m | Ignore readings beyond this |
| `minimum_travel_distance` | 0.35 m | Minimum movement for new scan |
| `minimum_travel_heading` | 0.35 rad | ~20° rotation for new scan |
| `map_update_interval` | 2.0 s | Seconds between map updates |
| `do_loop_closing` | `true` | Enable loop closure |
| `loop_search_maximum_distance` | 3.0 m | Search radius for loop closure |
| `width / height` | 20 / 20 m | Initial map size (auto-expands) |

### Localization Parameters (`config/slam_localization_params.yaml`)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `mode` | `localization` | Use saved map |
| `minimum_travel_distance` | 0.30 m | Tighter than mapping |
| `minimum_travel_heading` | 0.30 rad | Tighter than mapping |
| `publish_period_sec` | 2.0 s | Map publish rate (static map) |

---

## Map Files

### File Formats

When you save a map, two formats are created:

| Format | Files | Purpose |
|--------|-------|---------|
| **slam_toolbox** | `my_map.posegraph`, `my_map.data` | Reload for localization mode |
| **Nav2 standard** | `my_map.pgm`, `my_map.yaml` | Load into Nav2 map server |

### Save Map

```bash
# Method 1: slam_toolbox service (preserves pose graph)
ros2 service call /slam_toolbox/save_map slam_toolbox/srv/SaveMap \
  "{name: {data: '/home/orbibot/maps/my_map'}}"

# Method 2: Nav2 map saver (standard format only)
ros2 run nav2_map_server map_saver_cli -f /home/orbibot/maps/my_map
```

### Load Map for Localization

```bash
ros2 launch orbibot_slam slam_localization.launch.py \
  map_file_name:=/home/orbibot/maps/my_map
```

**Note**: Use the path **without extension**. The node loads both `.posegraph` and `.data` files.

---

## Mapping Best Practices

### For Good Map Quality

1. **Drive slowly** (< 0.5 m/s)
   - Gives SLAM time to process scans
   - Reduces motion blur

2. **Close loops intentionally**
   - Return to starting point before saving
   - Triggers loop closure, corrects drift

3. **Avoid long featureless corridors**
   - SLAM needs features to match scans
   - Add artificial features (boxes, walls) if needed

4. **Map in sections for large spaces**
   - Save partial maps at waypoints
   - Merge using slam_toolbox multi-session

5. **Monitor for loop closure**
   ```bash
   ros2 topic echo /slam_toolbox/loop_closure  # If available
   # Watch console for "Loop closure detected" messages
   ```

### Common Map Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Map "smears" or duplicates walls | Odometry drift, no loop closure | Return to start, drive slower |
| Map doesn't update | No `/scan` or wrong TF | Check LiDAR, verify `odom → base_footprint` |
| Map drifts over time | No loop closure detected | Ensure `do_loop_closing: true`, increase search radius |
| Map too noisy | High `minimum_travel_distance` | Lower to 0.3m for more scans |
| CPU overload (RPi) | Too frequent updates | Increase `map_update_interval` to 5.0s |

---

## Debugging

### Verify Data Flow
```bash
# Check scan is arriving
ros2 topic hz /scan  # Should be ~10Hz

# Check TF is present
ros2 run tf2_tools view_frames  # Verify odom → base_footprint

# Check map is publishing
ros2 topic hz /map  # ~0.5Hz mapping, ~0.5Hz localization

# Inspect map
ros2 topic echo /map --no-arr  # Check width, height, resolution
```

### SLAM Diagnostics
```bash
# Monitor console output
ros2 launch orbibot_slam slam.launch.py log_level:=debug

# Look for:
# - "Registered new scan" → Scans being added
# - "Loop closure detected" → Drift correction triggered
# - "Scan matcher failed" → Poor scan match, possible issue
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Failed to compute odom pose" | Missing TF | Start EKF localization first |
| "No scans to process" | No /scan topic | Check LiDAR is publishing |
| "Map is empty" | No scans added yet | Drive around, check thresholds |
| "Deserialize: file not found" | Wrong map path | Verify `.posegraph` and `.data` files exist |
| High CPU usage | RPi overloaded | Increase `map_update_interval`, reduce `resolution` |

---

## Services

| Service | Type | Description |
|---------|------|-------------|
| `/slam_toolbox/save_map` | `slam_toolbox/SaveMap` | Save serialized map |
| `/slam_toolbox/serialize_map` | `slam_toolbox/SerializePoseGraph` | Save pose graph only |
| `/slam_toolbox/deserialize_map` | `slam_toolbox/DeserializePoseGraph` | Load saved map |

---

## Dependencies

```bash
sudo apt install ros-jazzy-slam-toolbox
sudo apt install ros-jazzy-nav2-map-server
```

---

## References

- **slam_toolbox**: https://github.com/SteveMacenski/slam_toolbox
- **SLAM Tutorial**: https://navigation.ros.org/setup_guides/slam/setup_slam.html
- **Ceres Solver**: http://ceres-solver.org/ (optimization backend)

---

**Last Updated**: 2026-02-24  
**Maintainer**: Jewel Nath