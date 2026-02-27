# 6. Human Pose Estimation & Activity Recognition

**Difficulty:** Moderate
**Hardware Used:** RealSense D435 (RGB + Depth), Raspberry Pi 5
**Prerequisites:** Feature #4 (MediaPipe pipeline)

## Description

Detect human poses and recognize activities (sitting, standing, waving, fallen).

## Implementation

- Use **MediaPipe Pose** or **MoveNet** for skeleton detection
- Map 2D keypoints to 3D using aligned depth data
- Train a simple classifier (or use rules) to recognize activities:
    - **Waving:** Trigger approach behavior
    - **Fallen person:** Send alert, approach carefully
    - **Pointing:** Move in pointed direction

## Why It Fits

Enables more natural human-robot interaction beyond simple gestures.

## Activity Rules Example

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

## Implementation

### Pose Estimation Node

```python
import mediapipe as mp
import numpy as np

class PoseEstimationNode(Node):
    def __init__(self):
        super().__init__('pose_estimation')

        # MediaPipe Pose setup
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,  # 0=lite, 1=full, 2=heavy
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

        # ROS setup
        self.bridge = CvBridge()
        self.rgb_sub = self.create_subscription(
            Image, '/camera/color/image_raw',
            self.rgb_callback, 10
        )
        self.depth_sub = self.create_subscription(
            Image, '/camera/aligned_depth_to_color/image_raw',
            self.depth_callback, 10
        )

        # Publishers
        self.activity_pub = self.create_publisher(
            String, '/detected_activity', 10
        )
        self.pose_pub = self.create_publisher(
            PoseArray, '/human_poses', 10
        )

        # State
        self.latest_depth = None
        self.pose_history = []

    def rgb_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Process pose
        results = self.pose.process(rgb_frame)

        if results.pose_landmarks:
            # Convert to 3D using depth
            keypoints_3d = self.map_to_3d(
                results.pose_landmarks,
                frame.shape
            )

            # Recognize activity
            activity = self.recognize_activity(keypoints_3d)

            if activity:
                self.publish_activity(activity)

    def depth_callback(self, msg):
        self.latest_depth = self.bridge.imgmsg_to_cv2(msg, '16UC1') / 1000.0
```

### 3D Keypoint Mapping

```python
def map_to_3d(self, pose_landmarks, image_shape):
    """
    Convert 2D pose landmarks to 3D using depth data

    MediaPipe Pose Landmarks (33 points):
    0: Nose, 1: Left Eye Inner, 2: Left Eye, 3: Left Eye Outer,
    4: Right Eye Inner, 5: Right Eye, 6: Right Eye Outer,
    7: Left Ear, 8: Right Ear, 9: Mouth Left, 10: Mouth Right,
    11: Left Shoulder, 12: Right Shoulder,
    13: Left Elbow, 14: Right Elbow,
    15: Left Wrist, 16: Right Wrist,
    23: Left Hip, 24: Right Hip,
    25: Left Knee, 26: Right Knee,
    27: Left Ankle, 28: Right Ankle
    """
    keypoints_3d = []

    height, width = image_shape[:2]

    for landmark in pose_landmarks.landmark:
        # Convert normalized coords to pixels
        x_px = int(landmark.x * width)
        y_px = int(landmark.y * height)

        # Get depth at keypoint
        if self.latest_depth is not None:
            x_px = np.clip(x_px, 0, width - 1)
            y_px = np.clip(y_px, 0, height - 1)
            depth = self.latest_depth[y_px, x_px]

            # Convert to 3D camera coordinates
            # (requires camera intrinsics)
            x_3d, y_3d, z_3d = self.pixel_to_3d(x_px, y_px, depth)

            keypoints_3d.append({
                'x': x_3d,
                'y': y_3d,
                'z': z_3d,
                'visibility': landmark.visibility
            })
        else:
            # Fallback to 2D + estimated depth
            keypoints_3d.append({
                'x': landmark.x,
                'y': landmark.y,
                'z': landmark.z,  # MediaPipe estimated depth
                'visibility': landmark.visibility
            })

    return keypoints_3d

def pixel_to_3d(self, x_px, y_px, depth):
    """Convert pixel coordinates + depth to 3D camera coordinates"""
    # RealSense D435 intrinsics (example - get from camera)
    fx = 616.0  # focal length x
    fy = 616.0  # focal length y
    cx = 320.0  # principal point x
    cy = 240.0  # principal point y

    x_3d = (x_px - cx) * depth / fx
    y_3d = (y_px - cy) * depth / fy
    z_3d = depth

    return x_3d, y_3d, z_3d
```

