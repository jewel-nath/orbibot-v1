# 8. Autonomous Security Patrol

**Difficulty:** Moderate
**Hardware Used:** RealSense D435, RPLidar A1, Raspberry Pi 5
**Prerequisites:** Features #1 (object detection), Nav2 navigation

## Description

Robot patrols predefined waypoints and detects anomalies (new objects, missing objects, or motion).

## Implementation

- Define patrol waypoints using Nav2's waypoint follower
- At each waypoint, capture images and compare with baseline using **image differencing** or **CLIP embeddings**
- Detect intruders/motion using background subtraction or YOLO person detection
- Send alerts (email, MQTT, or webhook) when anomalies are detected

## Why It Fits

Combines existing SLAM/navigation with computer vision for a practical home/office security application.

## Patrol Configuration

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

## Implementation

### Security Patrol Node

```python
import numpy as np
from nav2_simple_commander.robot_navigator import BasicNavigator
from geometry_msgs.msg import PoseStamped
import yaml

class SecurityPatrolNode(Node):
    def __init__(self):
        super().__init__('security_patrol')

        # Load patrol configuration
        config_path = self.get_parameter('config_path').value
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

        # Navigation
        self.navigator = BasicNavigator()

        # Vision processing
        self.detector = YOLOv8Detector()
        self.baseline_images = {}
        self.anomaly_detector = AnomalyDetector(self)

        # Alert system
        self.alerter = AlertSystem(self.config['alert_config'])

        # ROS setup
        self.bridge = CvBridge()
        self.image_sub = self.create_subscription(
            Image, '/camera/color/image_raw',
            self.image_callback, 10
        )

        # State
        self.current_waypoint = 0
        self.patrol_active = False
        self.latest_frame = None

        # Services
        self.start_patrol_srv = self.create_service(
            Trigger, '/start_patrol',
            self.start_patrol_callback
        )
        self.stop_patrol_srv = self.create_service(
            Trigger, '/stop_patrol',
            self.stop_patrol_callback
        )

    def image_callback(self, msg):
        self.latest_frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def start_patrol_callback(self, request, response):
        """Start security patrol"""
        if self.patrol_active:
            response.success = False
            response.message = "Patrol already active"
            return response

        self.patrol_active = True

        # Start patrol loop in separate thread
        import threading
        self.patrol_thread = threading.Thread(target=self.patrol_loop)
        self.patrol_thread.start()

        response.success = True
        response.message = "Security patrol started"
        return response

    def stop_patrol_callback(self, request, response):
        """Stop security patrol"""
        self.patrol_active = False
        self.navigator.cancelTask()

        response.success = True
        response.message = "Security patrol stopped"
        return response

    def patrol_loop(self):
        """Main patrol loop"""
        waypoints = self.config['patrol_waypoints']

        while self.patrol_active:
            for wp in waypoints:
                if not self.patrol_active:
                    break

                # Navigate to waypoint
                self.get_logger().info(f"Navigating to {wp['name']}")
                self.navigate_to_waypoint(wp)

                # Wait for arrival
                while not self.navigator.isTaskComplete():
                    time.sleep(0.1)

                # Perform security check
                self.perform_security_check(wp)

                # Wait before next waypoint
                time.sleep(wp.get('check_interval', 60))

    def navigate_to_waypoint(self, waypoint):
        """Navigate to specified waypoint"""
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.navigator.get_clock().now().to_msg()

        goal_pose.pose.position.x = waypoint['x']
        goal_pose.pose.position.y = waypoint['y']

        # Convert theta to quaternion
        from tf_transformations import quaternion_from_euler
        q = quaternion_from_euler(0, 0, waypoint['theta'])
        goal_pose.pose.orientation.x = q[0]
        goal_pose.pose.orientation.y = q[1]
        goal_pose.pose.orientation.z = q[2]
        goal_pose.pose.orientation.w = q[3]

        self.navigator.goToPose(goal_pose)

    def perform_security_check(self, waypoint):
        """Check for anomalies at waypoint"""
        wp_name = waypoint['name']

        # Capture current image
        current_image = self.latest_frame

        if current_image is None:
            self.get_logger().warn('No image available for security check')
            return

        # First visit - save baseline
        if wp_name not in self.baseline_images:
            self.baseline_images[wp_name] = current_image
            self.get_logger().info(f'Baseline image saved for {wp_name}')
            return

        # Compare with baseline
        anomalies = self.anomaly_detector.detect_anomalies(
            self.baseline_images[wp_name],
            current_image,
            waypoint
        )

        if anomalies:
            self.handle_anomalies(anomalies, waypoint)
```

### Anomaly Detection

