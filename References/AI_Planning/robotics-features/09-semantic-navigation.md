# 9. Semantic Navigation (LLM + VLM Integration)

**Difficulty:** Hard (Advanced)
**Hardware Used:** Raspberry Pi 5 (running local SLM or API calls), RealSense/Lidar
**Prerequisites:** Features #3 (voice commands), #7 (VLM), Nav2 SLAM

## Description

Give the robot natural language commands like "Go to the kitchen" or "Find the red cup".

## Implementation

- **Visual SLAM / Semantic Mapping:** As the robot maps (using slam_toolbox), use the camera to identify objects (chairs, tables, doors) and save their coordinates in a semantic database
- **LLM/NLP Interface:** Use a lightweight LLM (e.g., Llama-3-8B quantized or Gemma) or cloud API to parse user text/voice into ROS 2 navigation goals

## Why It Fits

Moves the robot from "Geometry-aware" (knowing where walls are) to "Context-aware" (knowing what rooms/objects are).

## Semantic Database Schema

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

## Implementation

### Semantic Mapping Node

```python
import json
from pathlib import Path
import numpy as np

class SemanticMappingNode(Node):
    def __init__(self):
        super().__init__('semantic_mapping')

        # Load/create semantic map
        self.map_path = Path.home() / '.orbibot' / 'semantic_map.json'
        self.semantic_map = self.load_semantic_map()

        # Vision components
        self.object_detector = YOLO('yolov8n.pt')
        self.vlm = VLMInterface(self)  # From feature #7

        # ROS setup
        self.bridge = CvBridge()
        self.image_sub = self.create_subscription(
            Image, '/camera/color/image_raw',
            self.image_callback, 10
        )
        self.odom_sub = self.create_subscription(
            Odometry, '/odom',
            self.odom_callback, 10
        )
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer, self)

        # Services
        self.annotate_srv = self.create_service(
            AnnotateLocation, '/annotate_location',
            self.annotate_location_callback
        )
        self.query_srv = self.create_service(
            QueryLocation, '/query_location',
            self.query_location_callback
        )

        # State
        self.current_position = None
        self.latest_frame = None

        # Periodic semantic scan
        self.create_timer(10.0, self.semantic_scan_callback)

    def semantic_scan_callback(self):
        """Periodically scan and annotate surroundings"""
        if self.latest_frame is None or self.current_position is None:
            return

        # Detect objects in current view
        detections = self.detect_objects(self.latest_frame)

        # Add to semantic map
        for detection in detections:
            self.add_object_to_map(detection)

    def detect_objects(self, image):
        """Detect and localize objects in 3D"""
        results = self.object_detector(image)

        detections = []
        for box in results[0].boxes:
            # Get 2D position
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2

            # Get 3D position using depth
            position_3d = self.pixel_to_map_frame(cx, cy)

            if position_3d:
                detections.append({
                    'class': results[0].names[int(box.cls[0])],
                    'position': position_3d,
                    'confidence': float(box.conf[0]),
                    'bbox': [x1, y1, x2, y2]
                })

        return detections

    def pixel_to_map_frame(self, x_px, y_px):
        """Convert pixel coordinates to map frame"""
        # Get depth at pixel
        # (Implementation depends on depth camera integration)

        # Transform from camera frame to map frame using TF
        try:
            transform = self.tf_buffer.lookup_transform(
                'map',
                'camera_link',
                rclpy.time.Time()
            )

            # Apply transform to get map coordinates
            # (Full implementation omitted for brevity)

            return (map_x, map_y, map_z)

        except Exception as e:
            self.get_logger().warn(f'Transform failed: {e}')
            return None

    def add_object_to_map(self, detection):
        """Add or update object in semantic map"""
        # Check if object already exists nearby
        existing = self.find_nearby_object(
            detection['position'],
            detection['class'],
            radius=0.5
        )

        if existing:
            # Update existing object
            existing['last_seen'] = time.time()
            existing['confidence'] = max(existing['confidence'], detection['confidence'])
        else:
            # Add new object
            obj_id = f"obj_{len(self.semantic_map['objects']):04d}"
            self.semantic_map['objects'].append({
                'id': obj_id,
                'class': detection['class'],
                'position': detection['position'],
                'confidence': detection['confidence'],
                'first_seen': time.time(),
                'last_seen': time.time()
            })

            self.get_logger().info(f"Added {detection['class']} at {detection['position']}")

        # Save map
        self.save_semantic_map()

    def find_nearby_object(self, position, object_class, radius=0.5):
        """Find object of same class within radius"""
        for obj in self.semantic_map['objects']:
            if obj['class'] != object_class:
                continue

            dist = np.linalg.norm(np.array(obj['position']) - np.array(position))
            if dist < radius:
                return obj

        return None

    def annotate_location_callback(self, request, response):
        """Manually annotate current location"""
        location = {
            'id': f"loc_{len(self.semantic_map['locations']):04d}",
            'type': request.location_type,
            'name': request.name,
            'center': self.current_position,
            'annotated_at': time.time()
        }

        # Optional: Get room description from VLM
        if request.auto_describe:
            description = self.vlm.generate_description(
                self.latest_frame,
                f"Describe this {request.location_type} in 1-2 sentences."
            )
            location['description'] = description

        self.semantic_map['locations'].append(location)
        self.save_semantic_map()

        response.success = True
        response.location_id = location['id']
        return response
```

