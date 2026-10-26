# 04 - Madgwick Filter

> **Note:** this lesson was written before 2026-04-28, when OrbiBot stopped using the ICM-20948's magnetometer. Where it mentions the magnetometer, it describes the 9-DOF mode OrbiBot no longer uses. Today the IMU sends gyro and accelerometer only, in a 12-byte packet, and the yaw comes from the gyro alone.

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
| use_mag | false | No magnetometer on OrbiBot: Madgwick runs on gyro and accel (6-DOF) |

---

## 🎯 Key Takeaways

1. **Madgwick** = Fast orientation fusion
2. **Fuses** gyro + accel (OrbiBot has no magnetometer input)
3. **Output** = Quaternion orientation
4. **Runs at** 50Hz on OrbiBot

---

## 📖 Next Steps

Learn EKF:

**→ Continue to:** [05 - EKF Basics](05-ekf-basics.md)

---

*Last Updated: March 2026*