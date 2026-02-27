# 4. Gesture Control Teleop

**Difficulty:** Easy/Moderate
**Hardware Used:** RealSense D435 (RGB), Raspberry Pi 5
**Prerequisites:** Feature #1 (object detection pipeline)

## Description

Control the robot using hand gestures instead of a keyboard or joystick.

## Implementation

- Use **MediaPipe Hands** to detect hand landmarks
- Map gestures to velocity commands:
    - **Open Palm:** Stop
    - **Fist:** Move Forward
    - **Thumb Left/Right:** Strafe or Rotate Left/Right
    - **Index Finger Pointing:** Move in that direction

## Why It Fits

Makes for an impressive, interactive demo without requiring extra hardware.

## Gesture Mapping

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

## Implementation

### MediaPipe Hand Detection

```python
import mediapipe as mp
import cv2
from cv_bridge import CvBridge

class GestureControlNode(Node):
    def __init__(self):
        super().__init__('gesture_control')

        # MediaPipe setup
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.mp_draw = mp.solutions.drawing_utils

        # ROS setup
        self.bridge = CvBridge()
        self.image_sub = self.create_subscription(
            Image, '/camera/color/image_raw',
            self.image_callback, 10
        )
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

        # Gesture state
        self.current_gesture = 'open_palm'
        self.gesture_history = []

    def image_callback(self, msg):
        # Convert to OpenCV
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process hands
        results = self.hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Recognize gesture
                gesture = self.recognize_gesture(hand_landmarks)

                # Publish velocity
                self.publish_gesture_velocity(gesture)

                # Draw landmarks (for debugging)
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks,
                    self.mp_hands.HAND_CONNECTIONS
                )
```

### Gesture Recognition Logic

```python
def recognize_gesture(self, hand_landmarks):
    """
    Recognize gesture from hand landmarks

    Hand landmarks indices (MediaPipe):
    0: Wrist
    4: Thumb tip
    8: Index finger tip
    12: Middle finger tip
    16: Ring finger tip
    20: Pinky tip
    """
    landmarks = hand_landmarks.landmark

    # Extract key points
    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    middle_tip = landmarks[12]
    ring_tip = landmarks[16]
    pinky_tip = landmarks[20]

    wrist = landmarks[0]
    index_mcp = landmarks[5]  # Index finger base

    # Calculate finger states
    fingers_up = self.count_fingers_up(landmarks)

    # Gesture classification
    if fingers_up == 0:
        return 'closed_fist'

    elif fingers_up == 5:
        return 'open_palm'

    elif fingers_up == 1 and index_tip.y < index_mcp.y:
        # Only index finger extended and pointing up
        if index_tip.y < wrist.y - 0.1:
            return 'point_up'
        elif index_tip.y > wrist.y + 0.1:
            return 'point_down'

    elif thumb_tip.x < wrist.x - 0.1:
        return 'thumb_left'

    elif thumb_tip.x > wrist.x + 0.1:
        return 'thumb_right'

    return 'unknown'

def count_fingers_up(self, landmarks):
    """Count number of extended fingers"""
    finger_tips = [4, 8, 12, 16, 20]
    finger_pips = [3, 6, 10, 14, 18]

    count = 0
    for tip, pip in zip(finger_tips, finger_pips):
        if landmarks[tip].y < landmarks[pip].y:
            count += 1

    return count
```

### Velocity Publishing with Smoothing

```python
def publish_gesture_velocity(self, gesture):
    """
    Publish velocity command based on gesture
    with temporal smoothing to avoid jitter
    """
    # Add to history
    self.gesture_history.append(gesture)
    if len(self.gesture_history) > 5:
        self.gesture_history.pop(0)

    # Use most common gesture in history (voting)
    from collections import Counter
    most_common = Counter(self.gesture_history).most_common(1)[0][0]

    # Get velocity from gesture map
    if most_common in GESTURE_MAP:
        vx, vy, vz = GESTURE_MAP[most_common]

        twist = Twist()
        twist.linear.x = vx
        twist.linear.y = vy
        twist.angular.z = vz

        self.cmd_vel_pub.publish(twist)

        # Log gesture
        if most_common != self.current_gesture:
            self.get_logger().info(f'Gesture: {most_common}')
            self.current_gesture = most_common
```

## Advanced Gestures

### Distance-Based Speed Control

