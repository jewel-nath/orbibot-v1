# 1. Visual "Follow Me" & Object Tracking

**Difficulty:** Moderate
**Hardware Used:** RealSense D435 (RGB + Depth), Raspberry Pi 5
**Prerequisites:** None (foundational feature)

## Description

Enable the robot to detect a specific person or object and autonomously follow them while maintaining a safe distance.

## Implementation

- Use **YOLOv8** (running on Pi 5 NPU/CPU) for bounding box detection on the RGB stream
- Map the bounding box center to the **Depth** stream to get the 3D position (X, Y, Z) of the target relative to the robot
- Implement a PID controller or simple logic to drive the robot to keep the target at a fixed distance (e.g., 1.0m) and centered in the frame

## Why It Fits

The Pi 5 is powerful enough for quantized YOLO models, and the Mecanum wheels allow for smooth strafing to keep the target centered without rotating the whole body if needed.

## ROS 2 Integration

```python
# Node structure:
# Subscribes: /camera/color/image_raw, /camera/aligned_depth_to_color/image_raw
# Publishes: /cmd_vel
# Parameters: follow_distance, max_speed, target_class (person/object)
```

## Example Implementation

Create `orbibot_ai/orbibot_ai/person_tracker_node.py`:

```python
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from cv_bridge import CvBridge
from ultralytics import YOLO
import numpy as np

class PersonTrackerNode(Node):
    def __init__(self):
        super().__init__('person_tracker')

        # Load YOLOv8 model
        self.model = YOLO('yolov8n.pt')  # Nano model for Pi 5

        # Subscribers
        self.rgb_sub = self.create_subscription(
            Image, '/camera/color/image_raw',
            self.rgb_callback, 10)
        self.depth_sub = self.create_subscription(
            Image, '/camera/aligned_depth_to_color/image_raw',
            self.depth_callback, 10)

        # Publisher
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # State
        self.bridge = CvBridge()
        self.latest_depth = None
        self.target_distance = 1.0  # meters

    def rgb_callback(self, msg):
        # Convert ROS Image to OpenCV
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

        # Run YOLO detection
        results = self.model(frame, classes=[0])  # class 0 = person

        if len(results[0].boxes) > 0:
            # Get largest detection (closest person)
            box = results[0].boxes[0]
            cx, cy = box.xywh[0][:2].cpu().numpy()

            # Get depth at center
            if self.latest_depth is not None:
                depth = self.latest_depth[int(cy), int(cx)]
                self.follow_target(cx, cy, depth, frame.shape)

    def depth_callback(self, msg):
        self.latest_depth = self.bridge.imgmsg_to_cv2(msg, '16UC1') / 1000.0

    def follow_target(self, cx, cy, depth, shape):
        twist = Twist()

        # PID-like control
        error_x = (cx - shape[1]/2) / (shape[1]/2)  # Normalized [-1, 1]
        error_dist = depth - self.target_distance

        # Strafe to center target
        twist.linear.y = -error_x * 0.2

        # Move forward/backward to maintain distance
        twist.linear.x = error_dist * 0.3

        self.cmd_vel_pub.publish(twist)

def main():
    rclpy.init()
    node = PersonTrackerNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
```

## Setup Instructions

### 1. Create ROS 2 Package

```bash
cd ~/orbibot_ws/src
ros2 pkg create orbibot_ai --build-type ament_python \
    --dependencies rclpy sensor_msgs geometry_msgs cv_bridge
```

### 2. Install Dependencies

```bash
pip3 install ultralytics opencv-python numpy pyrealsense2
```

### 3. Launch Integration

Add to `orbibot_bringup/launch/ai_system.launch.py`:

```python
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='orbibot_ai',
            executable='person_tracker',
            name='person_tracker',
            parameters=[{
                'target_distance': 1.0,
                'max_speed': 0.3,
            }]
        ),
    ])
```

### 4. Build and Test

```bash
cd ~/orbibot_ws
colcon build --packages-select orbibot_ai
source install/setup.bash
ros2 launch orbibot_bringup ai_system.launch.py
```

## Performance Expectations

| Model | Task | FPS | Notes |
|-------|------|-----|-------|
| YOLOv8n | Object detection | 15-20 | Quantized INT8 |

**Optimization tips:**
- Use quantized models (INT8) for faster inference
- Reduce input resolution (640×480 vs 1920×1080)
- Consider Coral TPU for production deployments

---

[↑ Index](README.md) | [Next: Visual Docking →](02-visual-docking.md)
