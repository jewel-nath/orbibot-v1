# orbibot_sensors — Audit & Changelog

**Date:** 2026-02-23
**Scope:** RPLidar A1 config, RealSense config, launch files, obstacle_detector node

---

## Architecture Assessment

Sound. No structural changes needed.

- `rplidar_ros` / `realsense2_camera` are correct external drivers
- `obstacle_detector` pattern (subscribe /scan, publish safety signals) is correct
- `lidar_link` frame matches URDF — no TF mismatch
- `scan_topic: /scan` in slam_params.yaml matches what rplidar_ros publishes
- `flip_x_axis: true` + URDF `rpy="0 0 0"` is consistent (driver handles mounting correction)

---

## Issues Found

| ID | Severity | File | Issue |
|----|----------|------|-------|
| BUG-1 | High | `config/rplidar_params.yaml` | Contains 9 non-existent rplidar_ros parameters — silently ignored but create false impression of active features (filtering, auto-reconnect, frequency control) |
| BUG-2 | Medium | `launch/sensors.launch.py` | Camera launch overrides RPi-optimized config with heavy settings: 640×480@30fps + pointcloud enabled — contradicts the config defaults (424×240@15fps, pointcloud=false) |
| Q1 | Low | `orbibot_sensors/obstacle_detector.py` | Scan subscriber uses `depth=10` — for safety-critical latest-scan processing should be `depth=1` |
| C1 | Low | `README.md` | Minimal — no launch argument table, QoS table, or topic list |

---

## Reference Comparison

| Feature | Yahboom X3 | OrbiBot (before) | OrbiBot (after) |
|---------|-----------|-----------------|-----------------|
| LiDAR driver | `sllidar_ros2` (sllidar_launch.py) | `rplidar_ros` (rplidar_composition) | unchanged |
| LiDAR frame | `laser` (via static TF, rpy=π,0,0) | `lidar_link` (flip_x_axis in driver) | unchanged |
| Scan topic | `/scan` | `/scan` | unchanged |
| Obstacle avoidance | Simple front/left/right zones | 8-sector 360° with hysteresis | unchanged (better) |

---

## BUG-1: Invalid rplidar_ros parameters (HIGH)

**File:** `config/rplidar_params.yaml`

The following parameters do **not exist** in the `rplidar_ros` `rplidar_composition` node:

| Invalid param | Was | Effect |
|--------------|-----|--------|
| `scan_filter_enabled` | true | Silently ignored — no filtering active |
| `scan_filter_min_distance` | 0.15 | Silently ignored — range not filtered by driver |
| `scan_filter_max_distance` | 8.0 | Silently ignored — range not filtered by driver |
| `auto_reconnect` | true | Silently ignored — reconnect handled by `respawn: true` in launch |
| `reconnect_timeout` | 2.0 | Silently ignored |
| `publish_scan` | true | Silently ignored — scan always published |
| `publish_intensity` | false | Silently ignored |
| `scan_frequency` | 10.0 | Silently ignored — frequency set by scan_mode hardware |
| `range_min` | 0.15 | Silently ignored — range filtering done by slam_toolbox |
| `range_max` | 8.0 | Silently ignored — range filtering done by slam_toolbox |

**Note:** Range filtering (min 0.15m, max 8.0m) is already correctly configured in
`slam_params.yaml` (`min_laser_range`, `max_laser_range`) — the driver does not need it.

**Fix:** Remove all invalid parameters. Keep only the 9 valid rplidar_ros params.

**Commit:** `fix(sensors): remove invalid rplidar_params — driver ignores them silently`

---

## BUG-2: sensors.launch.py overrides RPi-optimized camera defaults (MEDIUM)

**File:** `launch/sensors.launch.py`

When `sensors:=both` or `sensors:=camera`, the meta-launcher overrides the
camera.launch.py defaults with resource-heavy settings:

| Setting | config default | sensors.launch.py override |
|---------|---------------|---------------------------|
| `color_width` | 424 | **640** |
| `color_height` | 240 | **480** |
| `color_fps` | 15 | **30** |
| `enable_pointcloud` | false | **true** |

640×480@30fps + pointcloud generation will saturate the RPi 5 CPU on top of
slam_toolbox + Nav2. The config was clearly tuned for RPi.

**Fix:** Change sensors.launch.py camera overrides to match the RPi-friendly config defaults.

**Commit:** `fix(sensors): restore RPi-friendly camera settings in sensors.launch.py`

---

## Q1: obstacle_detector scan subscriber depth too large (LOW)

**File:** `orbibot_sensors/obstacle_detector.py`

```python
# Current
sensor_qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    depth=10  # ← stale scans can build up
)
```

`depth=10` allows 10 scan messages to queue. At 10Hz scan rate that's 1 second of
backlogged data. If the obstacle_detector callback takes longer than one scan cycle,
it will process stale data instead of the latest scan — dangerous for safety.

**Fix:** `depth=1` — always process only the freshest scan.

**Commit:** `fix(sensors): set obstacle_detector scan QoS depth to 1 for latest-only safety`

---

## C1: README minimal (LOW)

**Fix:** Rewrite README with:
- All three launch files with argument tables
- Topic/QoS table (published + subscribed)
- obstacle_detector thresholds
- depthimage_to_laserscan explanation

**Commit:** `docs(sensors): rewrite README with topics, launch args, obstacle thresholds`
