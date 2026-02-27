# Implementation Roadmap

This roadmap provides a progressive learning path for implementing all robotics features, organized from foundational features through to advanced autonomous behaviors.

## Recommended Starting Point

Start with **Feature #1: Visual "Follow Me"** - it touches on the core pillars of AI robotics (Vision, Depth Processing, and Control) and provides immediate, impressive results.

## Progressive Learning Path

| Phase | Feature | Category | Difficulty | Key Skills | Est. Time |
|-------|---------|----------|------------|------------|-----------|
| 1 | [Visual Follow Me](01-visual-tracking.md) (#1) | Foundation | Moderate | YOLO, depth processing, PID control | 1-2 weeks |
| 2 | [Visual Docking](02-visual-docking.md) (#2) | Foundation | Moderate | AprilTags, visual servoing | 1 week |
| 3 | [Voice Commands](03-voice-control.md) (#3) | Foundation | Easy | Whisper/Vosk, intent parsing | 3-5 days |
| 4 | [Gesture Control](04-gesture-control.md) (#4) | Vision | Easy | MediaPipe, gesture mapping | 3-5 days |
| 5 | [Face Recognition](05-face-recognition.md) (#5) | Vision | Moderate | Face embeddings, personalization | 1 week |
| 6 | [Security Patrol](08-security-patrol.md) (#8) | Autonomous | Moderate | Nav2 waypoints, anomaly detection | 1-2 weeks |
| 7 | [Scene Narration](07-scene-narration.md) (#7) | Vision | Hard | VLM integration (LLaVA/GPT-4V) | 1-2 weeks |
| 8 | [Pose Estimation](06-pose-estimation.md) (#6) | Vision | Moderate | MediaPipe Pose, activity recognition | 1 week |
| 9 | [Semantic Navigation](09-semantic-navigation.md) (#9) | Autonomous | Hard | LLM, semantic mapping | 2-3 weeks |
| 10 | [Object Retrieval](10-object-retrieval.md) (#10) | Autonomous | Hard | CLIP, full autonomy stack | 2-3 weeks |

**Total estimated time:** 3-4 months for all features (working part-time)

## Phase Breakdown

### Phase 1-3: Foundation (2-3 weeks)

**Goal:** Build core competencies in vision, motion control, and voice interaction

**Features:**
- Visual Follow Me (#1)
- Visual Docking (#2)
- Voice Commands (#3)

**Key Deliverables:**
- Robot can autonomously follow a person
- Robot can dock precisely using visual markers
- Robot responds to basic voice commands

**Skills Acquired:**
- YOLO object detection
- Depth sensor integration
- Visual servoing
- Speech recognition
- Command parsing

### Phase 2: Vision & Perception (2-3 weeks)

**Goal:** Advanced computer vision and human interaction

**Features:**
- Gesture Control (#4)
- Face Recognition (#5)
- Pose Estimation (#6)

**Key Deliverables:**
- Gesture-based teleoperation
- Personalized user recognition
- Activity recognition from human poses

**Skills Acquired:**
- MediaPipe hands/pose
- Face embeddings
- Activity classification
- User personalization

### Phase 3: Autonomous Behaviors (4-6 weeks)

**Goal:** Advanced autonomy with semantic understanding

**Features:**
- Security Patrol (#8)
- Scene Narration (#7)
- Semantic Navigation (#9)
- Object Retrieval (#10)

**Key Deliverables:**
- Autonomous patrol with anomaly detection
- Natural language scene descriptions
- Semantic map building
- Full object retrieval pipeline

**Skills Acquired:**
- Nav2 waypoint navigation
- VLM integration
- LLM-based command parsing
- Semantic mapping
- Multi-step task planning

## Hardware Additions Timeline

### Phase 1 (Immediate)
- **USB Microphone** ($10-30) - Required for voice commands
- **AprilTag Markers** ($5-10) - Required for visual docking

### Phase 2 (Optional)
- **Speaker** ($15-40) - For audio feedback
- **Coral TPU** ($60) - If performance insufficient

### Phase 3 (Advanced)
- **Robot Arm/Gripper** ($200-1000+) - For object retrieval
- **Jetson Nano** ($150) - Alternative compute if Pi 5 insufficient

## Quick Start Guide

### Week 1: Feature #1 Setup

#### Day 1-2: Environment Setup
```bash
# Create ROS 2 package
cd ~/orbibot_ws/src
ros2 pkg create orbibot_ai --build-type ament_python \
    --dependencies rclpy sensor_msgs geometry_msgs cv_bridge

# Install dependencies
pip3 install ultralytics opencv-python numpy pyrealsense2
```

#### Day 3-5: Implement Person Tracker

Create `/home/jewel/orbibot_ws/src/orbibot_ai/orbibot_ai/person_tracker_node.py`:

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

#### Day 6-7: Testing and Refinement

```bash
# Build
cd ~/orbibot_ws
colcon build --packages-select orbibot_ai
source install/setup.bash

# Test
ros2 run orbibot_ai person_tracker
```

### Week 2: Feature #2 (Visual Docking)

Follow the implementation guide in [02-visual-docking.md](02-visual-docking.md)

### Week 3: Feature #3 (Voice Commands)

Follow the implementation guide in [03-voice-control.md](03-voice-control.md)

## Performance Expectations on Raspberry Pi 5

| Model | Task | FPS | Memory | Notes |
|-------|------|-----|--------|-------|
| YOLOv8n | Object detection | 15-20 | 500MB | Quantized INT8 |
| MediaPipe Hands | Gesture tracking | 20-30 | 200MB | Optimized for ARM |
| MediaPipe Pose | Pose estimation | 15-25 | 250MB | Optimized for ARM |
| Whisper Tiny | Speech-to-text | ~2-3x realtime | 1GB | Local inference |
| LLaVA 7B (quantized) | Vision-Language | 1-2 tokens/sec | 4GB | Memory constrained |

### Optimization Tips

1. **Use quantized models (INT8)** for faster inference
2. **Reduce input resolution** (640×480 vs 1920×1080)
3. **Run heavy models on cloud APIs** if latency acceptable
4. **Consider Coral TPU** for production deployments
5. **Batch processing** when real-time not required

## Success Criteria

### Foundation Phase
- [ ] Robot follows person maintaining 1m distance
- [ ] Robot docks within 2cm accuracy
- [ ] Voice commands recognized with >85% accuracy

### Vision Phase
- [ ] Gesture control works at 2m distance
- [ ] Face recognition >95% accuracy for enrolled users
- [ ] Activity recognition correctly identifies 5+ activities

### Autonomous Phase
- [ ] Security patrol completes route without intervention
- [ ] Scene descriptions are contextually accurate
- [ ] Semantic navigation succeeds for 90%+ of commands
- [ ] Object retrieval finds correct object 80%+ of time

## Troubleshooting Common Issues

### Performance Issues
- **Symptom:** Low FPS, laggy response
- **Solution:** Use lighter models, reduce resolution, enable quantization

### Memory Issues
- **Symptom:** Out of memory errors
- **Solution:** Close unused models, use swap, upgrade to cloud APIs

### Navigation Issues
- **Symptom:** Robot gets stuck, poor localization
- **Solution:** Tune Nav2 parameters, improve map quality, check TF tree

### Detection Issues
- **Symptom:** Poor object/face detection
- **Solution:** Improve lighting, re-train models, adjust confidence thresholds

## Next Steps

1. **Choose your starting feature** - Recommend #1 (Visual Follow Me) for maximum learning
2. **Set up development environment** - Install Python ML libraries on Pi 5
3. **Calibrate your camera** - Use RealSense SDK tools for optimal depth quality
4. **Create test scenarios** - Define success criteria before implementing
5. **Iterate and refine** - Start simple, add complexity gradually

## Resources

### Documentation
- [Main Documentation](../README.md)
- [Features Index](README.md)
- [AI Development Features](../developer-features/)

### Community
- ROS Discourse: https://discourse.ros.org
- YOLO: https://github.com/ultralytics/ultralytics
- MediaPipe: https://developers.google.com/mediapipe

### Hardware Vendors
- RealSense: https://www.intelrealsense.com
- Coral TPU: https://coral.ai
- Jetson: https://developer.nvidia.com/jetson

---

**Last Updated:** 2026-01-20
**Project:** OrbiBot - Mecanum Wheeled Robot
**Platform:** ROS 2 Jazzy, Raspberry Pi 5

[← Previous: Object Retrieval](10-object-retrieval.md) | [↑ Index](README.md)
