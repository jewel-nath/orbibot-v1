# 07 - Localization Launch

**Running the sensor fusion stack**

---

## 🎯 Learning Objectives

- Launch localization stack
- Verify data flow
- Debug common issues

---

## 🚀 Launching

```bash
# Launch localization
ros2 launch orbibot_localization localization.launch.py

# With debug logging
ros2 launch orbibot_localization localization.launch.py log_level:=debug
```

---

## ✅ Verification

```bash
# Check topics
ros2 topic hz /imu/data_filtered      # ~50Hz
ros2 topic hz /odometry/filtered      # ~25Hz

# Check TF
ros2 run tf2_tools view_frames
# Should show: odom → base_footprint

# Monitor output
ros2 topic echo /odometry/filtered --once
```

---

## 🔍 Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No output | Missing inputs | Check /odom and /imu/* |
| Yaw drifts slowly | No absolute heading (no magnetometer) | Expected; SLAM or AMCL correct it through map → odom |
| Jumpy position | Wheel slip | Increase rejection threshold |

---

## 🎯 Key Takeaways

1. **Launch** = localization.launch.py
2. **Inputs** = /odom + /imu/data_filtered
3. **Output** = /odometry/filtered + TF
4. **Rate** = 25Hz

---

**OrbiBot Localization Guide Complete!**

---

*Last Updated: March 2026*