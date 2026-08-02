---
title: "01 - LiDAR Basics"
type: learn
area: sensors
package: orbibot_sensors
tags:
  - learn
  - sensors
---

# 01 - LiDAR Basics

**How 2D laser scanners work**

---

## 🎯 Learning Objectives

- Understand LiDAR operating principle
- Know RPLidar A1 specifications
- Launch and verify LiDAR operation

---

## 🔦 How LiDAR Works

```
1. Laser emits light pulse
2. Pulse hits object
3. Light reflects back
4. Sensor measures time-of-flight
5. Calculate distance: d = (speed × time) / 2

Repeat 360° for full scan!
```

---

## 📊 RPLidar A1 Specifications

| Parameter | Value |
|-----------|-------|
| Range | 0.15 - 8.0 meters |
| Update rate | 10 Hz |
| Angular resolution | 0.5° (Express) / 1° (Standard) |
| Interface | USB Serial |
| Power | 5V, ~400mA |

---

## 🚀 Launching the LiDAR

```bash
# Basic launch
ros2 launch orbibot_sensors lidar.launch.py

# With options
ros2 launch orbibot_sensors lidar.launch.py \
  serial_port:=/dev/lidar \
  scan_mode:=Standard
```

### Verify Operation

```bash
# Check topic
ros2 topic list | grep scan

# Check rate
ros2 topic hz /scan
# Should be ~10Hz

# View data
ros2 topic echo /scan --once
```

---

## 🎯 Key Takeaways

1. **LiDAR** = Time-of-flight distance measurement
2. **RPLidar A1** = 360° scanning, 10Hz, 8m range
3. **Topic** = `/scan` with LaserScan message
4. **Launch** = `lidar.launch.py`

---

## 📖 Next Steps

Learn LaserScan message format:

**→ Continue to:** [[02-laserscan-message]]

---

*Last Updated: March 2026*