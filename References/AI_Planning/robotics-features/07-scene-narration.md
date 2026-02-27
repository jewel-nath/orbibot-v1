# 7. Scene Narration (VLM-Powered)

**Difficulty:** Moderate/Hard
**Hardware Used:** RealSense D435 (RGB), Raspberry Pi 5
**Prerequisites:** Basic vision pipeline from earlier features

## Description

Robot describes its surroundings using a Vision-Language Model.

## Implementation

- Capture images from the RGB camera periodically or on request
- Run inference using **LLaVA**, **MiniGPT-4**, or cloud API (GPT-4V, Claude Vision)
- Generate natural language descriptions: "I see a wooden desk with a laptop, a coffee mug, and some books."
- Useful for accessibility (assisting visually impaired users) or inventory tasks

## Why It Fits

Transforms raw sensor data into human-understandable context.

## ROS 2 Integration

```python
# Node structure:
# Subscribes: /camera/color/image_raw
# Services: /describe_scene, /answer_visual_question
# Parameters: vlm_model, use_cloud_api, prompt_template
```

## Implementation

### Scene Narration Node

```python
import base64
import json
from PIL import Image
import io

class SceneNarrationNode(Node):
    def __init__(self):
        super().__init__('scene_narration')

        # Configuration
        self.declare_parameter('vlm_backend', 'cloud')  # 'local' or 'cloud'
        self.declare_parameter('model_name', 'gpt-4-vision-preview')
        self.declare_parameter('api_key', '')

        backend = self.get_parameter('vlm_backend').value

        # Initialize VLM backend
        if backend == 'local':
            self.vlm = LocalVLM(self)
        else:
            self.vlm = CloudVLM(self)

        # ROS setup
        self.bridge = CvBridge()
        self.image_sub = self.create_subscription(
            Image, '/camera/color/image_raw',
            self.image_callback, 10
        )

        # Services
        self.describe_srv = self.create_service(
            DescribeScene, '/describe_scene',
            self.describe_scene_callback
        )
        self.vqa_srv = self.create_service(
            VisualQuestion, '/answer_visual_question',
            self.visual_question_callback
        )

        # State
        self.latest_frame = None
        self.last_description = None

    def image_callback(self, msg):
        self.latest_frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')

    def describe_scene_callback(self, request, response):
        """Generate description of current scene"""
        if self.latest_frame is None:
            response.success = False
            response.description = "No image available"
            return response

        try:
            # Generate description
            prompt = request.prompt or "Describe what you see in this image in detail."
            description = self.vlm.generate_description(
                self.latest_frame,
                prompt
            )

            response.success = True
            response.description = description
            self.last_description = description

            # Optional: Convert to speech
            if self.get_parameter('enable_tts').value:
                self.speak(description)

        except Exception as e:
            response.success = False
            response.description = f"Error: {str(e)}"

        return response

    def visual_question_callback(self, request, response):
        """Answer question about current scene"""
        if self.latest_frame is None:
            response.success = False
            response.answer = "No image available"
            return response

        try:
            answer = self.vlm.answer_question(
                self.latest_frame,
                request.question
            )

            response.success = True
            response.answer = answer

        except Exception as e:
            response.success = False
            response.answer = f"Error: {str(e)}"

        return response
```

### Cloud VLM Backend (GPT-4V / Claude)

```python
import anthropic
import openai

class CloudVLM:
    """Use cloud APIs for vision-language tasks"""

    def __init__(self, node):
        self.node = node
        self.api_provider = node.get_parameter('api_provider').value
        self.api_key = node.get_parameter('api_key').value

        if self.api_provider == 'openai':
            self.client = openai.OpenAI(api_key=self.api_key)
        elif self.api_provider == 'anthropic':
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate_description(self, image, prompt):
        """Generate scene description"""
        # Encode image to base64
        image_b64 = self.encode_image(image)

        if self.api_provider == 'openai':
            return self.describe_with_openai(image_b64, prompt)
        elif self.api_provider == 'anthropic':
            return self.describe_with_claude(image_b64, prompt)

    def describe_with_openai(self, image_b64, prompt):
        """Use GPT-4 Vision"""
        response = self.client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )

        return response.choices[0].message.content

    def describe_with_claude(self, image_b64, prompt):
        """Use Claude Vision"""
        message = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )

        return message.content[0].text

    def encode_image(self, cv_image):
        """Convert OpenCV image to base64"""
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)

        # Encode to JPEG
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=85)
        image_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return image_b64

    def answer_question(self, image, question):
        """Answer visual question"""
        return self.generate_description(image, question)
```

### Local VLM Backend (LLaVA)

```python
from llava.model.builder import load_pretrained_model
from llava.mm_utils import get_model_name_from_path
from llava.eval.run_llava import eval_model

class LocalVLM:
    """Run VLM locally using LLaVA"""

    def __init__(self, node):
        self.node = node
        model_path = node.get_parameter('model_path').value

        # Load LLaVA model (quantized for Pi 5)
        self.node.get_logger().info('Loading LLaVA model...')
        self.tokenizer, self.model, self.image_processor, self.context_len = \
            load_pretrained_model(
                model_path=model_path,
                model_base=None,
                model_name=get_model_name_from_path(model_path),
                load_8bit=True,  # Quantization for Pi 5
                device='cpu'
            )

        self.node.get_logger().info('LLaVA model loaded')

    def generate_description(self, image, prompt):
        """Generate description using local model"""
        # Save temporary image
        temp_path = '/tmp/scene_image.jpg'
        cv2.imwrite(temp_path, image)

        # Run inference
        args = type('Args', (), {
            "model_path": self.model_path,
            "model_base": None,
            "model_name": get_model_name_from_path(self.model_path),
            "query": prompt,
            "conv_mode": None,
            "image_file": temp_path,
            "sep": ",",
            "temperature": 0.2,
            "top_p": None,
            "num_beams": 1,
            "max_new_tokens": 512
        })()

        response = eval_model(args)
        return response

    def answer_question(self, image, question):
        """Answer visual question"""
        return self.generate_description(image, question)
```

