# 10. Autonomous Object Retrieval

**Difficulty:** Hard
**Hardware Used:** RealSense D435, RPLidar A1, Raspberry Pi 5, (optional: robot arm)
**Prerequisites:** Features #1, #9 (semantic navigation)

## Description

Given a command like "bring me the red cup", the robot finds and retrieves the object.

## Implementation

- Use YOLO or CLIP for object detection and identification
- Navigate to the object using semantic map data
- If equipped with a gripper/arm, perform pick-and-place
- Without arm: Navigate to object and notify user of location

## Why It Fits

The ultimate test combining perception, navigation, and manipulation.

## Task Pipeline

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

## Implementation

### Object Retrieval Node

```python
from enum import Enum
import asyncio

class RetrievalState(Enum):
    IDLE = 0
    PARSING_COMMAND = 1
    SEARCHING_MAP = 2
    SEARCHING_ROOMS = 3
    NAVIGATING = 4
    VERIFYING = 5
    APPROACHING = 6
    GRASPING = 7
    RETURNING = 8
    PLACING = 9
    COMPLETE = 10
    FAILED = 11

class ObjectRetrievalNode(Node):
    def __init__(self):
        super().__init__('object_retrieval')

        # Components
        self.semantic_nav = SemanticNavigationNode()
        self.object_detector = ObjectDetector(self)
        self.llm = LLMInterface(self)
        self.vlm = VLMInterface(self)

        # Manipulation (if available)
        self.has_arm = self.get_parameter('has_arm').value
        if self.has_arm:
            self.arm_controller = ArmController(self)

        # Services
        self.retrieve_srv = self.create_service(
            RetrieveObject, '/retrieve_object',
            self.retrieve_object_callback
        )

        # State
        self.state = RetrievalState.IDLE
        self.current_task = None

    def retrieve_object_callback(self, request, response):
        """Service call to retrieve object"""
        description = request.object_description

        # Start retrieval task
        task_id = self.start_retrieval_task(description)

        response.success = True
        response.task_id = task_id
        response.message = f"Started retrieval task for: {description}"

        return response

    def start_retrieval_task(self, description):
        """Start asynchronous retrieval task"""
        task_id = str(uuid.uuid4())

        # Run in separate thread
        import threading
        thread = threading.Thread(
            target=self.execute_retrieval,
            args=(task_id, description)
        )
        thread.start()

        return task_id

    def execute_retrieval(self, task_id, description):
        """Main retrieval pipeline"""
        self.get_logger().info(f"Starting retrieval: {description}")

        try:
            # Step 1: Parse command
            self.state = RetrievalState.PARSING_COMMAND
            object_query = self.parse_object_description(description)

            # Step 2: Search semantic map
            self.state = RetrievalState.SEARCHING_MAP
            location = self.search_semantic_map(object_query)

            # Step 3: If not found, search rooms
            if not location:
                self.state = RetrievalState.SEARCHING_ROOMS
                location = self.search_for_object(object_query)

            if not location:
                self.state = RetrievalState.FAILED
                self.notify_user(f"Could not find {description}")
                return

            # Step 4: Navigate to object
            self.state = RetrievalState.NAVIGATING
            self.navigate_to(location)

            # Step 5: Visual verification and localization
            self.state = RetrievalState.VERIFYING
            object_pose = self.verify_and_localize(object_query)

            if not object_pose:
                self.state = RetrievalState.FAILED
                self.notify_user(f"Found location but could not see {description}")
                return

            # Step 6: Approach object precisely
            self.state = RetrievalState.APPROACHING
            self.approach_object(object_pose)

            # Step 7: Grasp (if arm available)
            if self.has_arm:
                self.state = RetrievalState.GRASPING
                success = self.grasp_object(object_pose)

                if success:
                    # Return to user
                    self.state = RetrievalState.RETURNING
                    self.return_to_user()

                    # Place object
                    self.state = RetrievalState.PLACING
                    self.place_object()
                else:
                    self.state = RetrievalState.FAILED
                    self.notify_user(f"Failed to grasp {description}")
                    return
            else:
                # No arm - just notify
                self.notify_user(f"Found {description} at current location")

            self.state = RetrievalState.COMPLETE
            self.get_logger().info(f"Retrieval complete: {description}")

        except Exception as e:
            self.state = RetrievalState.FAILED
            self.get_logger().error(f"Retrieval failed: {e}")
            self.notify_user(f"Retrieval failed: {str(e)}")

    def parse_object_description(self, description):
        """Parse natural language object description"""
        prompt = f"""Parse this object retrieval request into structured data:

Request: "{description}"

Return JSON:
{{
    "object_class": "general category (cup, book, etc.)",
    "attributes": {{
        "color": "red/blue/etc or null",
        "size": "large/small/etc or null",
        "material": "wooden/plastic/etc or null"
    }},
    "location_hint": "specific location mentioned or null"
}}
"""

        response = self.llm.query(prompt)
        return json.loads(response)

    def search_semantic_map(self, object_query):
        """Search semantic map for object"""
        semantic_map = self.load_semantic_map()

        # Filter objects by class
        candidates = [
            obj for obj in semantic_map['objects']
            if obj['class'] == object_query['object_class']
        ]

        # Filter by attributes
        if object_query['attributes'].get('color'):
            # Use VLM to verify color
            candidates = [
                obj for obj in candidates
                if self.verify_attribute(obj, 'color', object_query['attributes']['color'])
            ]

        if candidates:
            # Return closest or most recently seen
            return candidates[0]['position']

        return None

    def search_for_object(self, object_query):
        """Search rooms for object"""
        semantic_map = self.load_semantic_map()

        # Get all room locations
        rooms = [loc for loc in semantic_map['locations'] if loc['type'] == 'room']

        for room in rooms:
            self.get_logger().info(f"Searching {room['name']}...")

            # Navigate to room
            self.navigate_to(room['center'])

            # Scan for object
            found = self.scan_for_object(object_query)

            if found:
                return found

        return None

    def scan_for_object(self, object_query):
        """Scan current view for object"""
        # Rotate 360 degrees and scan
        for angle in range(0, 360, 45):
            # Rotate
            self.rotate_to_angle(angle)

            # Capture image
            image = self.get_current_image()

            # Detect objects
            detections = self.object_detector.detect(image)

            # Check for match
            for det in detections:
                if self.matches_query(det, object_query):
                    return det['position']

        return None

    def verify_and_localize(self, object_query):
        """Verify object and get precise 3D pose"""
        image = self.get_current_image()

        # Detect objects
        detections = self.object_detector.detect(image)

        # Find matching object
        for det in detections:
            if self.matches_query(det, object_query):
                # Get 3D pose
                pose = self.estimate_object_pose(det)
                return pose

        return None

    def matches_query(self, detection, query):
        """Check if detection matches query"""
        # Class match
        if detection['class'] != query['object_class']:
            return False

        # Attribute matching using VLM
        if query['attributes'].get('color'):
            if not self.verify_attribute(detection, 'color', query['attributes']['color']):
                return False

        return True

    def verify_attribute(self, detection, attribute, expected_value):
        """Verify object attribute using VLM"""
        # Crop object from image
        image = self.get_current_image()
        bbox = detection['bbox']
        cropped = image[int(bbox[1]):int(bbox[3]), int(bbox[0]):int(bbox[2])]

        # Ask VLM
        question = f"What {attribute} is this object? Answer with a single word."
        answer = self.vlm.answer_question(cropped, question)

        return expected_value.lower() in answer.lower()

    def approach_object(self, object_pose):
        """Navigate close to object for grasping"""
        # Calculate approach position (offset from object)
        approach_x = object_pose['x'] - 0.3  # 30cm in front
        approach_y = object_pose['y']

        # Navigate to approach position
        self.navigate_to([approach_x, approach_y])

        # Rotate to face object
        angle_to_object = np.arctan2(
            object_pose['y'] - approach_y,
            object_pose['x'] - approach_x
        )
        self.rotate_to_angle(angle_to_object)

    def grasp_object(self, object_pose):
        """Grasp object with robot arm"""
        if not self.has_arm:
            return False

        # Move arm to pre-grasp position
        self.arm_controller.move_to_pre_grasp(object_pose)

        # Open gripper
        self.arm_controller.open_gripper()

        # Move to grasp position
        self.arm_controller.move_to_grasp(object_pose)

        # Close gripper
        self.arm_controller.close_gripper()

        # Verify grasp
        grasp_success = self.arm_controller.verify_grasp()

        if grasp_success:
            # Lift object
            self.arm_controller.lift_object()

        return grasp_success

    def return_to_user(self):
        """Navigate back to user"""
        # Get user location (from face detection or preset)
        user_location = self.get_user_location()

        if user_location:
            self.navigate_to(user_location)
        else:
            # Return to home position
            self.navigate_to([0, 0])

    def place_object(self):
        """Place object for user"""
        if not self.has_arm:
            return

        # Move to placement position
        self.arm_controller.move_to_placement()

        # Open gripper
        self.arm_controller.open_gripper()

        # Retract arm
        self.arm_controller.retract()
```

