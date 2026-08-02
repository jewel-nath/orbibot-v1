---
title: "03 - Sensor Fusion Concept"
type: learn
area: localization
package: orbibot_localization
tags:
  - learn
  - localization
---

# 03 - Sensor Fusion Concept

**Combining sensors for better accuracy**

---

## 🎯 Learning Objectives

- Understand why fuse sensors
- Know complementary filtering
- Understand the fusion pipeline

---

## 🤔 Why Fuse Sensors?

### Odometry Alone
```
✅ Fast (50Hz)
✅ Good position short-term
❌ Drifts over time
```

### IMU Alone
```
✅ Good orientation
✅ Fast response
❌ No position
❌ Gyro drifts
```

### Fused Together
```
✅ Fast
✅ Accurate position
✅ Accurate orientation
✅ Reduced drift
```

---

## 🔄 Sensor Fusion Pipeline

```
┌─────────────────────────────────────────┐
│         OrbiBot Fusion Pipeline         │
├─────────────────────────────────────────┤
│                                         │
│  IMU Raw Data                           │
│  ├── /imu/data_raw (accel, gyro)        │
│  └── /imu/mag (magnetometer)            │
│         ↓                               │
│  Madgwick Filter (50Hz)                 │
│  └── Fuses: gyro + accel + mag          │
│  └── Output: /imu/data_filtered         │
│         ↓                               │
│  EKF (25Hz)                             │
│  ├── Input: /imu/data_filtered          │
│  ├── Input: /odom (wheel velocities)    │
│  └── Output: /odometry/filtered         │
│                                         │
└─────────────────────────────────────────┘
```

---

## 🎯 Key Takeaways

1. **Each sensor** has strengths and weaknesses
2. **Fusion** = Combine strengths, cancel weaknesses
3. **Two-stage** = Madgwick for orientation, EKF for full state
4. **Result** = Better than any single sensor

---

## 📖 Next Steps

Learn Madgwick filter:

**→ Continue to:** [[04-madgwick-filter]]

---

*Last Updated: March 2026*