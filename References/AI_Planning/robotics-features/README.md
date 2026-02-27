# OrbiBot Robotics Features

This directory contains detailed documentation for AI-driven robotics features for OrbiBot (Raspberry Pi 5, RealSense D435, RPLidar A1, Mecanum wheels), organized by complexity and domain.

> **For AI development workflow features** (Claude Code integration, MCP servers, code generation), see [../developer-features/](../developer-features/)

## Features Index

### I. Foundation Features (Start Here)

1. [Visual "Follow Me" & Object Tracking](01-visual-tracking.md) - **Moderate**
   - Enable the robot to detect and autonomously follow a person or object
   - Hardware: RealSense D435, Raspberry Pi 5
   - Prerequisites: None (foundational feature)

2. [Visual Docking / Precision Parking](02-visual-docking.md) - **Moderate**
   - Use visual markers for precise docking and charging alignment
   - Hardware: RealSense D435
   - Prerequisites: None (foundational feature)

3. [Voice Command Interface](03-voice-control.md) - **Easy/Moderate**
   - Control the robot using natural voice commands
   - Hardware: USB Microphone, Raspberry Pi 5
   - Prerequisites: None (foundational feature)

### II. Vision & Perception

4. [Gesture Control Teleop](04-gesture-control.md) - **Easy/Moderate**
   - Control the robot using hand gestures
   - Hardware: RealSense D435, Raspberry Pi 5
   - Prerequisites: Feature #1 (object detection pipeline)

5. [Face Recognition & Personalization](05-face-recognition.md) - **Moderate**
   - Recognize known users and personalize robot behavior
   - Hardware: RealSense D435, Raspberry Pi 5
   - Prerequisites: Feature #4 (vision processing pipeline)

6. [Human Pose Estimation & Activity Recognition](06-pose-estimation.md) - **Moderate**
   - Detect human poses and recognize activities
   - Hardware: RealSense D435, Raspberry Pi 5
   - Prerequisites: Feature #4 (MediaPipe pipeline)

7. [Scene Narration (VLM-Powered)](07-scene-narration.md) - **Moderate/Hard**
   - Robot describes its surroundings using Vision-Language Models
   - Hardware: RealSense D435, Raspberry Pi 5
   - Prerequisites: Basic vision pipeline from earlier features

### III. Autonomous Behaviors

8. [Autonomous Security Patrol](08-security-patrol.md) - **Moderate**
   - Patrol predefined waypoints and detect anomalies
   - Hardware: RealSense D435, RPLidar A1, Raspberry Pi 5
   - Prerequisites: Features #1 (object detection), Nav2 navigation

9. [Semantic Navigation (LLM + VLM)](09-semantic-navigation.md) - **Hard**
   - Give natural language navigation commands
   - Hardware: Raspberry Pi 5, RealSense, RPLidar
   - Prerequisites: Features #3 (voice commands), #7 (VLM), Nav2 SLAM

10. [Autonomous Object Retrieval](10-object-retrieval.md) - **Hard**
    - Find and retrieve objects on command
    - Hardware: RealSense D435, RPLidar A1, Raspberry Pi 5, (optional: robot arm)
    - Prerequisites: Features #1, #9 (semantic navigation)

## Implementation Roadmap

See [roadmap.md](roadmap.md) for the recommended progressive learning path, from foundational features through to advanced autonomous behaviors.

**Total estimated time:** 3-4 months for all features (working part-time)

## Quick Links

- [← Back to Main Documentation](../README.md)
- [Implementation Roadmap →](roadmap.md)
- [AI Development Features](../developer-features/)

---

**Last Updated:** 2026-01-20
**Project:** OrbiBot - Mecanum Wheeled Robot
**Platform:** ROS 2 Jazzy, Raspberry Pi 5