### Object Detection with CLIP

```python
import clip
import torch

class CLIPObjectDetector:
    """Use CLIP for zero-shot object detection"""

    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, self.preprocess = clip.load("ViT-B/32", device=self.device)

    def find_object(self, image, text_query):
        """Find object matching text description"""
        # Get region proposals (using selective search or YOLO)
        proposals = self.get_region_proposals(image)

        # Encode text query
        text = clip.tokenize([text_query]).to(self.device)
        text_features = self.model.encode_text(text)

        best_match = None
        best_score = 0

        for proposal in proposals:
            # Crop region
            crop = self.crop_region(image, proposal['bbox'])

            # Encode image
            image_input = self.preprocess(crop).unsqueeze(0).to(self.device)
            image_features = self.model.encode_image(image_input)

            # Calculate similarity
            similarity = (image_features @ text_features.T).item()

            if similarity > best_score:
                best_score = similarity
                best_match = proposal

        return best_match if best_score > 0.3 else None
```

### Arm Controller (Optional)

```python
class ArmController:
    """Control robot arm for manipulation"""

    def __init__(self, node):
        self.node = node

        # Initialize arm interface (depends on arm hardware)
        # Example: MoveIt 2 or direct servo control

    def move_to_pre_grasp(self, object_pose):
        """Move arm to pre-grasp position above object"""
        target = object_pose.copy()
        target['z'] += 0.1  # 10cm above object

        self.move_to_pose(target)

    def move_to_grasp(self, object_pose):
        """Move arm to grasp position"""
        self.move_to_pose(object_pose)

    def open_gripper(self):
        """Open gripper"""
        self.set_gripper_position(1.0)  # Fully open

    def close_gripper(self):
        """Close gripper"""
        self.set_gripper_position(0.0)  # Fully closed

    def verify_grasp(self):
        """Check if object is grasped"""
        # Check gripper force/position sensors
        gripper_state = self.get_gripper_state()

        return gripper_state['has_object']

    def lift_object(self):
        """Lift grasped object"""
        current_pose = self.get_current_pose()
        current_pose['z'] += 0.15  # Lift 15cm

        self.move_to_pose(current_pose)
```

