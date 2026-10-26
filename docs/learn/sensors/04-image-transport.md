# 04 - Image Transport

**Camera data in ROS2**

---

## 🎯 Learning Objectives

- Understand sensor_msgs/Image
- Know compressed transport
- View images in RViz

---

## 📨 Image Message

```python
from sensor_msgs.msg import Image

image = Image()
image.header.frame_id = 'camera_link'
image.height = 480
image.width = 640
image.encoding = 'rgb8'
image.step = 640 * 3  # width * bytes per pixel
image.data = [...]    # Raw pixel bytes
```

---

## 🗜️ Compressed Transport

Save bandwidth with compression:

```bash
# Subscribe to compressed
/camera/color/image_raw/compressed

# ROS2 automatically decompresses
```

---

## 🖥️ Viewing Images

```bash
# rqt_image_view
ros2 run rqt_image_view rqt_image_view

# Or in RViz
# Add Image display, topic: /camera/color/image_raw
```

---

## 🎯 Key Takeaways

1. **Image message** = Raw pixel data
2. **Encoding** = Color format (rgb8, bgr8, etc.)
3. **Compressed** = Save bandwidth
4. **RViz/rqt** = View images

---

## 📖 Next Steps

Learn obstacle detection:

**→ Continue to:** [05 - Obstacle Detection](05-obstacle-detection.md)

---

*Last Updated: March 2026*