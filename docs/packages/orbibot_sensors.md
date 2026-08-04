---
title: "orbibot_sensors"
type: package
tags:
  - package
  - sensors
---

# orbibot_sensors

RPLidar A1 and the RealSense D435, plus a LiDAR-based obstacle detector.

> **The API reference is `src/orbibot_sensors/README.md`.** This note is orientation:
> what the package owns, where to look first, and what is open.

## Owns

| | |
|---|---|
| RPLidar A1 | `/scan`, 8.0 Hz, 360°, 720 pts/rev, ~8 m, on `/dev/lidar` |
| RealSense D435 | Off by default — too much CPU on the Pi |
| `obstacle_detector.py` | Safety stop from `/scan` |

```bash
ros2 launch orbibot_sensors lidar.launch.py
ros2 launch orbibot_sensors sensors.launch.py   # both
```

## The RealSense decision

It is enumerated at **480 Mbps** while two 5000 Mbps controllers sit idle
([[inventory]]), and full RGB-D on a Pi 5 costs more CPU than the robot has to
spare. Until there is a mini PC, it is a **webcam** — v4l2 straight to WebRTC,
never through ROS. Pushing 640×480 at 15 Hz through DDS is ~14 MB/s of pure
overhead. See [[dashboard-design]].

## Related

[[packages-moc]] · [[orbibot_slam]] · [[dashboard-design]] · [[sensors-moc]]