```python
def calculate_speed_from_distance(self, hand_landmarks):
    """
    Use distance between hands (or hand size) to control speed
    """
    # Get hand bounding box
    x_coords = [lm.x for lm in hand_landmarks.landmark]
    y_coords = [lm.y for lm in hand_landmarks.landmark]

    hand_width = max(x_coords) - min(x_coords)

    # Map hand size to speed (closer = larger = faster)
    speed_multiplier = np.clip(hand_width * 3.0, 0.1, 1.0)

    return speed_multiplier
```

### Two-Hand Control

```python
def process_two_hands(self, results):
    """
    Use two hands for more complex control
    Left hand: direction
    Right hand: speed
    """
    if len(results.multi_hand_landmarks) == 2:
        left_hand = results.multi_hand_landmarks[0]
        right_hand = results.multi_hand_landmarks[1]

        direction = self.recognize_gesture(left_hand)
        speed = self.calculate_speed_from_distance(right_hand)

        return direction, speed
```

### Gesture Sequences

```python
class GestureSequenceDetector:
    """Detect gesture sequences (e.g., swipe left then right)"""

    def __init__(self):
        self.sequence = []
        self.sequence_timeout = 2.0  # seconds
        self.last_gesture_time = 0

    def add_gesture(self, gesture, timestamp):
        # Reset if timeout
        if timestamp - self.last_gesture_time > self.sequence_timeout:
            self.sequence = []

        self.sequence.append(gesture)
        self.last_gesture_time = timestamp

        # Check for known sequences
        if self.sequence == ['thumb_left', 'thumb_right']:
            return 'cancel_command'

        elif self.sequence == ['point_up', 'point_up']:
            return 'increase_speed'

        return None
```

## Safety Features

### Deadman Switch

```python
def check_hand_visible(self, results):
    """
    Require hand visible to continue motion
    Stop robot if no hand detected (safety feature)
    """
    if not results.multi_hand_landmarks:
        # No hand detected - stop robot
        self.publish_stop_command()
        return False
    return True
```

### Gesture Confirmation

```python
def require_confirmation_gesture(self):
    """
    Require specific gesture sequence for dangerous operations
    """
    confirmation_sequence = ['open_palm', 'closed_fist', 'open_palm']

    if self.gesture_history[-3:] == confirmation_sequence:
        return True
    return False
```

## Configuration Parameters

```yaml
gesture_control:
  # MediaPipe settings
  max_num_hands: 1
  min_detection_confidence: 0.7
  min_tracking_confidence: 0.5

  # Gesture smoothing
  history_size: 5

  # Velocity limits
  max_linear_speed: 0.3  # m/s
  max_angular_speed: 0.5  # rad/s

  # Safety
  require_hand_visible: true
  hand_timeout: 1.0  # seconds

  # Gesture mapping
  gestures:
    open_palm: [0.0, 0.0, 0.0]
    closed_fist: [0.3, 0.0, 0.0]
    thumb_left: [0.0, 0.2, 0.0]
    thumb_right: [0.0, -0.2, 0.0]
```

## Installation

```bash
# Install MediaPipe
pip3 install mediapipe opencv-python

# Install ROS dependencies
sudo apt-get install ros-jazzy-cv-bridge
```

## Testing

```bash
# Test hand detection
ros2 run orbibot_ai test_hand_detection

# Test gesture recognition
ros2 run orbibot_ai test_gesture_recognition

# Full gesture control
ros2 launch orbibot_ai gesture_control.launch.py
```

## Performance

| Model | Task | FPS | CPU Usage | Notes |
|-------|------|-----|-----------|-------|
| MediaPipe Hands | Gesture tracking | 20-30 | Low | Optimized for ARM |

## Gesture Reference Card

```
┌─────────────────────────────────────┐
│     GESTURE CONTROL REFERENCE       │
├─────────────────────────────────────┤
│ ✋ Open Palm      → Stop             │
│ ✊ Closed Fist    → Move Forward     │
│ 👍 Thumb Left     → Strafe Left      │
│ 👎 Thumb Right    → Strafe Right     │
│ ☝️ Point Up       → Rotate Left      │
│ 👇 Point Down     → Rotate Right     │
└─────────────────────────────────────┘
```

---

[← Previous: Voice Control](03-voice-control.md) | [↑ Index](README.md) | [Next: Face Recognition →](05-face-recognition.md)
