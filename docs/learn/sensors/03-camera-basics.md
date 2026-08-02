---
title: "03 - Camera Basics"
type: learn
area: sensors
package: orbibot_sensors
tags:
  - learn
  - sensors
---

# 03 - Camera Basics

**RealSense D435 RGB-D camera**

---

## 🎯 Learning Objectives

- Understand RGB-D cameras
- Know RealSense D435 specifications
- Launch and configure camera

---

## 📷 RGB-D Camera

Provides **color (RGB)** + **depth** information.

```
RGB Image:    Depth Image:
[Colors]      [Distance per pixel]
     ↓              ↓
Combined = 3D scene understanding
```

---

## 📊 RealSense D435 Specs

| Parameter | Value |
|-----------|-------|
| RGB resolution | Up to 1280×720 |
| Depth resolution | Up to 1280×720 |
| Depth range | 0.4 - 4.0 meters |
| Frame rate | 30-60 FPS |
| Interface | USB 3.0 |

---

## 🚀 Launching the Camera

```bash
# Basic launch
ros2 launch orbibot_sensors camera.launch.py

# RPi-optimized (default)
ros2 launch orbibot_sensors camera.launch.py \
  color_width:=424 \
  color_height:=240 \
  color_fps:=15

# With pointcloud (high CPU)
ros2 launch orbibot_sensors camera.launch.py \
  enable_pointcloud:=true
```

### Verify Operation

```bash
# Check topics
ros2 topic list | grep camera

# Check rate
ros2 topic hz /camera/color/image_raw

# View image
ros2 run rqt_image_view rqt_image_view
```

---

## 🎯 Key Takeaways

1. **RGB-D** = Color + depth per pixel
2. **RealSense** = Stereo depth camera
3. **Topics** = `/camera/color/...` and `/camera/depth/...`
4. **RPi optimization** = Lower resolution for CPU

---

## 📖 Next Steps

Learn image transport:

**→ Continue to:** [[04-image-transport]]

---

*Last Updated: March 2026*