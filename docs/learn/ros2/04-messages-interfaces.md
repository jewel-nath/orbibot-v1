---
title: "04 - Messages and Interfaces"
type: learn
area: ros2
tags:
  - learn
  - ros2
---

# 04 - Messages and Interfaces

**ROS2 data types and custom messages**

---

## 🎯 Learning Objectives

- Understand ROS2 message types
- Use standard messages
- Create custom messages

---

## 📨 Standard Messages

| Package | Message | Use For |
|---------|---------|---------|
| `std_msgs` | String, Int32, Float64 | Basic types |
| `geometry_msgs` | Twist, Pose, Point | Spatial data |
| `sensor_msgs` | LaserScan, Image, Imu | Sensor data |
| `nav_msgs` | Odometry, Path | Navigation |

### Common Examples

```python
from geometry_msgs.msg import Twist

msg = Twist()
msg.linear.x = 0.5   # m/s forward
msg.angular.z = 0.1  # rad/s rotation
```

```python
from sensor_msgs.msg import Imu

msg = Imu()
msg.linear_acceleration.z = 9.8  # gravity
```

---

## 📝 Custom Messages

Create `.msg` files in `msg/` directory:

```
# msg/MyCustom.msg
int32 id
float64 value
string name
```

Build to generate Python code.

---

## 🎯 Key Takeaways

1. **Messages** define data structure
2. **Standard messages** cover common use cases
3. **Custom messages** for specific needs
4. **Build** to generate code from .msg files

---

## 📖 Next Steps

**→ Continue to:** [[05-services]]

---

*Last Updated: March 2026*