```python
class AnomalyDetector:
    """Detect visual anomalies between baseline and current images"""

    def __init__(self, node):
        self.node = node

        # Initialize detectors
        self.person_detector = YOLO('yolov8n.pt')
        self.clip_model = self.load_clip_model()

        # Thresholds
        self.motion_threshold = 0.15
        self.object_threshold = 0.3

    def detect_anomalies(self, baseline_image, current_image, waypoint):
        """Compare images and detect anomalies"""
        anomalies = []

        # Method 1: Motion detection (background subtraction)
        motion_detected = self.detect_motion(baseline_image, current_image)
        if motion_detected:
            anomalies.append({
                'type': 'motion',
                'severity': 'high',
                'details': motion_detected
            })

        # Method 2: Person detection
        persons = self.detect_persons(current_image)
        if persons:
            anomalies.append({
                'type': 'person_detected',
                'severity': 'critical',
                'details': persons
            })

        # Method 3: Object appearance/disappearance
        object_changes = self.detect_object_changes(baseline_image, current_image)
        if object_changes:
            anomalies.append({
                'type': 'object_change',
                'severity': 'medium',
                'details': object_changes
            })

        return anomalies

    def detect_motion(self, baseline, current):
        """Detect motion using frame differencing"""
        # Convert to grayscale
        gray_baseline = cv2.cvtColor(baseline, cv2.COLOR_BGR2GRAY)
        gray_current = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)

        # Gaussian blur to reduce noise
        gray_baseline = cv2.GaussianBlur(gray_baseline, (21, 21), 0)
        gray_current = cv2.GaussianBlur(gray_current, (21, 21), 0)

        # Compute absolute difference
        frame_delta = cv2.absdiff(gray_baseline, gray_current)

        # Threshold
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]

        # Calculate percentage of changed pixels
        changed_ratio = np.sum(thresh > 0) / thresh.size

        if changed_ratio > self.motion_threshold:
            # Find contours of motion
            contours, _ = cv2.findContours(
                thresh.copy(),
                cv2.RETR_EXTERNAL,
                cv2.CHAIN_APPROX_SIMPLE
            )

            # Filter by area
            significant_contours = [
                c for c in contours
                if cv2.contourArea(c) > 500
            ]

            if significant_contours:
                return {
                    'changed_ratio': changed_ratio,
                    'num_regions': len(significant_contours),
                    'largest_area': max(cv2.contourArea(c) for c in significant_contours)
                }

        return None

    def detect_persons(self, image):
        """Detect people in image"""
        results = self.person_detector(image, classes=[0])  # class 0 = person

        persons = []
        for box in results[0].boxes:
            persons.append({
                'bbox': box.xyxy[0].cpu().numpy().tolist(),
                'confidence': float(box.conf[0])
            })

        return persons if persons else None

    def detect_object_changes(self, baseline, current):
        """Detect new/missing objects using object detection"""
        # Run detection on both images
        baseline_objects = self.detect_objects(baseline)
        current_objects = self.detect_objects(current)

        # Compare object sets
        baseline_classes = set(obj['class'] for obj in baseline_objects)
        current_classes = set(obj['class'] for obj in current_objects)

        new_objects = current_classes - baseline_classes
        missing_objects = baseline_classes - current_classes

        if new_objects or missing_objects:
            return {
                'new': list(new_objects),
                'missing': list(missing_objects)
            }

        return None

    def detect_objects(self, image):
        """Detect all objects in image"""
        results = self.person_detector(image)

        objects = []
        for box in results[0].boxes:
            objects.append({
                'class': results[0].names[int(box.cls[0])],
                'bbox': box.xyxy[0].cpu().numpy().tolist(),
                'confidence': float(box.conf[0])
            })

        return objects

    def load_clip_model(self):
        """Load CLIP for semantic comparison (optional)"""
        try:
            import clip
            model, preprocess = clip.load("ViT-B/32", device="cpu")
            return {'model': model, 'preprocess': preprocess}
        except:
            return None

    def compare_with_clip(self, baseline, current):
        """Use CLIP embeddings for semantic similarity"""
        if not self.clip_model:
            return None

        # Encode images
        baseline_features = self.encode_image(baseline)
        current_features = self.encode_image(current)

        # Calculate similarity
        similarity = (baseline_features @ current_features.T).item()

        return similarity
```

### Alert System

