---
title: "OrbiBot Localization Study Guide"
type: learn
area: localization
package: orbibot_localization
tags:
  - learn
  - localization
---

# OrbiBot Localization Study Guide

**Robot position estimation using sensor fusion**

---

## Prerequisites

**REQUIRED:**
1. **[ROS2 Study Guide](../ros2/)** - Common ROS2 fundamentals
   - Minimum: 00-ros2-overview, 03-topics-pub-sub, 04-messages-interfaces, 09-tf2-transforms
   - Essential: Topics, message types, TF2

2. **[Sensors Study Guide](../sensors/)** - Sensor data
   - Understand LaserScan, IMU messages

3. **Linear Algebra basics** - Matrices, vectors, covariance

---

## What You'll Learn

By completing this guide, you will understand:

- **Odometry** - Position estimation from wheel encoders
- **IMU data** - Orientation from accelerometer, gyroscope, magnetometer
- **Sensor fusion** - Combining multiple sensors for better accuracy
- **EKF (Extended Kalman Filter)** - State estimation algorithm
- **Madgwick filter** - IMU orientation fusion
- **Covariance** - Uncertainty representation

---

## Study Files

| File | Topic | Time |
|------|-------|------|
| [[00-what-is-localization]] | Why estimate position? | 10 min |
| [[01-odometry-basics]] | Wheel encoder odometry | 20 min |
| [[02-imu-sensors]] | IMU: accel, gyro, mag | 25 min |
| [[03-sensor-fusion-concept]] | Why fuse sensors? | 15 min |
| [[04-madgwick-filter]] | Orientation fusion | 25 min |
| [[05-ekf-basics]] | Kalman filtering | 30 min |
| [[06-ekf-configuration]] | Tuning parameters | 25 min |
| [[07-localization-launch]] | Running the stack | 15 min |

---

## Learning Path

### Week 1: Fundamentals
- 00-what-is-localization.md
- 01-odometry-basics.md
- 02-imu-sensors.md

### Week 2: Sensor Fusion
- 03-sensor-fusion-concept.md
- 04-madgwick-filter.md
- 05-ekf-basics.md

### Week 3: Practice
- 06-ekf-configuration.md
- 07-localization-launch.md

---

## Related Files

```
src/orbibot_localization/
├── launch/
│   └── localization.launch.py   ← Main launch file
├── config/
│   └── ekf_params.yaml          ← EKF configuration
└── localization-changelog.md    ← Version history
```

---

## Start Here

**Begin with:** [[00-what-is-localization]]

---

**Happy Learning!**