### Activity Recognition

```python
class ActivityRecognizer:
    """Recognize human activities from pose keypoints"""

    # Keypoint indices (MediaPipe Pose)
    NOSE = 0
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self, node):
        self.node = node
        self.pose_history = []
        self.motion_threshold = 0.3  # m/s

    def recognize_activity(self, keypoints_3d):
        """Main activity recognition logic"""
        # Add to history
        self.pose_history.append({
            'keypoints': keypoints_3d,
            'timestamp': time.time()
        })

        # Keep only recent history (1 second at 30 FPS)
        if len(self.pose_history) > 30:
            self.pose_history.pop(0)

        # Rule-based activity detection
        activities = []

        # Check for waving
        if self.is_waving(keypoints_3d):
            activities.append('waving')

        # Check for fallen person
        if self.is_fallen(keypoints_3d):
            activities.append('fallen')

        # Check for pointing
        pointing = self.is_pointing(keypoints_3d)
        if pointing:
            activities.append(('pointing', pointing['direction']))

        # Check for sitting/standing
        posture = self.detect_posture(keypoints_3d)
        activities.append(posture)

        return activities

    def is_waving(self, keypoints_3d):
        """Detect waving: hand above shoulder, rapid motion"""
        left_wrist = keypoints_3d[self.LEFT_WRIST]
        right_wrist = keypoints_3d[self.RIGHT_WRIST]
        left_shoulder = keypoints_3d[self.LEFT_SHOULDER]
        right_shoulder = keypoints_3d[self.RIGHT_SHOULDER]

        # Check if either hand is above shoulder
        left_raised = left_wrist['y'] < left_shoulder['y']
        right_raised = right_wrist['y'] < right_shoulder['y']

        if not (left_raised or right_raised):
            return False

        # Check for rapid motion
        if len(self.pose_history) < 10:
            return False

        # Calculate wrist motion speed
        wrist_idx = self.LEFT_WRIST if left_raised else self.RIGHT_WRIST
        motion_speed = self.calculate_motion_speed(wrist_idx)

        return motion_speed > self.motion_threshold

    def is_fallen(self, keypoints_3d):
        """Detect fallen person: torso horizontal"""
        left_shoulder = keypoints_3d[self.LEFT_SHOULDER]
        right_shoulder = keypoints_3d[self.RIGHT_SHOULDER]
        left_hip = keypoints_3d[self.LEFT_HIP]
        right_hip = keypoints_3d[self.RIGHT_HIP]

        # Average shoulder and hip heights
        shoulder_y = (left_shoulder['y'] + right_shoulder['y']) / 2
        hip_y = (left_hip['y'] + right_hip['y']) / 2

        # If both are close to ground (low Y in camera frame)
        # Note: In camera coords, Y increases downward
        ground_threshold = 0.5  # meters from camera

        if shoulder_y < ground_threshold and hip_y < ground_threshold:
            return True

        return False

    def is_pointing(self, keypoints_3d):
        """Detect pointing: extended arm with clear direction"""
        # Check both arms
        for side in ['left', 'right']:
            if side == 'left':
                shoulder = keypoints_3d[self.LEFT_SHOULDER]
                elbow = keypoints_3d[self.LEFT_ELBOW]
                wrist = keypoints_3d[self.LEFT_WRIST]
            else:
                shoulder = keypoints_3d[self.RIGHT_SHOULDER]
                elbow = keypoints_3d[self.RIGHT_ELBOW]
                wrist = keypoints_3d[self.RIGHT_WRIST]

            # Check if arm is extended
            if self.is_arm_extended(shoulder, elbow, wrist):
                # Calculate pointing direction
                direction = self.calculate_pointing_direction(shoulder, wrist)
                return {
                    'side': side,
                    'direction': direction
                }

        return None

    def is_arm_extended(self, shoulder, elbow, wrist):
        """Check if arm is in extended position"""
        # Calculate arm segments
        upper_arm = np.array([
            elbow['x'] - shoulder['x'],
            elbow['y'] - shoulder['y'],
            elbow['z'] - shoulder['z']
        ])

        forearm = np.array([
            wrist['x'] - elbow['x'],
            wrist['y'] - elbow['y'],
            wrist['z'] - elbow['z']
        ])

        # Check if segments are aligned (small angle)
        upper_norm = np.linalg.norm(upper_arm)
        forearm_norm = np.linalg.norm(forearm)

        if upper_norm == 0 or forearm_norm == 0:
            return False

        # Cosine of angle between segments
        cos_angle = np.dot(upper_arm, forearm) / (upper_norm * forearm_norm)

        # Extended if angle > 150 degrees (cos < -0.866)
        return cos_angle > 0.7  # ~45 degrees or less

    def calculate_pointing_direction(self, shoulder, wrist):
        """Calculate 3D direction vector of pointing arm"""
        direction = np.array([
            wrist['x'] - shoulder['x'],
            wrist['y'] - shoulder['y'],
            wrist['z'] - shoulder['z']
        ])

        # Normalize
        direction = direction / np.linalg.norm(direction)

        # Convert to angle (yaw in robot frame)
        yaw = np.arctan2(direction[0], direction[2])

        return {
            'vector': direction,
            'yaw': yaw,
            'description': self.direction_to_text(yaw)
        }

    def direction_to_text(self, yaw):
        """Convert yaw angle to cardinal direction"""
        angle_deg = np.degrees(yaw)

        if -45 < angle_deg <= 45:
            return 'forward'
        elif 45 < angle_deg <= 135:
            return 'left'
        elif -135 < angle_deg <= -45:
            return 'right'
        else:
            return 'backward'

    def detect_posture(self, keypoints_3d):
        """Detect sitting vs standing posture"""
        left_hip = keypoints_3d[self.LEFT_HIP]
        right_hip = keypoints_3d[self.RIGHT_HIP]
        left_knee = keypoints_3d[self.LEFT_KNEE]
        right_knee = keypoints_3d[self.RIGHT_KNEE]

        # Calculate hip-knee angle
        hip_y = (left_hip['y'] + right_hip['y']) / 2
        knee_y = (left_knee['y'] + right_knee['y']) / 2

        # Sitting: knees roughly at same height as hips
        if abs(hip_y - knee_y) < 0.2:
            return 'sitting'
        # Standing: knees below hips
        elif knee_y > hip_y + 0.2:
            return 'standing'
        else:
            return 'transitioning'

    def calculate_motion_speed(self, keypoint_idx):
        """Calculate motion speed of specific keypoint"""
        if len(self.pose_history) < 2:
            return 0.0

        # Get current and previous keypoint positions
        current = self.pose_history[-1]['keypoints'][keypoint_idx]
        previous = self.pose_history[-10]['keypoints'][keypoint_idx]

        # Calculate distance
        dx = current['x'] - previous['x']
        dy = current['y'] - previous['y']
        dz = current['z'] - previous['z']
        distance = np.sqrt(dx**2 + dy**2 + dz**2)

        # Calculate time difference
        dt = self.pose_history[-1]['timestamp'] - self.pose_history[-10]['timestamp']

        if dt == 0:
            return 0.0

        return distance / dt
```

