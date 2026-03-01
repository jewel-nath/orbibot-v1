# 10 - Bag Recording

**Recording and replaying ROS2 data**

---

## 🎯 Learning Objectives

- Record topic data
- Play back recordings
- Use for debugging

---

## 📝 Recording

```bash
# Record specific topics
ros2 bag record /odom /imu/data

# Record all topics
ros2 bag record -a

# Custom name
ros2 bag record -o my_session /odom
```

## ▶️ Playback

```bash
# Play recording
ros2 bag play rosbag2_2024_...

# Play at half speed
ros2 bag play rosbag2_... --rate 0.5
```

---

## 🎯 Key Takeaways

1. **ros2 bag record** = Save data
2. **ros2 bag play** = Replay data
3. Use for **debugging** and **testing**

---

## 📖 Next Steps

**→ Continue to:** [11-rviz-basics.md](11-rviz-basics.md)

---

*Last Updated: March 2026*