## Use Cases

### 1. Accessibility Assistant

```python
class AccessibilityAssistant:
    """Help visually impaired users navigate"""

    def describe_surroundings(self):
        """Periodic environment description"""
        description = self.vlm.generate_description(
            self.latest_frame,
            "Describe the room layout, obstacles, and objects in front of me."
        )
        self.speak(description)

    def identify_object(self, object_name):
        """Find specific object"""
        question = f"Do you see a {object_name}? If yes, describe its location."
        answer = self.vlm.answer_question(self.latest_frame, question)
        self.speak(answer)

    def read_text(self):
        """Read visible text"""
        text = self.vlm.answer_question(
            self.latest_frame,
            "Read any visible text in this image."
        )
        self.speak(text)
```

### 2. Inventory Management

```python
class InventoryManager:
    """Track objects and their locations"""

    def catalog_room(self):
        """Create inventory of visible objects"""
        description = self.vlm.generate_description(
            self.latest_frame,
            "List all objects you see with their approximate positions."
        )

        # Parse into structured data
        inventory = self.parse_inventory(description)
        return inventory

    def verify_item_present(self, item_name):
        """Check if item is visible"""
        answer = self.vlm.answer_question(
            self.latest_frame,
            f"Is there a {item_name} in this image? Answer yes or no."
        )
        return 'yes' in answer.lower()
```

### 3. Safety Monitoring

```python
class SafetyMonitor:
    """Detect safety hazards"""

    def check_hazards(self):
        """Identify potential safety issues"""
        hazards = self.vlm.answer_question(
            self.latest_frame,
            "Are there any safety hazards visible? List any spills, obstacles, or dangerous conditions."
        )

        if self.is_hazard_detected(hazards):
            self.send_alert(hazards)

    def verify_clear_path(self):
        """Check if path ahead is clear"""
        answer = self.vlm.answer_question(
            self.latest_frame,
            "Is the path ahead clear for a robot to navigate? Describe any obstacles."
        )
        return answer
```

## Prompt Templates

```python
PROMPT_TEMPLATES = {
    'general_description': "Describe what you see in this image in detail.",

    'navigation': "Describe the room layout and any obstacles in the path ahead.",

    'object_search': "List all {object_type} objects you can see and their approximate locations.",

    'safety_check': "Identify any safety hazards, spills, or dangerous conditions in this image.",

    'inventory': "Create a detailed inventory of all objects visible, organized by category.",

    'accessibility': "Describe this scene as if explaining it to a blind person, including spatial relationships.",

    'activity': "What activities or actions are happening in this image?",
}
```

## Configuration Parameters

```yaml
scene_narration:
  # Backend selection
  vlm_backend: 'cloud'  # 'local' or 'cloud'

  # Cloud API settings
  api_provider: 'anthropic'  # 'openai' or 'anthropic'
  api_key: 'your-api-key'
  model_name: 'claude-3-5-sonnet-20241022'

  # Local model settings
  model_path: '/home/pi/models/llava-v1.5-7b-q8'
  use_quantization: true

  # Generation parameters
  max_tokens: 300
  temperature: 0.2

  # Features
  enable_tts: true
  auto_describe_interval: 30  # seconds (0 = disabled)
  cache_descriptions: true
```

## Installation

### Cloud API Setup

```bash
# Install API clients
pip3 install openai anthropic
```

### Local LLaVA Setup

```bash
# Install dependencies
pip3 install transformers accelerate sentencepiece

# Clone LLaVA
cd ~
git clone https://github.com/haotian-liu/LLaVA.git
cd LLaVA
pip3 install -e .

# Download quantized model (smaller for Pi 5)
# Model: liuhaotian/llava-v1.5-7b
```

## Testing

```bash
# Test scene description
ros2 service call /describe_scene orbibot_msgs/srv/DescribeScene \
    "{prompt: 'Describe what you see'}"

# Test visual question
ros2 service call /answer_visual_question orbibot_msgs/srv/VisualQuestion \
    "{question: 'How many chairs are visible?'}"
```

## Performance Expectations

| Backend | Latency | Accuracy | Cost | Notes |
|---------|---------|----------|------|-------|
| GPT-4V | 2-5s | Excellent | $0.01/image | Best quality |
| Claude Vision | 2-4s | Excellent | $0.008/image | Good detail |
| LLaVA 7B (local) | 10-30s | Good | Free | Slow on Pi 5 |

**Recommendation:** Use cloud API for production, local model for offline/privacy-critical applications.

## Cost Optimization

```python
class CostOptimizer:
    """Reduce API costs"""

    def __init__(self):
        self.description_cache = {}
        self.min_interval = 5.0  # seconds
        self.last_request_time = 0

    def should_request(self, image_hash):
        """Rate limiting and caching"""
        now = time.time()

        # Check rate limit
        if now - self.last_request_time < self.min_interval:
            return False

        # Check cache
        if image_hash in self.description_cache:
            return False

        self.last_request_time = now
        return True
```

---

[← Previous: Pose Estimation](06-pose-estimation.md) | [↑ Index](README.md) | [Next: Security Patrol →](08-security-patrol.md)