### Response Behaviors

```python
def respond_to_activity(self, activity):
    """Trigger robot behaviors based on detected activity"""
    if activity == 'waving':
        self.approach_person()
        self.speak("Hello! How can I help you?")

    elif activity == 'fallen':
        self.send_alert("Person fallen detected!")
        self.approach_carefully()
        self.speak("Are you okay? I'm calling for help.")

    elif isinstance(activity, tuple) and activity[0] == 'pointing':
        direction = activity[1]['description']
        self.speak(f"Moving {direction}")
        self.move_in_direction(activity[1]['yaw'])

    elif activity == 'sitting':
        # Adjust camera angle for seated person
        pass
```

## Configuration Parameters

```yaml
pose_estimation:
  # MediaPipe settings
  model_complexity: 1  # 0=lite, 1=full, 2=heavy
  min_detection_confidence: 0.5
  min_tracking_confidence: 0.5

  # Activity detection
  motion_threshold: 0.3  # m/s for waving detection
  fallen_height_threshold: 0.5  # meters
  pointing_angle_threshold: 0.7  # cosine similarity

  # Behavior responses
  respond_to_waving: true
  respond_to_pointing: true
  alert_on_fallen: true
```

## Installation

```bash
# Install MediaPipe
pip3 install mediapipe

# Alternative: MoveNet (TensorFlow Lite)
pip3 install tensorflow-lite
```

## Performance

| Model | Task | FPS | Accuracy | Notes |
|-------|------|-----|----------|-------|
| MediaPipe Pose Lite | Pose estimation | 30+ | 85% | Fastest |
| MediaPipe Pose Full | Pose estimation | 15-25 | 95% | Recommended |
| MoveNet Thunder | Pose estimation | 10-15 | 97% | Most accurate |

---

[← Previous: Face Recognition](05-face-recognition.md) | [↑ Index](README.md) | [Next: Scene Narration →](07-scene-narration.md)
