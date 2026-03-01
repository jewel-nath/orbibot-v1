# 02 - LaserScan Message

**Understanding sensor_msgs/LaserScan**

---

## 🎯 Learning Objectives

- Understand LaserScan message structure
- Interpret range and intensity data
- Use angle information

---

## 📨 LaserScan Message

```python
from sensor_msgs.msg import LaserScan

scan = LaserScan()
scan.header.frame_id = 'lidar_link'
scan.angle_min = -3.14159      # -180°
scan.angle_max = 3.14159       # +180°
scan.angle_increment = 0.0087  # ~0.5° per reading
scan.range_min = 0.12          # 12cm minimum
scan.range_max = 8.0           # 8m maximum

scan.ranges = [1.5, 1.6, 1.7, ...]  # 720 distance values
scan.intensities = [100, 100, ...]   # Reflection strength
```

---

## 📐 Understanding Ranges Array

```
Angle:    -180°  -90°   0°   +90°  +180°
          [0]   [180] [360] [540] [720]
Ranges:   [1.5,  2.0,  1.2,  3.0,  0.8]

index = (angle - angle_min) / angle_increment
```

---

## 🎯 Key Takeaways

1. **ranges[]** = Distance at each angle
2. **angle_increment** = Angular resolution
3. **frame_id** = Sensor coordinate frame
4. **Inf values** = No obstacle detected

---

## 📖 Next Steps

Learn about cameras:

**→ Continue to:** [03-camera-basics.md](03-camera-basics.md)

---

*Last Updated: March 2026*