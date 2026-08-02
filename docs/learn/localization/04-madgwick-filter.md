---
title: "04 - Madgwick Filter"
type: learn
area: localization
package: orbibot_localization
tags:
  - learn
  - localization
---

# 04 - Madgwick Filter

**IMU orientation fusion**

---

## 🎯 Learning Objectives

- Understand Madgwick algorithm
- Know when to use it
- Configure parameters

---

## 🧮 What is Madgwick?

**Madgwick filter** = Sensor fusion algorithm for orientation.

```
Inputs:
├── Gyroscope (rotation rate)
├── Accelerometer (gravity reference)
└── Magnetometer (north reference)

Output:
└── Orientation quaternion (roll, pitch, yaw)
```

### Why Madgwick?

```
✅ Fast (computationally efficient)
✅ Accurate
✅ Works with 6-DOF (accel + gyro) or 9-DOF (+ mag)
✅ Good for real-time systems
```

---

## ⚙️ Parameters

| Parameter | Default | Effect |
|-----------|---------|--------|
| gain | 0.1 | Higher = faster response, more noise |
| zeta | 0.0 | Gyro drift compensation |
| use_mag | true | Use magnetometer for yaw |

---

## 🎯 Key Takeaways

1. **Madgwick** = Fast orientation fusion
2. **Fuses** gyro + accel + mag
3. **Output** = Quaternion orientation
4. **Runs at** 50Hz on OrbiBot

---

## 📖 Next Steps

Learn EKF:

**→ Continue to:** [[05-ekf-basics]]

---

*Last Updated: March 2026*