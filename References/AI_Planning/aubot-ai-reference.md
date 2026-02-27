# AuBot AI Feature Reference for OrbiBot

Extracted from AuBot (Autonomous-Mobile-Robot) codebase analysis for OrbiBot AI integration.

---

## Task Checklist

### AI Object Detection + Person Following (HIGH PRIORITY)

- [ ] Add YOLOv8 object detection on RealSense D435
- [ ] Implement person following with D435 depth
- [ ] Create perception launch file
- [ ] `orbibot_ai` package exists as placeholder but has no active nodes

### Voice Control (LOW PRIORITY)

- [ ] English voice commands via `speech_recognition` library
- [ ] Optional feature

---

## 1. AI Person Following Mode

**AuBot Feature:** YOLOv8-based person detection with auto-follow:
- Real-time object detection on camera feed
- P-D controller for smooth following
- UDP-based velocity commands
- Toggle between AI and manual mode

**Implementation for OrbiBot:**
```python
# orbibot_ai/orbibot_ai/person_follower.py

import cv2
from ultralytics import YOLO
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

class PersonFollower(Node):
    """Follow detected persons using RealSense D435."""

    def __init__(self):
        super().__init__('person_follower')
        self.model = YOLO('yolov8n.pt')  # Nano model for speed
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # P-D controller gains
        self.kp_linear = 0.5
        self.kp_angular = 0.8
        self.target_distance = 1.5  # meters

    def detect_and_follow(self, rgb_frame, depth_frame):
        """Detect person and compute follow velocity."""
        results = self.model(rgb_frame, classes=[0])  # class 0 = person

        if len(results[0].boxes) > 0:
            # Get largest person bounding box
            box = max(results[0].boxes, key=lambda b: b.xywh[0][2] * b.xywh[0][3])
            cx = box.xywh[0][0]  # center x

            # Get depth at person center
            depth = depth_frame[int(box.xywh[0][1]), int(cx)]

            # Compute velocity commands
            twist = Twist()
            twist.linear.x = self.kp_linear * (depth - self.target_distance)
            twist.angular.z = self.kp_angular * (rgb_frame.shape[1]/2 - cx) / (rgb_frame.shape[1]/2)

            self.cmd_pub.publish(twist)
```

**Advantage:** RealSense D435 provides depth directly, eliminating the need for bounding box size estimation.

---

## 2. Voice Control Integration

**AuBot Feature:** Vietnamese voice commands for robot control.

**Implementation for OrbiBot (English):**

```python
# orbibot_teleop/orbibot_teleop/voice_control.py

import speech_recognition as sr
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

VOICE_COMMANDS = {
    'forward': (0.3, 0.0),
    'backward': (-0.3, 0.0),
    'left': (0.0, 0.5),
    'right': (0.0, -0.5),
    'stop': (0.0, 0.0),
}

class VoiceControl(Node):
    """Control robot with voice commands."""

    def __init__(self):
        super().__init__('voice_control')
        self.recognizer = sr.Recognizer()
        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def listen_and_execute(self):
        """Listen for voice command and execute."""
        with sr.Microphone() as source:
            audio = self.recognizer.listen(source, timeout=5)

        try:
            text = self.recognizer.recognize_google(audio).lower()
            for cmd, (linear, angular) in VOICE_COMMANDS.items():
                if cmd in text:
                    twist = Twist()
                    twist.linear.x = linear
                    twist.angular.z = angular
                    self.cmd_pub.publish(twist)
                    break
        except sr.UnknownValueError:
            pass
```

---

## 3. AuBot Source Files Reference

| Feature | AuBot File | Purpose |
|---------|------------|---------|
| AI Server | `web_interface/ai_server.py` | YOLOv8 + Flask streaming |

---

*Extracted from: References/aubot.md (AuBot codebase analysis)*
*Date: 2026-02-03*
