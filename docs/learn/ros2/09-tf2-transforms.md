# 09 - TF2 Transforms

**Coordinate frame management**

---

## 🎯 Learning Objectives

- Understand coordinate frames
- Use TF2 for spatial relationships
- Transform between frames

---

## 📍 What is TF2?

**TF2** tracks spatial relationships between coordinate frames.

```
Robot Frame Hierarchy:
map (world)
└── odom (origin)
    └── base_link (robot center)
        ├── imu_link
        ├── laser_link
        └── camera_link
```

---

## 🎯 Key Takeaways

1. **TF2** = Coordinate frame tree
2. **Static transforms** = Fixed relationships
3. **Dynamic transforms** = Moving relationships
4. **Essential** for navigation, sensor fusion

---

## 📖 Next Steps

**→ Continue to:** [10 - Bag Recording](10-bag-recording.md)

---

*Last Updated: March 2026*