```python
class AlertSystem:
    """Send alerts when anomalies detected"""

    def __init__(self, config):
        self.config = config
        self.last_alert_time = {}
        self.cooldown = config.get('cooldown', 300)

        # Initialize alert methods
        self.methods = {
            'mqtt': MQTTAlerter(config.get('mqtt', {})),
            'email': EmailAlerter(config.get('email', {})),
            'webhook': WebhookAlerter(config.get('webhook', {}))
        }

    def send_alert(self, anomaly, waypoint):
        """Send alert through configured methods"""
        # Check cooldown
        key = f"{waypoint['name']}_{anomaly['type']}"
        now = time.time()

        if key in self.last_alert_time:
            if now - self.last_alert_time[key] < self.cooldown:
                return  # Skip - in cooldown period

        self.last_alert_time[key] = now

        # Format alert message
        message = self.format_alert_message(anomaly, waypoint)

        # Send through all configured methods
        for method_name in self.config.get('methods', []):
            if method_name in self.methods:
                try:
                    self.methods[method_name].send(message)
                except Exception as e:
                    print(f"Error sending alert via {method_name}: {e}")

    def format_alert_message(self, anomaly, waypoint):
        """Format alert message"""
        severity_emoji = {
            'low': '🔵',
            'medium': '🟡',
            'high': '🟠',
            'critical': '🔴'
        }

        emoji = severity_emoji.get(anomaly['severity'], '⚪')

        message = {
            'timestamp': time.time(),
            'waypoint': waypoint['name'],
            'anomaly_type': anomaly['type'],
            'severity': anomaly['severity'],
            'details': anomaly['details'],
            'text': f"{emoji} Security Alert: {anomaly['type']} detected at {waypoint['name']}"
        }

        return message

class MQTTAlerter:
    """Send alerts via MQTT"""

    def __init__(self, config):
        import paho.mqtt.client as mqtt

        self.client = mqtt.Client()
        self.client.connect(
            config.get('broker', 'localhost'),
            config.get('port', 1883)
        )
        self.topic = config.get('topic', 'orbibot/alerts')

    def send(self, message):
        import json
        self.client.publish(self.topic, json.dumps(message))

class EmailAlerter:
    """Send alerts via email"""

    def __init__(self, config):
        self.smtp_server = config.get('smtp_server')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.recipients = config.get('recipients', [])

    def send(self, message):
        import smtplib
        from email.mime.text import MIMEText

        msg = MIMEText(str(message['details']))
        msg['Subject'] = f"OrbiBot Security Alert: {message['anomaly_type']}"
        msg['From'] = self.username
        msg['To'] = ', '.join(self.recipients)

        with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)

class WebhookAlerter:
    """Send alerts via webhook"""

    def __init__(self, config):
        self.url = config.get('url')
        self.headers = config.get('headers', {})

    def send(self, message):
        import requests
        requests.post(self.url, json=message, headers=self.headers)
```

## Configuration File Example

```yaml
# security_patrol.yaml

patrol_waypoints:
  - name: "front_entrance"
    x: 2.0
    y: 0.5
    theta: 1.57
    check_interval: 60

  - name: "hallway"
    x: 5.0
    y: 2.0
    theta: 0.0
    check_interval: 90

  - name: "office"
    x: 7.5
    y: 4.0
    theta: -1.57
    check_interval: 120

  - name: "storage_room"
    x: 3.0
    y: 5.5
    theta: 3.14
    check_interval: 180

detection_config:
  motion_threshold: 0.15
  object_threshold: 0.3
  person_confidence: 0.7

alert_config:
  methods: ['mqtt', 'email']
  sensitivity: 0.8
  cooldown: 300

  mqtt:
    broker: "localhost"
    port: 1883
    topic: "orbibot/security/alerts"

  email:
    smtp_server: "smtp.gmail.com"
    smtp_port: 587
    username: "robot@example.com"
    password: "your-app-password"
    recipients: ["admin@example.com"]

  webhook:
    url: "https://your-server.com/webhook"
    headers:
      Authorization: "Bearer your-token"
```

## Launch File

```python
# security_patrol.launch.py

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
import os

def generate_launch_description():
    # Get config file
    config_file = os.path.join(
        get_package_share_directory('orbibot_ai'),
        'config',
        'security_patrol.yaml'
    )

    return LaunchDescription([
        # Include base system
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('orbibot_bringup'),
                '/launch/system.launch.py'
            ])
        ),

        # Include navigation
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                get_package_share_directory('orbibot_navigation'),
                '/launch/navigation.launch.py'
            ])
        ),

        # Security patrol node
        Node(
            package='orbibot_ai',
            executable='security_patrol',
            name='security_patrol',
            parameters=[config_file]
        ),
    ])
```

## Usage

```bash
# Launch security patrol system
ros2 launch orbibot_ai security_patrol.launch.py

# Start patrol
ros2 service call /start_patrol std_srvs/srv/Trigger

# Stop patrol
ros2 service call /stop_patrol std_srvs/srv/Trigger

# Update baseline images
ros2 service call /reset_baselines std_srvs/srv/Trigger
```

## Advanced Features

### Scheduled Patrols

```python
import schedule

def setup_scheduled_patrol():
    # Patrol every night from 10pm to 6am
    schedule.every().day.at("22:00").do(start_patrol)
    schedule.every().day.at("06:00").do(stop_patrol)

    while True:
        schedule.run_pending()
        time.sleep(60)
```

### Integration with Home Automation

```python
# Home Assistant integration via MQTT
def publish_to_home_assistant(anomaly):
    topic = "homeassistant/binary_sensor/orbibot_security/state"
    state = "ON" if anomaly else "OFF"
    mqtt_client.publish(topic, state)
```

---

[← Previous: Scene Narration](07-scene-narration.md) | [↑ Index](README.md) | [Next: Semantic Navigation →](09-semantic-navigation.md)
