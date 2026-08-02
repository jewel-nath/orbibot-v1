---
title: "00 - Sensor Overview"
type: learn
area: sensors
package: orbibot_sensors
tags:
  - learn
  - sensors
---

# 00 - Sensor Overview

**Types of robot sensors**

---

## 🎯 Learning Objectives

- Know common robot sensor types
- Understand sensor characteristics
- Choose right sensor for task

---

## 📡 Common Robot Sensors

### Distance Sensors

| Sensor | Range | Use Case |
|--------|-------|----------|
| **LiDAR** | 0.15-8m | Navigation, mapping |
| **Ultrasonic** | 0.02-4m | Obstacle avoidance |
| **IR** | 0.1-1m | Cliff detection |
| **Depth Camera** | 0.4-4m | 3D perception |

### Vision Sensors

| Sensor | Output | Use Case |
|--------|--------|----------|
| **RGB Camera** | 2D image | Object detection |
| **Depth Camera** | RGB + depth | 3D reconstruction |
| **Stereo Camera** | Depth | Visual SLAM |

### Proprioceptive Sensors

| Sensor | Measures | Use Case |
|--------|----------|----------|
| **IMU** | Orientation, acceleration | Localization |
| **Encoders** | Wheel rotation | Odometry |
| **GPS** | Global position | Outdoor navigation |

---

## 🎯 OrbiBot Sensors

```
┌─────────────────────────────────────────┐
│           OrbiBot Sensors               │
├─────────────────────────────────────────┤
│                                         │
│  RPLidar A1 (Primary)                   │
│  ├── 360° 2D scanning                   │
│  ├── 10 Hz update rate                  │
│  └── Topic: /scan                       │
│                                         │
│  RealSense D435 (Optional)              │
│  ├── RGB image                          │
│  ├── Depth image                        │
│  └── Topics: /camera/...                │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🎯 Key Takeaways

1. **LiDAR** = Primary navigation sensor
2. **Camera** = Visual data for advanced apps
3. **IMU/Encoders** = Internal state (in hardware package)
4. Each sensor has specific strengths

---

## 📖 Next Steps

Learn about LiDAR:

**→ Continue to:** [[01-lidar-basics]]

---

*Last Updated: March 2026*