---
title: "04 - TF Tree"
type: learn
area: description
package: orbibot_description
tags:
  - learn
  - description
---

# 04 - TF Tree

**Coordinate frames and transforms**

---

## 🎯 Learning Objectives

- Understand the TF tree
- Know OrbiBot's frame hierarchy
- Use TF2 tools

---

## 🌳 OrbiBot TF Tree

```
map (world)
└── odom (odometry origin)
    └── base_footprint (ground level)
        └── base_link (robot center, 100mm up)
            ├── wheel_front_left_link
            ├── wheel_back_left_link
            ├── wheel_front_right_link
            ├── wheel_back_right_link
            ├── lidar_link (200mm up)
            ├── imu_link (100mm up)
            └── camera_link (150mm up)
```

---

## 📍 Key Frames

| Frame | Purpose |
|-------|---------|
| `base_link` | Robot center, main reference |
| `lidar_link` | LiDAR data frame_id |
| `imu_link` | IMU data frame_id |
| `camera_link` | Camera data frame_id |

---

## 🖥️ TF2 Tools

```bash
# View all frames
ros2 run tf2_tools view_frames

# Echo a transform
ros2 run tf2_ros tf2_echo odom base_link

# Check TF rate
ros2 topic hz /tf
```

---

## 🎯 Key Takeaways

1. **TF tree** = Spatial relationships
2. **base_link** = Main robot frame
3. **Sensor frames** = Where sensors are mounted
4. **TF2** = Tracks dynamic relationships

---

## 📖 Next Steps

Learn visualization:

**→ Continue to:** [[05-visualization]]

---

*Last Updated: March 2026*