# 3. Voice Command Interface

**Difficulty:** Easy/Moderate
**Hardware Used:** USB Microphone, Raspberry Pi 5
**Prerequisites:** None (foundational feature)

## Description

Control the robot using natural voice commands like "move forward", "stop", "turn around", or "go to the kitchen".

## Implementation

- Use **Whisper** (OpenAI's speech-to-text, runs locally on Pi 5) or **Vosk** for offline recognition
- Parse commands into intents and map to ROS 2 actions:
    - Navigation goals (`/navigate_to_pose`)
    - Direct velocity commands (`/cmd_vel`)
    - System commands (start mapping, save map, etc.)
- Optional: Add text-to-speech feedback using **Piper** or **espeak**

## Why It Fits

Hands-free operation is intuitive and works great with semantic navigation.

## ROS 2 Integration

```python
# Node structure:
# Subscribes: Audio input stream
# Publishes: /cmd_vel, /voice_command_text
# Action clients: NavigateToPose
# Parameters: wake_word, language_model, confidence_threshold
```

## Implementation Options

### Option 1: Whisper (High Accuracy, More Resource-Intensive)

```python
import whisper
import pyaudio
import numpy as np

class WhisperVoiceNode(Node):
    def __init__(self):
        super().__init__('whisper_voice_node')

        # Load Whisper model
        self.model = whisper.load_model("tiny")  # tiny, base, small, medium, large

        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=1024
        )

        # Command publisher
        self.cmd_pub = self.create_publisher(String, '/voice_command_text', 10)
        self.vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)

    def listen_and_transcribe(self):
        """Capture audio and transcribe"""
        audio_data = self.capture_audio(duration=3.0)
        result = self.model.transcribe(audio_data)
        text = result["text"].lower()
        return text

    def capture_audio(self, duration):
        """Record audio for specified duration"""
        frames = []
        for _ in range(0, int(16000 / 1024 * duration)):
            data = self.stream.read(1024)
            frames.append(data)

        audio_np = np.frombuffer(b''.join(frames), dtype=np.int16).astype(np.float32) / 32768.0
        return audio_np
```

### Option 2: Vosk (Lightweight, Fast, Offline)

```python
from vosk import Model, KaldiRecognizer
import json

class VoskVoiceNode(Node):
    def __init__(self):
        super().__init__('vosk_voice_node')

        # Load Vosk model
        model_path = "/path/to/vosk-model-small-en-us-0.15"
        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)

        # Audio setup
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4096
        )

    def listen_continuous(self):
        """Continuously listen and recognize"""
        while True:
            data = self.stream.read(4096, exception_on_overflow=False)

            if self.recognizer.AcceptWaveform(data):
                result = json.loads(self.recognizer.Result())
                text = result.get('text', '')
                if text:
                    self.process_command(text)
            else:
                # Partial result
                partial = json.loads(self.recognizer.PartialResult())
```

## Command Intent Parsing

```python
class CommandParser:
    """Parse natural language commands into robot actions"""

    MOTION_COMMANDS = {
        'move forward': {'linear.x': 0.3},
        'move backward': {'linear.x': -0.3},
        'move back': {'linear.x': -0.3},
        'turn left': {'angular.z': 0.5},
        'turn right': {'angular.z': -0.5},
        'strafe left': {'linear.y': 0.3},
        'strafe right': {'linear.y': -0.3},
        'stop': {'linear.x': 0.0, 'linear.y': 0.0, 'angular.z': 0.0},
    }

    NAVIGATION_KEYWORDS = ['go to', 'navigate to', 'move to', 'head to']
    SYSTEM_KEYWORDS = ['start mapping', 'save map', 'shutdown', 'reboot']

    def parse_command(self, text):
        """Convert text to command intent"""
        text = text.lower().strip()

        # Check for motion commands
        for phrase, velocities in self.MOTION_COMMANDS.items():
            if phrase in text:
                return {'type': 'motion', 'velocities': velocities}

        # Check for navigation commands
        for keyword in self.NAVIGATION_KEYWORDS:
            if keyword in text:
                location = text.replace(keyword, '').strip()
                return {'type': 'navigation', 'location': location}

        # Check for system commands
        for keyword in self.SYSTEM_KEYWORDS:
            if keyword in text:
                return {'type': 'system', 'command': keyword}

        return {'type': 'unknown', 'text': text}

    def execute_command(self, intent):
        """Execute parsed command"""
        if intent['type'] == 'motion':
            self.publish_velocity(intent['velocities'])

        elif intent['type'] == 'navigation':
            self.navigate_to_location(intent['location'])

        elif intent['type'] == 'system':
            self.execute_system_command(intent['command'])

        else:
            self.get_logger().warn(f"Unknown command: {intent['text']}")
```

## Wake Word Detection

```python
import porcupine

class WakeWordDetector:
    """Detect wake word before listening for commands"""

    def __init__(self, keyword='jarvis'):
        self.porcupine = porcupine.create(
            access_key='YOUR_PICOVOICE_KEY',
            keywords=[keyword]
        )

    def wait_for_wake_word(self):
        """Block until wake word detected"""
        while True:
            pcm = self.get_next_audio_frame()
            result = self.porcupine.process(pcm)

            if result >= 0:
                return True  # Wake word detected
```

## Text-to-Speech Feedback

```python
from piper import PiperVoice

class TextToSpeech:
    """Provide audio feedback to user"""

    def __init__(self):
        self.voice = PiperVoice.load('en_US-lessac-medium')

    def speak(self, text):
        """Convert text to speech"""
        audio = self.voice.synthesize(text)
        self.play_audio(audio)

    def confirm_command(self, command):
        """Acknowledge received command"""
        responses = {
            'motion': "Moving now",
            'navigation': f"Navigating to {command.get('location')}",
            'system': "Command received",
            'unknown': "Sorry, I didn't understand that",
        }
        self.speak(responses.get(command['type'], "OK"))
```

## Configuration Parameters

```yaml
voice_control:
  # Speech recognition
  engine: 'vosk'  # 'whisper' or 'vosk'
  model_path: '/home/pi/vosk-model-small-en-us-0.15'

  # Wake word
  use_wake_word: true
  wake_word: 'robot'

  # Audio
  sample_rate: 16000
  channels: 1

  # Command processing
  confidence_threshold: 0.7
  command_timeout: 5.0  # seconds

  # Text-to-speech
  enable_tts: true
  tts_engine: 'piper'
  voice: 'en_US-lessac-medium'
```

## Installation

### Vosk Setup

```bash
# Install Vosk
pip3 install vosk

# Download model
cd ~
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

### Whisper Setup

```bash
# Install Whisper
pip3 install openai-whisper

# Models download automatically on first use
# tiny, base, small recommended for Pi 5
```

### Audio Setup

```bash
# Install audio libraries
sudo apt-get install portaudio19-dev python3-pyaudio
pip3 install pyaudio

# Test microphone
arecord -l  # List recording devices
arecord -d 5 test.wav  # Record 5 second test
aplay test.wav  # Play back test
```

## Testing

```bash
# Test voice recognition
ros2 run orbibot_ai test_voice_recognition

# Test command parsing
ros2 run orbibot_ai test_command_parser

# Full integration test
ros2 launch orbibot_ai voice_control.launch.py
```

## Example Commands

| Command | Action |
|---------|--------|
| "Move forward" | Drive forward 0.3 m/s |
| "Turn left" | Rotate counterclockwise |
| "Stop" | Halt all motion |
| "Go to the kitchen" | Navigate to semantic location |
| "Start mapping" | Begin SLAM mapping |
| "Follow me" | Activate person tracking |

## Performance Expectations

| Engine | Latency | Accuracy | CPU Usage | Notes |
|--------|---------|----------|-----------|-------|
| Whisper Tiny | ~2-3s | 90-95% | High | Best accuracy |
| Vosk Small | ~0.5s | 85-90% | Low | Best for real-time |

## Hardware Requirements

| Component | Cost | Notes |
|-----------|------|-------|
| USB Microphone | $10-30 | USB sound card with mic |
| Speaker | $15-40 | USB or 3.5mm speaker |

---

[← Previous: Visual Docking](02-visual-docking.md) | [↑ Index](README.md) | [Next: Gesture Control →](04-gesture-control.md)