### Natural Language Navigation

```python
class SemanticNavigationNode(Node):
    """Navigate using natural language commands"""

    def __init__(self):
        super().__init__('semantic_navigation')

        # Load semantic map
        self.semantic_map = self.load_semantic_map()

        # LLM interface
        self.llm = LLMInterface(self)

        # Navigation
        self.navigator = BasicNavigator()

        # Services
        self.nav_srv = self.create_service(
            NavigateToDescription, '/navigate_to_description',
            self.navigate_to_description_callback
        )

    def navigate_to_description_callback(self, request, response):
        """Navigate based on natural language description"""
        description = request.description

        # Parse command with LLM
        navigation_plan = self.parse_navigation_command(description)

        if not navigation_plan:
            response.success = False
            response.message = "Could not understand navigation command"
            return response

        # Execute navigation
        success = self.execute_navigation(navigation_plan)

        response.success = success
        response.message = f"Navigating to {navigation_plan['target']}"
        return response

    def parse_navigation_command(self, description):
        """Use LLM to parse natural language command"""
        # Prepare semantic map context
        context = self.format_semantic_context()

        # LLM prompt
        prompt = f"""You are a robot navigation assistant. Given the semantic map and user command, determine the navigation target.

Semantic Map:
{context}

User Command: "{description}"

Respond with JSON:
{{
    "target_type": "location" or "object",
    "target_name": "name of location/object",
    "target_position": [x, y] coordinates,
    "confidence": 0.0-1.0
}}
"""

        # Query LLM
        response = self.llm.query(prompt)

        try:
            plan = json.loads(response)
            return plan
        except:
            self.get_logger().error('Failed to parse LLM response')
            return None

    def format_semantic_context(self):
        """Format semantic map for LLM context"""
        locations_str = "\n".join([
            f"- {loc['name']} ({loc['type']}) at ({loc['center'][0]:.2f}, {loc['center'][1]:.2f})"
            for loc in self.semantic_map['locations']
        ])

        objects_str = "\n".join([
            f"- {obj['class']} at ({obj['position'][0]:.2f}, {obj['position'][1]:.2f})"
            for obj in self.semantic_map['objects'][:20]  # Limit to avoid token limits
        ])

        return f"Locations:\n{locations_str}\n\nObjects:\n{objects_str}"

    def execute_navigation(self, plan):
        """Execute navigation to target"""
        target_pos = plan['target_position']

        # Create navigation goal
        goal_pose = PoseStamped()
        goal_pose.header.frame_id = 'map'
        goal_pose.header.stamp = self.navigator.get_clock().now().to_msg()
        goal_pose.pose.position.x = target_pos[0]
        goal_pose.pose.position.y = target_pos[1]
        goal_pose.pose.orientation.w = 1.0

        self.navigator.goToPose(goal_pose)

        return True
```

### LLM Interface

