# 11 - RViz Basics

**Visualizing robot data**

---

## 🎯 Learning Objectives

- Launch RViz2
- Add displays
- Visualize robot state

---

## 🚀 Launching RViz

```bash
# Basic launch
ros2 run rviz2 rviz2

# With config file
ros2 run rviz2 rviz2 -d config.rviz
```

---

## 📊 Common Displays

| Display | Shows |
|---------|-------|
| RobotModel | URDF robot |
| LaserScan | LIDAR data |
| Image | Camera feed |
| PointCloud2 | 3D point cloud |
| Odometry | Position trail |
| TF | Coordinate frames |

---

## 🎯 OrbiBot Config

```bash
# Launch with OrbiBot config
ros2 launch orbibot_description rviz.launch.py
```

---

## 🎯 Key Takeaways

1. **RViz** = Robot visualization
2. **Displays** show different data types
3. **Config files** save your setup

---

## 📖 Next Steps

**→ Continue to:** [12 - CLI Tools](12-cli-tools.md)

---

*Last Updated: March 2026*