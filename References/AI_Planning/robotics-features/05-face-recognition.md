# 5. Face Recognition & Personalization

**Difficulty:** Moderate
**Hardware Used:** RealSense D435 (RGB), Raspberry Pi 5
**Prerequisites:** Feature #4 (vision processing pipeline)

## Description

Recognize known users and personalize robot behavior accordingly.

## Implementation

- Use **face_recognition** library or **InsightFace** for face detection and embedding
- Store face embeddings in a local database with associated user preferences
- Personalized behaviors:
    - Greet users by name
    - Adjust follow distance per user preference
    - Restrict certain commands to authorized users

## Why It Fits

Adds a personal touch and enables access control for sensitive operations.

## Database Schema

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

## Implementation

### Face Recognition Node

```python
import face_recognition
import pickle
import numpy as np
from pathlib import Path

class FaceRecognitionNode(Node):
    def __init__(self):
        super().__init__('face_recognition')

        # Load user database
        self.db_path = Path.home() / '.orbibot' / 'face_database.pkl'
        self.user_db = self.load_database()

        # ROS setup
        self.bridge = CvBridge()
        self.image_sub = self.create_subscription(
            Image, '/camera/color/image_raw',
            self.image_callback, 10
        )

        # Publishers
        self.user_detected_pub = self.create_publisher(
            String, '/user_detected', 10
        )

        # Services
        self.enroll_srv = self.create_service(
            EnrollUser, '/enroll_user',
            self.enroll_user_callback
        )

        # State
        self.current_user = None
        self.last_recognition_time = 0

    def image_callback(self, msg):
        # Convert to OpenCV
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        # Recognize each face
        for encoding in face_encodings:
            user = self.recognize_face(encoding)

            if user:
                self.handle_user_detection(user)

    def recognize_face(self, face_encoding):
        """
        Match face encoding against database
        Returns user_id if match found, else None
        """
        if not self.user_db:
            return None

        # Get all known encodings
        known_encodings = [u['face_embedding'] for u in self.user_db.values()]
        known_ids = list(self.user_db.keys())

        # Compare faces
        matches = face_recognition.compare_faces(
            known_encodings, face_encoding,
            tolerance=0.6  # Lower = stricter
        )

        # Calculate distances
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)

        if True in matches:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                return known_ids[best_match_index]

        return None
```

### User Enrollment

```python
def enroll_user_callback(self, request, response):
    """
    Service to enroll new user
    Request: name, access_level, preferences
    Response: success, user_id
    """
    try:
        # Capture face images
        face_encodings = self.capture_face_samples(num_samples=5)

        if not face_encodings:
            response.success = False
            response.message = "No face detected"
            return response

        # Average encodings for robustness
        avg_encoding = np.mean(face_encodings, axis=0)

        # Create user profile
        user_id = str(uuid.uuid4())
        self.user_db[user_id] = {
            'name': request.name,
            'face_embedding': avg_encoding,
            'preferences': {
                'follow_distance': request.follow_distance or 1.0,
                'greeting': request.greeting or f"Hello {request.name}",
                'access_level': request.access_level or 1,
            },
            'enrolled_at': time.time()
        }

        # Save database
        self.save_database()

        response.success = True
        response.user_id = user_id
        response.message = f"User {request.name} enrolled successfully"

        self.get_logger().info(f'Enrolled new user: {request.name}')

    except Exception as e:
        response.success = False
        response.message = str(e)

    return response

def capture_face_samples(self, num_samples=5):
    """Capture multiple face images for robust enrollment"""
    encodings = []

    for i in range(num_samples):
        # Capture frame
        frame = self.get_current_frame()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Detect face
        face_locations = face_recognition.face_locations(rgb_frame)

        if len(face_locations) == 1:
            face_encoding = face_recognition.face_encodings(rgb_frame, face_locations)[0]
            encodings.append(face_encoding)

            # Give user time to adjust pose
            time.sleep(0.5)
        else:
            self.get_logger().warn(f'Expected 1 face, found {len(face_locations)}')

    return encodings
```

### Personalization Engine

```python
class PersonalizationEngine:
    """Apply user-specific behaviors"""

    def __init__(self, node):
        self.node = node
        self.current_user = None

    def on_user_detected(self, user_id):
        """Called when user is recognized"""
        user = self.node.user_db.get(user_id)

        if not user:
            return

        self.current_user = user_id

        # Greet user
        self.greet_user(user)

        # Apply preferences
        self.apply_preferences(user['preferences'])

        # Log interaction
        self.log_user_interaction(user_id)

    def greet_user(self, user):
        """Greet user by name"""
        greeting = user['preferences']['greeting']

        # Publish to TTS
        self.node.speak(greeting)

        # Publish user detection event
        msg = String()
        msg.data = f"user_detected:{user['name']}"
        self.node.user_detected_pub.publish(msg)

    def apply_preferences(self, preferences):
        """Apply user-specific settings"""
        # Update follow distance
        if 'follow_distance' in preferences:
            self.node.set_parameter(
                'follow_distance',
                preferences['follow_distance']
            )

        # Update max speed based on user comfort
        if 'max_speed' in preferences:
            self.node.set_parameter(
                'max_speed',
                preferences['max_speed']
            )

    def check_access_level(self, required_level):
        """
        Check if current user has sufficient access
        """
        if not self.current_user:
            return False

        user = self.node.user_db[self.current_user]
        return user['preferences']['access_level'] >= required_level
```