```python
class LLMInterface:
    """Interface to LLM (local or cloud)"""

    def __init__(self, node):
        self.node = node
        backend = node.get_parameter('llm_backend').value

        if backend == 'local':
            self.backend = LocalLLM(node)
        else:
            self.backend = CloudLLM(node)

    def query(self, prompt):
        """Query LLM with prompt"""
        return self.backend.generate(prompt)

class LocalLLM:
    """Local LLM using llama.cpp or transformers"""

    def __init__(self, node):
        from llama_cpp import Llama

        model_path = node.get_parameter('model_path').value
        self.llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=4
        )

    def generate(self, prompt):
        output = self.llm(
            prompt,
            max_tokens=256,
            temperature=0.2,
            stop=["```"]
        )
        return output['choices'][0]['text']

class CloudLLM:
    """Cloud LLM (OpenAI, Anthropic, etc.)"""

    def __init__(self, node):
        import anthropic

        api_key = node.get_parameter('api_key').value
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(self, prompt):
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=256,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
```

## Advanced Features

### Multi-Step Navigation

```python
def navigate_to_description_multi_step(self, description):
    """Handle complex multi-step navigation"""
    # Example: "Go to the kitchen, then find the red cup"

    # Parse into steps
    steps = self.llm.parse_multi_step_command(description)

    for i, step in enumerate(steps):
        self.get_logger().info(f"Step {i+1}: {step['action']}")

        if step['type'] == 'navigate':
            self.navigate_to(step['target'])
        elif step['type'] == 'search':
            self.search_for_object(step['object'])

        # Wait for completion
        self.wait_for_task_complete()
```

### Spatial Reasoning

```python
def resolve_spatial_reference(self, description):
    """Resolve spatial references like 'near the door', 'left of the table'"""
    # Example: "Go to the chair near the window"

    prompt = f"""
Given:
- Semantic map: {self.format_semantic_context()}
- Command: "{description}"

Identify the most likely target location using spatial reasoning.
Return JSON with target coordinates.
"""

    response = self.llm.query(prompt)
    return json.loads(response)
```

### Room Discovery

```python
def discover_and_label_rooms(self):
    """Automatically discover and label rooms during mapping"""
    # Segment map into rooms based on geometry
    rooms = self.segment_map_into_rooms()

    for room in rooms:
        # Navigate to room center
        self.navigate_to(room['center'])

        # Capture image and describe with VLM
        description = self.vlm.generate_description(
            self.latest_frame,
            "What type of room is this? (kitchen, bedroom, bathroom, etc.) Answer in 1-2 words."
        )

        # Add to semantic map
        self.add_location(
            name=description.lower(),
            type='room',
            bounds=room['bounds']
        )
```

## Configuration

```yaml
semantic_navigation:
  # LLM backend
  llm_backend: 'cloud'  # 'local' or 'cloud'
  api_provider: 'anthropic'
  api_key: 'your-api-key'
  model_path: '/home/pi/models/llama-3-8b.gguf'

  # Semantic mapping
  object_detection_interval: 10.0  # seconds
  min_object_confidence: 0.6
  object_merge_radius: 0.5  # meters

  # Navigation
  arrival_tolerance: 0.3  # meters
  enable_replanning: true
```

## Usage

```bash
# Start semantic navigation system
ros2 launch orbibot_ai semantic_navigation.launch.py

# Navigate using natural language
ros2 service call /navigate_to_description orbibot_msgs/srv/NavigateToDescription \
    "{description: 'Go to the kitchen'}"

# Annotate current location
ros2 service call /annotate_location orbibot_msgs/srv/AnnotateLocation \
    "{name: 'living room', location_type: 'room', auto_describe: true}"

# Query semantic map
ros2 service call /query_location orbibot_msgs/srv/QueryLocation \
    "{query: 'Where is the red chair?'}"
```

## Example Commands

| Command | Interpretation | Action |
|---------|---------------|---------|
| "Go to the kitchen" | Navigate to room named 'kitchen' | Navigate to kitchen center |
| "Find the red cup" | Search for object | Search all rooms, navigate to cup |
| "Go near the door" | Spatial reference | Navigate to position near door object |
| "Take me to the charging station" | Navigate to specific location | Navigate to annotated charging location |

---

[← Previous: Security Patrol](08-security-patrol.md) | [↑ Index](README.md) | [Next: Object Retrieval →](10-object-retrieval.md)
