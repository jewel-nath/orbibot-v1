---
title: "05 - Obstacle Detection"
type: learn
area: sensors
package: orbibot_sensors
tags:
  - learn
  - sensors
---

# 05 - Obstacle Detection

**LiDAR-based safety system**

---

## 🎯 Learning Objectives

- Understand 8-sector obstacle detection
- Know warning vs emergency distances
- Configure thresholds

---

## 🛡️ Safety System Overview

```
LiDAR Scan → obstacle_detector → Safety Topics
                 ↓
    ┌────────────┼────────────┐
    ↓            ↓            ↓
obstacle_  emergency_    min_obstacle
detected    stop          _distance
```

---

## 🎱 8-Sector Layout

```
              Front (0)
                ↑
    FL (1) ↖       ↗ FR (7)
             ╲     ╱
    Left (2)  ╲   ╱  Right (6)
               ╲ ╱
    BL (3) ↙       ↘ BR (5)
                ↓
              Back (4)
```

---

## ⚠️ Thresholds

| Parameter | Default | Trigger |
|-----------|---------|---------|
| warning_distance | 0.50m | obstacle_detected = true |
| emergency_distance | 0.25m | emergency_stop = true |
| hysteresis | 0.05m | Prevents rapid toggling |

---

## 🚀 Launching

```bash
# With default thresholds
ros2 run orbibot_sensors obstacle_detector

# Custom thresholds
ros2 run orbibot_sensors obstacle_detector \
  --ros-args \
  -p warning_distance:=0.6 \
  -p emergency_distance:=0.3
```

---

## 🎯 Key Takeaways

1. **8 sectors** = Full 360° coverage
2. **Warning** = Slow down (0.5m)
3. **Emergency** = Stop immediately (0.25m)
4. **Hysteresis** = Prevent oscillation

---

## 📖 Next Steps

Learn device setup:

**→ Continue to:** [[06-device-setup]]

---

*Last Updated: March 2026*