## Configuration

```yaml
object_retrieval:
  # Detection
  object_detector: 'yolo'  # 'yolo' or 'clip'
  detection_confidence: 0.7

  # Manipulation
  has_arm: false
  grasp_timeout: 10.0  # seconds
  max_grasp_attempts: 3

  # Navigation
  approach_distance: 0.3  # meters from object
  search_rotation_step: 45  # degrees

  # User interaction
  notify_method: 'tts'  # 'tts' or 'publish'
```

## Usage

```bash
# Start object retrieval system
ros2 launch orbibot_ai object_retrieval.launch.py

# Retrieve object
ros2 service call /retrieve_object orbibot_msgs/srv/RetrieveObject \
    "{object_description: 'the red cup'}"

# Check task status
ros2 topic echo /retrieval_status
```

## Example Scenarios

### Without Arm (Finder Mode)

```
User: "Find the TV remote"
Robot: [Searches semantic map, not found]
Robot: [Searches living room, bedroom]
Robot: [Detects remote in bedroom]
Robot: "I found the TV remote in the bedroom on the nightstand"
```

### With Arm (Full Retrieval)

```
User: "Bring me the blue book"
Robot: [Searches semantic map, found in study]
Robot: [Navigates to study]
Robot: [Verifies blue book visually]
Robot: [Approaches and grasps book]
Robot: [Returns to user]
Robot: [Places book in front of user]
Robot: "Here is the blue book"
```

## Advanced Features

### Multi-Object Retrieval

```python
def retrieve_multiple_objects(self, object_list):
    """Retrieve multiple objects in optimal order"""
    # Plan optimal route visiting all objects
    route = self.plan_optimal_route(object_list)

    for obj in route:
        self.retrieve_object(obj)
```

### Object Handoff

```python
def handoff_to_person(self, object_pose):
    """Hand object directly to person"""
    # Detect person
    person_pose = self.detect_person()

    # Extend arm toward person
    self.arm_controller.extend_to_person(person_pose)

    # Wait for person to take object
    self.wait_for_object_taken()

    # Open gripper
    self.arm_controller.open_gripper()
```

---

[← Previous: Semantic Navigation](09-semantic-navigation.md) | [↑ Index](README.md) | [Roadmap →](roadmap.md)
