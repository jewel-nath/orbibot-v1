---
title: "05 - Visualization"
type: learn
area: description
package: orbibot_description
tags:
  - learn
  - description
---

# 05 - Visualization

**Seeing your robot in RViz**

---

## 🎯 Learning Objectives

- Launch RViz with OrbiBot model
- Add and configure displays
- Debug common visualization issues

---

## 🚀 Launch Commands

```bash
# Publish robot description
ros2 launch orbibot_description description.launch.py

# Launch RViz
ros2 launch orbibot_description rviz.launch.py

# Fixed frame (no hardware needed)
ros2 launch orbibot_description rviz.launch.py fixed_frame:=true
```

---

## 📊 Essential Displays

| Display | Topic/Frame | Shows |
|---------|-------------|-------|
| RobotModel | /robot_description | URDF model |
| TF | /tf | Coordinate frames |
| LaserScan | /scan | LiDAR data |
| Image | /camera/color/image_raw | Camera feed |

---

## 🔍 Debugging

### Robot not visible?
- Check fixed frame is set to `odom` or `base_link`
- Ensure `description.launch.py` is running

### Wheels not moving?
- Hardware must be running for joint states
- Or use `fixed_frame:=true`

### TF errors?
```bash
ros2 run tf2_tools view_frames
```

---

## 🎯 Key Takeaways

1. **RViz** = Robot visualization
2. **RobotModel** shows URDF
3. **TF** shows coordinate frames
4. **Fixed frame** determines viewpoint

---

**OrbiBot Description Guide Complete!**

---

*Last Updated: March 2026*