---
title: "OrbiBot Sensors Study Guide"
type: learn
area: sensors
package: orbibot_sensors
tags:
  - learn
  - sensors
---

# OrbiBot Sensors Study Guide

**LiDAR, camera, and obstacle detection**

---

## Prerequisites

**REQUIRED:**
1. **[ROS2 Study Guide](../ros2/)** - Common ROS2 fundamentals
   - Minimum: 00-ros2-overview, 03-topics-pub-sub, 04-messages-interfaces
   - Essential: Topics, message types

2. **[Description Study Guide](../description/)** - Robot modeling
   - Understand TF frames and coordinate systems

3. **Basic Linux** - Device permissions, udev rules

---

## What You'll Learn

By completing this guide, you will understand:

- **LiDAR** - How 2D laser scanners work
- **Camera** - RGB-D sensors and depth data
- **Message types** - LaserScan, Image, PointCloud2
- **Obstacle detection** - Safety systems using sensor data
- **Device configuration** - udev rules and permissions

---

## Study Files

| File | Topic | Time |
|------|-------|------|
| [[00-sensor-overview]] | Types of robot sensors | 10 min |
| [[01-lidar-basics]] | RPLidar A1 operation | 25 min |
| [[02-laserscan-message]] | LaserScan data structure | 20 min |
| [[03-camera-basics]] | RealSense D435 | 25 min |
| [[04-image-transport]] | Camera data in ROS2 | 20 min |
| [[05-obstacle-detection]] | Safety system | 25 min |
| [[06-device-setup]] | udev and permissions | 20 min |

---

## Learning Path

### Week 1: LiDAR
- 00-sensor-overview.md
- 01-lidar-basics.md
- 02-laserscan-message.md

### Week 2: Camera and Integration
- 03-camera-basics.md
- 04-image-transport.md
- 05-obstacle-detection.md
- 06-device-setup.md

---

## Related Files

```
src/orbibot_sensors/
├── orbibot_sensors/
│   └── obstacle_detector.py    ← Obstacle detection node
├── launch/
│   ├── lidar.launch.py         ← LiDAR launch
│   ├── camera.launch.py        ← Camera launch
│   └── sensors.launch.py       ← Combined launch
└── config/
    ├── rplidar_params.yaml     ← LiDAR configuration
    └── realsense_camera_params.yaml  ← Camera configuration
```

---

## Start Here

**Begin with:** [[00-sensor-overview]]

---

**Happy Learning!**