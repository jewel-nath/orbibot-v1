# 06 - EKF Configuration

**Tuning robot_localization**

---

## 🎯 Learning Objectives

- Understand configuration file
- Know which variables to fuse
- Tune parameters

---

## 📁 Configuration File

```yaml
# config/ekf_params.yaml
ekf_filter_node:
  ros__parameters:
    frequency: 25.0
    sensor_timeout: 0.1
    two_d_mode: true
    
    # Odom (wheel velocities)
    odom0: /odom
    odom0_config: [false, false, false,  # x, y, z position
                   false, false, false,  # roll, pitch, yaw
                   true,  true,  false,  # vx, vy, vz
                   false, false, true,   # vroll, vpitch, vyaw
                   false, false, false]  # ax, ay, az
    
    # IMU (from Madgwick)
    imu0: /imu/data_filtered
    imu0_config: [false, false, false,
                  false, false, true,   # yaw only
                  false, false, false,
                  false, false, true,   # vyaw
                  false, false, false]
```

---

## 🔧 Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| frequency | 25.0 | Output rate (Hz) |
| sensor_timeout | 0.1 | Max wait for data (s) |
| two_d_mode | true | Planar robot (ignore z) |

---

## 🎯 What Gets Fused?

### From Odometry
- ✅ vx, vy (linear velocities)
- ✅ vyaw (angular velocity)

### From IMU
- ✅ yaw (absolute heading)
- ✅ vyaw (yaw rate)

---

## 🎯 Key Takeaways

1. **Only fuse** what's reliable
2. **two_d_mode** for planar robots
3. **sensor_timeout** handles dropped data
4. **Process noise** controls smoothing

---

## 📖 Next Steps

Learn to launch:

**→ Continue to:** [07-localization-launch.md](07-localization-launch.md)

---

*Last Updated: March 2026*