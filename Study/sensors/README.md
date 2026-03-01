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
| [00-sensor-overview.md](00-sensor-overview.md) | Types of robot sensors | 10 min |
| [01-lidar-basics.md](01-lidar-basics.md) | RPLidar A1 operation | 25 min |
| [02-laserscan-message.md](02-laserscan-message.md) | LaserScan data structure | 20 min |
| [03-camera-basics.md](03-camera-basics.md) | RealSense D435 | 25 min |
| [04-image-transport.md](04-image-transport.md) | Camera data in ROS2 | 20 min |
| [05-obstacle-detection.md](05-obstacle-detection.md) | Safety system | 25 min |
| [06-device-setup.md](06-device-setup.md) | udev and permissions | 20 min |

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

**Begin with:** [00-sensor-overview.md](00-sensor-overview.md)

---

**Happy Learning!**