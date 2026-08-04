---
title: "orbibot_slam"
type: package
tags:
  - package
  - slam
---

# orbibot_slam

slam_toolbox, wrapped for an 8 Hz 8 m RPLidar A1. Mapping and localization.

> **The API reference is `src/orbibot_slam/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

```bash
ros2 launch orbibot_slam slam.launch.py              # build a map
ros2 launch orbibot_slam slam_localization.launch.py # use a saved one
```

Publishes `/map` and the `map → odom` transform.

## The rule that matters

**Exactly one node may publish `map → odom`** — slam_toolbox *or* AMCL, never
both. Two publishers on that edge is the classic way to make a robot appear to
teleport.

Since the magnetometer went, this package also carries the burden of absolute
heading: gyro yaw drifts without bound, and scan matching is what pulls it
back.

## Related

[[packages-moc]] · [[orbibot_localization]] · [[orbibot_navigation]] ·
[[system-overview]]
