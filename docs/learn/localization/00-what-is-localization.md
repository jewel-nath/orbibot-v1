# 00 - What is Localization?

**Why robots need to know where they are**

---

## 🎯 Learning Objectives

- Understand the localization problem
- Know different localization methods
- Understand why accuracy matters

---

## 🤔 The Problem

```
You're blindfolded in a room.
Someone spins you around.
Now: Where are you? Which way is forward?

Robot without localization = You blindfolded
```

### Why It Matters

| Task | Needs Localization |
|------|------------------|
| Navigate to kitchen | ✅ Yes |
| Avoid obstacles | ✅ Yes |
| Return to charging dock | ✅ Yes |
| Patrol area | ✅ Yes |

---

## 📍 Types of Localization

### 1. Odometry (Dead Reckoning)

```
Start at (0, 0)
Move forward 1m → at (1, 0)
Turn 90° right
Move forward 1m → at (1, 1)

Problem: Small errors accumulate!
```

### 2. Global Positioning (GPS)

```
Satellites tell you absolute position
Accuracy: 1-10 meters

Problem: Not precise enough for indoor robots
```

### 3. Landmark-based

```
See known feature (door, wall corner)
Calculate position relative to feature

Problem: Need to recognize landmarks
```

### 4. Probabilistic (SLAM)

```
Combine: Odometry + Sensor data + Map
Most accurate for indoor robots

OrbiBot uses this approach!
```

---

## 🎯 OrbiBot's Approach

```
┌─────────────────────────────────────┐
│         OrbiBot Localization        │
├─────────────────────────────────────┤
│                                     │
│  1. Wheel Odometry                  │
│     └── Fast, but drifts            │
│                                     │
│  2. IMU (accelerometer + gyro)      │
│     └── Orientation, but noisy      │
│                                     │
│  3. Sensor Fusion (EKF)             │
│     └── Combine both → Better!      │
│                                     │
└─────────────────────────────────────┘
```

---

## 🎯 Key Takeaways

1. **Localization** = Knowing position and orientation
2. **Odometry** = Fast but drifts
3. **IMU** = Good orientation but noisy
4. **Sensor fusion** = Best of both worlds

---

## 📖 Next Steps

Learn about odometry:

**→ Continue to:** [01 - Odometry Basics](01-odometry-basics.md)

---

*Last Updated: March 2026*