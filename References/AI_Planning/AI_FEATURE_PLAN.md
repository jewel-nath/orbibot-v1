# OrbiBot AI Feature Plan

This document outlines AI-driven robotics features for OrbiBot (Raspberry Pi 5, RealSense D435, RPLidar A1, Mecanum wheels), organized by complexity and domain.

> **For AI development workflow features** (Claude Code integration, MCP servers, code generation), see [ai_development_plan.md](ai_development_plan.md)

## Table of Contents

### I. Foundation Features (Start Here)
1. [Visual "Follow Me" & Object Tracking](#1-visual-follow-me--object-tracking)
2. [Visual Docking / Precision Parking](#2-visual-docking--precision-parking)
3. [Voice Command Interface](#3-voice-command-interface)

### II. Vision & Perception
4. [Gesture Control Teleop](#4-gesture-control-teleop)
5. [Face Recognition & Personalization](#5-face-recognition--personalization)
6. [Human Pose Estimation & Activity Recognition](#6-human-pose-estimation--activity-recognition)
7. [Scene Narration (VLM-Powered)](#7-scene-narration-vlm-powered)

### III. Autonomous Behaviors
8. [Autonomous Security Patrol](#8-autonomous-security-patrol)
9. [Semantic Navigation (LLM + VLM)](#9-semantic-navigation-llm--vlm-integration)
10. [Autonomous Object Retrieval](#10-autonomous-object-retrieval)

### IV. [Implementation Roadmap](#implementation-roadmap)

---

# I. Foundation Features (Start Here)

## 1. Visual "Follow Me" & Object Tracking
**Difficulty:** Moderate
**Hardware Used:** RealSense D435 (RGB + Depth), Raspberry Pi 5
**Prerequisites:** None (foundational feature)

**Description:**
Enable the robot to detect a specific person or object and autonomously follow them while maintaining a safe distance.

**Implementation:**
- Use **YOLOv8** (running on Pi 5 NPU/CPU) for bounding box detection on the RGB stream
- Map the bounding box center to the **Depth** stream to get the 3D position (X, Y, Z) of the target relative to the robot
- Implement a PID controller or simple logic to drive the robot to keep the target at a fixed distance (e.g., 1.0m) and centered in the frame

**Why it fits:** The Pi 5 is powerful enough for quantized YOLO models, and the Mecanum wheels allow for smooth strafing to keep the target centered without rotating the whole body if needed.

**ROS 2 Integration:**
```python
# Node structure:
# Subscribes: /camera/color/image_raw, /camera/aligned_depth_to_color/image_raw
# Publishes: /cmd_vel
# Parameters: follow_distance, max_speed, target_class (person/object)
```

---

## 2. Visual Docking / Precision Parking
**Difficulty:** Moderate
**Hardware Used:** RealSense D435
**Prerequisites:** None (foundational feature)

**Description:**
Use visual markers (AprilTags/ArUco) or shape detection to dock precisely, specifically useful for charging.

**Implementation:**
- Mecanum wheels allow for precise X and Y adjustments (strafing) to align perfectly with a connector
- The standard Lidar navigation gets you close (e.g., within 0.5m), and the Vision system takes over for the final approach
- Visual servoing loop adjusts position based on marker pose estimation

**Why it fits:** Essential for autonomous charging and teaches visual servoing fundamentals.

**ROS 2 Integration:**
```python
# Node structure:
# Subscribes: /camera/color/image_raw, /odom
# Publishes: /cmd_vel, /docking_status
# Services: /dock (trigger docking), /undock
# Uses: cv_bridge, apriltag_ros or custom ArUco detection
```

---

## 3. Voice Command Interface
**Difficulty:** Easy/Moderate
**Hardware Used:** USB Microphone, Raspberry Pi 5
**Prerequisites:** None (foundational feature)

**Description:**
Control the robot using natural voice commands like "move forward", "stop", "turn around", or "go to the kitchen".

**Implementation:**
- Use **Whisper** (OpenAI's speech-to-text, runs locally on Pi 5) or **Vosk** for offline recognition
- Parse commands into intents and map to ROS 2 actions:
    - Navigation goals (`/navigate_to_pose`)
    - Direct velocity commands (`/cmd_vel`)
    - System commands (start mapping, save map, etc.)
- Optional: Add text-to-speech feedback using **Piper** or **espeak**

**Why it fits:** Hands-free operation is intuitive and works great with semantic navigation.

**ROS 2 Integration:**
```python
# Node structure:
# Subscribes: Audio input stream
# Publishes: /cmd_vel, /voice_command_text
# Action clients: NavigateToPose
# Parameters: wake_word, language_model, confidence_threshold
```

---

# II. Vision & Perception

## 4. Gesture Control Teleop
**Difficulty:** Easy/Moderate
**Hardware Used:** RealSense D435 (RGB), Raspberry Pi 5
**Prerequisites:** Feature #1 (object detection pipeline)

**Description:**
Control the robot using hand gestures instead of a keyboard or joystick.

**Implementation:**
- Use **MediaPipe Hands** to detect hand landmarks
- Map gestures to velocity commands:
    - **Open Palm:** Stop
    - **Fist:** Move Forward
    - **Thumb Left/Right:** Strafe or Rotate Left/Right
    - **Index Finger Pointing:** Move in that direction

**Why it fits:** Makes for an impressive, interactive demo without requiring extra hardware.

**Gesture Mapping Example:**
```python
GESTURE_MAP = {
    'open_palm': (0.0, 0.0, 0.0),      # Stop
    'closed_fist': (0.3, 0.0, 0.0),    # Forward
    'thumb_left': (0.0, 0.2, 0.0),     # Strafe left
    'thumb_right': (0.0, -0.2, 0.0),   # Strafe right
    'point_up': (0.0, 0.0, 0.5),       # Rotate CCW
    'point_down': (0.0, 0.0, -0.5),    # Rotate CW
}
```

---

## 5. Face Recognition & Personalization
**Difficulty:** Moderate
**Hardware Used:** RealSense D435 (RGB), Raspberry Pi 5
**Prerequisites:** Feature #4 (vision processing pipeline)

**Description:**
Recognize known users and personalize robot behavior accordingly.

**Implementation:**
- Use **face_recognition** library or **InsightFace** for face detection and embedding
- Store face embeddings in a local database with associated user preferences
- Personalized behaviors:
    - Greet users by name
    - Adjust follow distance per user preference
    - Restrict certain commands to authorized users

**Why it fits:** Adds a personal touch and enables access control for sensitive operations.

**Database Schema:**
```python
user_profiles = {
    'user_id': {
        'name': str,
        'face_embedding': np.array,
        'preferences': {
            'follow_distance': float,
            'greeting': str,
            'access_level': int,
        }
    }
}
```

---

## 6. Human Pose Estimation & Activity Recognition
**Difficulty:** Moderate
**Hardware Used:** RealSense D435 (RGB + Depth), Raspberry Pi 5
**Prerequisites:** Feature #4 (MediaPipe pipeline)

**Description:**
Detect human poses and recognize activities (sitting, standing, waving, fallen).

**Implementation:**
- Use **MediaPipe Pose** or **MoveNet** for skeleton detection
- Map 2D keypoints to 3D using aligned depth data
- Train a simple classifier (or use rules) to recognize activities:
    - **Waving:** Trigger approach behavior
    - **Fallen person:** Send alert, approach carefully
    - **Pointing:** Move in pointed direction

**Why it fits:** Enables more natural human-robot interaction beyond simple gestures.

**Activity Rules Example:**
```python
def detect_activity(keypoints_3d):
    # Waving: Hand above shoulder, rapid motion
    if hand_y > shoulder_y and motion_speed > threshold:
        return 'waving'

    # Fallen: Hip and shoulder close to ground
    if max(hip_y, shoulder_y) < 0.5:
        return 'fallen'

    # Pointing: Extended arm with direction
    if is_arm_extended(keypoints_3d):
        return 'pointing', calculate_direction(keypoints_3d)
```

---

## 7. Scene Narration (VLM-Powered)
**Difficulty:** Moderate/Hard
**Hardware Used:** RealSense D435 (RGB), Raspberry Pi 5
**Prerequisites:** Basic vision pipeline from earlier features

**Description:**
Robot describes its surroundings using a Vision-Language Model.

**Implementation:**
- Capture images from the RGB camera periodically or on request
- Run inference using **LLaVA**, **MiniGPT-4**, or cloud API (GPT-4V, Claude Vision)
- Generate natural language descriptions: "I see a wooden desk with a laptop, a coffee mug, and some books."
- Useful for accessibility (assisting visually impaired users) or inventory tasks

**Why it fits:** Transforms raw sensor data into human-understandable context.

**ROS 2 Integration:**
```python
# Node structure:
# Subscribes: /camera/color/image_raw
# Services: /describe_scene, /answer_visual_question
# Parameters: vlm_model, use_cloud_api, prompt_template
```

---

# III. Autonomous Behaviors

## 8. Autonomous Security Patrol
**Difficulty:** Moderate
**Hardware Used:** RealSense D435, RPLidar A1, Raspberry Pi 5
**Prerequisites:** Features #1 (object detection), Nav2 navigation

**Description:**
Robot patrols predefined waypoints and detects anomalies (new objects, missing objects, or motion).

**Implementation:**
- Define patrol waypoints using Nav2's waypoint follower
- At each waypoint, capture images and compare with baseline using **image differencing** or **CLIP embeddings**
- Detect intruders/motion using background subtraction or YOLO person detection
- Send alerts (email, MQTT, or webhook) when anomalies are detected

**Why it fits:** Combines existing SLAM/navigation with computer vision for a practical home/office security application.

**Patrol Configuration:**
```yaml
patrol_waypoints:
  - name: "front_door"
    x: 2.0
    y: 0.5
    theta: 1.57
    check_interval: 60  # seconds

  - name: "living_room"
    x: 5.0
    y: 3.0
    theta: 0.0
    check_interval: 120

alert_config:
  methods: ['mqtt', 'email']
  sensitivity: 0.8
  cooldown: 300  # seconds between alerts
```

---

## 9. Semantic Navigation (LLM + VLM Integration)
**Difficulty:** Hard (Advanced)
**Hardware Used:** Raspberry Pi 5 (running local SLM or API calls), RealSense/Lidar
**Prerequisites:** Features #3 (voice commands), #7 (VLM), Nav2 SLAM

**Description:**
Give the robot natural language commands like "Go to the kitchen" or "Find the red cup".

**Implementation:**
- **Visual SLAM / Semantic Mapping:** As the robot maps (using slam_toolbox), use the camera to identify objects (chairs, tables, doors) and save their coordinates in a semantic database
- **LLM/NLP Interface:** Use a lightweight LLM (e.g., Llama-3-8B quantized or Gemma) or cloud API to parse user text/voice into ROS 2 navigation goals

**Why it fits:** Moves the robot from "Geometry-aware" (knowing where walls are) to "Context-aware" (knowing what rooms/objects are).

**Semantic Database Schema:**
```python
semantic_map = {
    'locations': [
        {
            'id': 'kitchen_001',
            'type': 'room',
            'name': 'kitchen',
            'bounds': {'x_min': 0.0, 'x_max': 4.0, 'y_min': 0.0, 'y_max': 3.0},
            'center': (2.0, 1.5),
            'objects': ['refrigerator', 'sink', 'table']
        }
    ],
    'objects': [
        {
            'id': 'obj_001',
            'class': 'chair',
            'position': (2.5, 3.1, 0.0),
            'description': 'wooden chair',
            'last_seen': timestamp
        }
    ]
}
```

---

## 10. Autonomous Object Retrieval
**Difficulty:** Hard
**Hardware Used:** RealSense D435, RPLidar A1, Raspberry Pi 5, (optional: robot arm)
**Prerequisites:** Features #1, #9 (semantic navigation)

**Description:**
Given a command like "bring me the red cup", the robot finds and retrieves the object.

**Implementation:**
- Use YOLO or CLIP for object detection and identification
- Navigate to the object using semantic map data
- If equipped with a gripper/arm, perform pick-and-place
- Without arm: Navigate to object and notify user of location

**Why it fits:** The ultimate test combining perception, navigation, and manipulation.

**Task Pipeline:**
```python
async def retrieve_object(object_description: str):
    # 1. Parse natural language
    object_query = parse_description(object_description)

    # 2. Search semantic map
    known_location = semantic_map.find(object_query)

    # 3. If not in map, search rooms
    if not known_location:
        search_result = await search_for_object(object_query)
        known_location = search_result.location

    # 4. Navigate to object
    await navigate_to(known_location)

    # 5. Visual verification
    object_pose = verify_and_localize(object_query)

    # 6. Manipulation (if arm available)
    if has_arm:
        await pick_object(object_pose)
        await navigate_to_user()
        await place_object()
    else:
        notify_user(f"Found {object_description} at {known_location}")
```

---

# Implementation Roadmap

## Recommended Starting Point

Start with **#1: Visual "Follow Me"** - it touches on the core pillars of AI robotics (Vision, Depth Processing, and Control) and provides immediate, impressive results.

## Progressive Learning Path

This roadmap takes you from foundational features through to advanced autonomous behaviors:

| Phase | Feature | Category | Difficulty | Key Skills | Est. Time |
|-------|---------|----------|------------|------------|-----------|
| 1 | Visual Follow Me (#1) | Foundation | Moderate | YOLO, depth processing, PID control | 1-2 weeks |
| 2 | Visual Docking (#2) | Foundation | Moderate | AprilTags, visual servoing | 1 week |
| 3 | Voice Commands (#3) | Foundation | Easy | Whisper/Vosk, intent parsing | 3-5 days |
| 4 | Gesture Control (#4) | Vision | Easy | MediaPipe, gesture mapping | 3-5 days |
| 5 | Face Recognition (#5) | Vision | Moderate | Face embeddings, personalization | 1 week |
| 6 | Security Patrol (#8) | Autonomous | Moderate | Nav2 waypoints, anomaly detection | 1-2 weeks |
| 7 | Scene Narration (#7) | Vision | Hard | VLM integration (LLaVA/GPT-4V) | 1-2 weeks |
| 8 | Pose Estimation (#6) | Vision | Moderate | MediaPipe Pose, activity recognition | 1 week |
| 9 | Semantic Navigation (#9) | Autonomous | Hard | LLM, semantic mapping | 2-3 weeks |
| 10 | Object Retrieval (#10) | Autonomous | Hard | CLIP, full autonomy stack | 2-3 weeks |

**Total estimated time:** 3-4 months for all features (working part-time)

## Quick Start: Feature #1 Setup

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

### 3. Create Person Tracker Node

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

### 4. Launch Integration

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

### 5. Build and Test
```bash
cd ~/orbibot_ws
colcon build --packages-select orbibot_ai
source install/setup.bash
ros2 launch orbibot_bringup ai_system.launch.py
```

## Hardware Additions to Consider

| Hardware | Required For | Estimated Cost | Notes |
|----------|--------------|----------------|-------|
| USB Microphone | Voice commands (#3) | $10-30 | USB sound card with mic |
| Speaker | Audio feedback | $15-40 | USB or 3.5mm speaker |
| Robot Arm/Gripper | Object retrieval (#10) | $200-1000+ | Check weight capacity |
| Coral TPU | Heavy ML models | $60 | 4 TOPS, USB accelerator |
| Jetson Nano | Alternative compute | $150 | If Pi 5 insufficient |
| AprilTag Markers | Visual docking (#2) | $5-10 | Print on cardstock |

## Performance Expectations on Raspberry Pi 5

| Model | Task | FPS | Notes |
|-------|------|-----|-------|
| YOLOv8n | Object detection | 15-20 | Quantized INT8 |
| MediaPipe Hands | Gesture tracking | 20-30 | Optimized for ARM |
| MediaPipe Pose | Pose estimation | 15-25 | Optimized for ARM |
| Whisper Tiny | Speech-to-text | ~2-3x realtime | Local inference |
| LLaVA 7B (quantized) | Vision-Language | 1-2 tokens/sec | Memory constrained |

**Optimization tips:**
- Use quantized models (INT8) for faster inference
- Reduce input resolution (640×480 vs 1920×1080)
- Run heavy models on cloud APIs if latency acceptable
- Consider Coral TPU for production deployments

## Next Steps

1. **Choose your starting feature** - Recommend #1 (Visual Follow Me) for maximum learning
2. **Set up development environment** - Install Python ML libraries on Pi 5
3. **Calibrate your camera** - Use RealSense SDK tools for optimal depth quality
4. **Create test scenarios** - Define success criteria before implementing
5. **Iterate and refine** - Start simple, add complexity gradually

For **AI development workflow improvements** (Claude Code hooks, MCP integration, code generation), see [ai_development_plan.md](ai_development_plan.md).

---

**Last Updated:** 2026-01-18
**Project:** OrbiBot - Mecanum Wheeled Robot
**Platform:** ROS 2 Jazzy, Raspberry Pi 5