### Access Control

```python
class SecureCommandHandler:
    """Restrict commands based on user access level"""

    ACCESS_LEVELS = {
        'GUEST': 0,
        'USER': 1,
        'ADMIN': 2,
    }

    COMMAND_REQUIREMENTS = {
        'move': ACCESS_LEVELS['GUEST'],
        'navigate': ACCESS_LEVELS['USER'],
        'map': ACCESS_LEVELS['USER'],
        'shutdown': ACCESS_LEVELS['ADMIN'],
        'update': ACCESS_LEVELS['ADMIN'],
    }

    def authorize_command(self, command, user_id):
        """Check if user authorized for command"""
        required_level = self.COMMAND_REQUIREMENTS.get(command, 999)

        if not user_id:
            # Unknown user - only allow guest commands
            return required_level <= self.ACCESS_LEVELS['GUEST']

        user = self.user_db.get(user_id)
        if not user:
            return False

        user_level = user['preferences']['access_level']

        if user_level >= required_level:
            self.log_authorized_command(user_id, command)
            return True
        else:
            self.log_unauthorized_attempt(user_id, command)
            self.speak(f"Sorry, you don't have permission for that")
            return False
```

## User Database Management

```python
def load_database(self):
    """Load user database from disk"""
    if self.db_path.exists():
        with open(self.db_path, 'rb') as f:
            return pickle.load(f)
    return {}

def save_database(self):
    """Save user database to disk"""
    self.db_path.parent.mkdir(parents=True, exist_ok=True)

    with open(self.db_path, 'wb') as f:
        pickle.dump(self.user_db, f)

def backup_database(self):
    """Create timestamped backup"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = self.db_path.parent / f'face_database_backup_{timestamp}.pkl'

    import shutil
    shutil.copy(self.db_path, backup_path)

    self.get_logger().info(f'Database backed up to {backup_path}')
```

## Advanced Features

### Multi-Face Tracking

```python
def track_multiple_users(self, face_locations, face_encodings):
    """Track multiple recognized users in scene"""
    recognized_users = []

    for location, encoding in zip(face_locations, face_encodings):
        user_id = self.recognize_face(encoding)

        if user_id:
            user = self.user_db[user_id]
            recognized_users.append({
                'user_id': user_id,
                'name': user['name'],
                'location': location,  # (top, right, bottom, left)
                'center': self.calculate_face_center(location)
            })

    return recognized_users
```

### User Re-identification

```python
def track_user_across_frames(self):
    """Maintain user identity even if temporarily not visible"""
    # Simple tracking using position prediction
    if self.current_user and time.time() - self.last_recognition_time < 3.0:
        # User likely still in scene
        return self.current_user
    else:
        # User lost
        self.current_user = None
        return None
```

## Configuration Parameters

```yaml
face_recognition:
  # Detection settings
  detection_method: 'hog'  # 'hog' or 'cnn' (faster vs more accurate)
  upsampling: 1  # Higher = better quality, slower

  # Recognition settings
  tolerance: 0.6  # Lower = stricter matching
  num_enrollment_samples: 5

  # Database
  database_path: '~/.orbibot/face_database.pkl'
  auto_backup: true
  backup_interval: 86400  # seconds (daily)

  # Personalization
  greeting_enabled: true
  auto_apply_preferences: true

  # Security
  require_authorization: true
  session_timeout: 300  # seconds
```

## Installation

```bash
# Install face_recognition
pip3 install face_recognition

# Alternative: InsightFace (faster, more accurate)
pip3 install insightface onnxruntime
```

## Usage

### Enroll New User

```bash
# Via service call
ros2 service call /enroll_user orbibot_msgs/srv/EnrollUser \
    "{name: 'Alice', access_level: 2, follow_distance: 1.5}"

# Via CLI tool
ros2 run orbibot_ai enroll_user_cli --name Alice --access-level 2
```

### List Users

```bash
ros2 service call /list_users std_srvs/srv/Trigger
```

### Remove User

```bash
ros2 service call /remove_user orbibot_msgs/srv/RemoveUser \
    "{user_id: 'uuid-here'}"
```

## Privacy Considerations

- Face embeddings stored locally (not images)
- Database encrypted at rest (optional)
- User can request data deletion
- No cloud uploads unless explicitly configured

## Performance

| Library | Speed | Accuracy | Memory | Notes |
|---------|-------|----------|--------|-------|
| face_recognition | 2-3 FPS | 95% | 200MB | Easy to use |
| InsightFace | 10-15 FPS | 98% | 300MB | Production ready |

---

[← Previous: Gesture Control](04-gesture-control.md) | [↑ Index](README.md) | [Next: Pose Estimation →](06-pose-estimation.md)
