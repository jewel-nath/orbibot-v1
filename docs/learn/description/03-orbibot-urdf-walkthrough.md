# 03 - OrbiBot URDF Walkthrough

**Complete analysis of orbibot.urdf.xacro**

---

## 🎯 Learning Objectives

- Understand OrbiBot's complete URDF structure
- See how Xacro macros are used
- Know the robot's physical parameters

---

## 📁 File Structure

```
orbibot.urdf.xacro
├── Robot parameters (wheel size, track width)
├── Base link (chassis)
├── Wheel macros (4 mecanum wheels)
└── Sensor mounts (LiDAR, IMU, Camera)
```

---

## 🔢 Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| wheel_radius | 0.05 m | 50mm radius |
| wheel_width | 0.04 m | 40mm width |
| track_width | 0.36 m | Left-right distance |
| wheelbase | 0.26 m | Front-rear distance |

---

## 🦽 Wheel Configuration

**Mecanum ABBA Pattern:**

```
     Front
  FL(A)  FR(B)
     \  /
      \/     A = +45° rollers
      /\     B = -45° rollers
     /  \
  BL(B)  BR(A)
```

---

## 🎯 Key Takeaways

1. **Parameters** defined at top
2. **Base link** is robot center
3. **4 wheels** with continuous joints
4. **Sensors** mounted with fixed joints

---

## 📖 Next Steps

Learn about coordinate frames:

**→ Continue to:** [04 - TF Tree](04-tf-tree.md)

---

*Last Updated: March 2026*