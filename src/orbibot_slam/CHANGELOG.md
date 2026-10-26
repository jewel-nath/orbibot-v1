# orbibot_slam — Audit Findings

**Date:** 2026-02-23
**Audited:** `config/slam_params.yaml`, `config/slam_localization_params.yaml`, `launch/slam.launch.py`, `launch/slam_localization.launch.py`, `README.md`
**References compared:** `References/Autonomous-Mobile-Robot/ros2_ws/src/my_robot_description/config/my_slam_config.yaml`, `References/LGDXRobot2/lgdxrobot2-ros2/lgdxrobot2_navigation/launch/slam_launch.py`

---

## Progress Legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Done

---

## Architecture Assessment

**Verdict: Architecture is sound. No structural changes required.**

The SLAM stack is well-structured:

- **Correct executable**: `async_slam_toolbox_node` for mapping (non-blocking, better for RPi), `localization_slam_toolbox_node` for localization-only mode
- **Correct frames**: `base_frame: base_footprint` (project convention), `odom_frame: odom`, `map_frame: map`
- **Correct topic**: `scan_topic: /scan`
- **LifecycleNode autostart**: configure → activate chain is correct and avoids Nav2 dependency for standalone launch
- **Two separate configs**: mapping and localization have correctly different parameters (relaxed matching for mapping, tighter for localization)
- **`do_loop_closing: true`**: correct — loop closure is needed for long mapping sessions

---

## Issues Found

### Bugs

| ID | Severity | File | Description |
|----|----------|------|-------------|
| BUG-1 | Medium | `slam_params.yaml`, `slam_localization_params.yaml` | `min_laser_range` missing — without it, near-robot scan readings (below LiDAR minimum usable range) can create erroneous free-space cells in the occupancy grid; RPLidar A1 minimum usable range is 0.15m |
| BUG-2 | Low | `slam_params.yaml` | `width: 10, height: 10` — initial map is only 10×10m; typical room is 3–6m wide but a house can exceed 10m, causing immediate map reallocation; raise to `20, 20` |

### Improvements

| ID | File | Description |
|----|------|-------------|
| Q1 | `slam_localization_params.yaml` | `publish_period_sec` absent — defaults to 10.0s in slam_toolbox; while the map is static in localization mode, Nav2 costmaps may not receive the map if they subscribe after the first publish; add explicit `2.0` |

### Documentation

| ID | Description |
|----|-------------|
| C1 | README missing: dependency install, full topic/TF table, complete mapping→save→localization workflow, debug commands |

---

## Reference Comparison Notes

| Parameter | OrbiBot | AMR Reference | Assessment |
|-----------|---------|--------------|------------|
| `min_laser_range` | missing | 0.1 | **Fix** — add 0.15 (RPLidar A1 min) |
| `max_laser_range` | 8.0 | 12.0 | OK — RPLidar A1 is 8m max |
| `transform_publish_period` | 0.02 | 0.1 | OK — 50Hz TF is fine, avoids Nav2 extrapolation warnings |
| `map_update_interval` | 2.0 | 5.0 | OK — more frequent updates are better for live mapping |
| `minimum_time_interval` | 0.3 | 0.2 | OK — slightly conservative for RPi CPU |
| `minimum_travel_distance` | 0.35 (mapping) | 0.5 | OK — more responsive mapping |
| `width / height` | 10 | (not set) | **Fix** — too small, raise to 20 |
| `correlation_search_space_smear_deviation` | 0.06 (mapping) | 0.1 | OK — tighter than reference but appropriate |
| `loop_search_space_dimension` | 6.0 (mapping) | 8.0 | OK — conservative but saves CPU |
| `publish_period_sec` | 0.05 (mapping), absent (localization) | — | **Fix** — add explicit 2.0 to localization |

---

## Fix Status

- [x] BUG-1 — Add `min_laser_range: 0.15` to both configs
- [x] BUG-2 — Raise initial map `width` and `height` from 10 to 20
- [x] Q1 — Add `publish_period_sec: 2.0` to localization config
- [x] C1 — Rewrite README
