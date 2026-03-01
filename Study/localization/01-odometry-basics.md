# 01 - Odometry Basics

**Position from wheel encoders**

---

## 🎯 Learning Objectives

- Understand how wheel odometry works
- Know odometry message format
- Understand drift problem

---

## 🔄 How Odometry Works

```
Encoders count wheel rotations
    ↓
Know wheel circumference
    ↓
Calculate distance traveled
    ↓
Integrate to get position
```

### The Math

```
distance = encoder_counts × (2π × radius) / counts_per_rev

position = previous_position + distance
```

---

## 📨 Odometry Message

```python
from nav_msgs.msg import Odometry

odom = Odometry()
odom.header.frame_id = 'odom'
odom.child_frame_id = 'base_footprint'

# Position
odom.pose.pose.position.x = 1.5  # meters
odom.pose.pose.position.y = 0.5
odom.pose.pose.orientation.z = 0.707  # quaternion

# Velocity
odom.twist.twist.linear.x = 0.3   # m/s forward
odom.twist.twist.angular.z = 0.1  # rad/s rotation
```

---

## ⚠️ The Drift Problem

```
True path:    Straight line
Odometry:     _/_/_/  (curves due to slip)

Errors accumulate over time!
```

---

## 🎯 Key Takeaways

1. **Odometry** = Position from wheel encoders
2. **Fast update** (20-50Hz)
3. **Drifts** over time due to wheel slip
4. **Needs correction** from other sensors

---

## 📖 Next Steps

Learn about IMU:

**→ Continue to:** [02-imu-sensors.md](02-imu-sensors.md)

---

*Last Updated: March 2026*