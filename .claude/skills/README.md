# OrbiBot Skills Index

Skills in this folder are auto-discovered by Cursor. Each skill is a single `SKILL.md` with YAML frontmatter (`name`, `description`). Naming is **snake_case** for consistency.

---

## How to use these skills

### In Cursor (Cursor IDE)

1. **Auto-discovery**  
   Cursor discovers skills under `.claude/skills/` and can inject them when your question matches a skill’s `description` (e.g. “add a systemd service for the robot” → `robot_bringup`).

2. **Mention the skill**  
   In the chat, refer to the skill by name so the right context is used, e.g.:  
   - “Using the **robot_bringup** skill, add a systemd unit for orbibot_bringup.”  
   - “Following **ros2_launch_config**, refactor this launch file.”

3. **@-mention the file**  
   To force a skill into context: type `@` and choose `.claude/skills/<name>/SKILL.md` (e.g. `@.claude/skills/nav2/SKILL.md`).

4. **Rules + skills**  
   Rules in `.claude/rules/` (and root `CLAUDE.md`) are always in context; skills are pulled in when relevant or when you @ them.

### In Claude Code (Claude for development)

1. **Project rules**  
   If your project is set up to use `.claude/` (e.g. via Cursor or a similar integration), the same skills are available when the agent reads this repo.

2. **Explicit reference**  
   Ask the agent to “read `.claude/skills/<skill_name>/SKILL.md` and apply it to …” when you want a specific skill used.

3. **Index**  
   Point the agent at this file: “Read `.claude/skills/README.md` and use the skill that matches …” so it can pick the right one.

### Quick reference

| You want to…                    | Use skill(s) |
|---------------------------------|--------------|
| Add a ROS2 node / service       | `ros2_node_creation`, `ros2_service_action` |
| Compose launch files             | `ros2_launch_config`, `robot_bringup` |
| Work on Nav2 / costmaps          | `nav2`, `path_planning` |
| Camera / LiDAR / perception     | `robot_perception`, `camera_vision`, `lidar_pointcloud` |
| SLAM / EKF / localization        | `sensor_fusion_slam` |
| Safety / watchdogs / security   | `safety_systems`, `robotics_security` |
| Testing                         | `ros2_testing`, `robotics_testing` |
| Web API / dashboard              | `ros2_web_integration` |
| Docker for ROS2                 | `docker_ros2_development` |
| STM32 / firmware / serial       | `microcontrollers`, `serial_can_protocols` |

---

## Conventions

- **Folder name** = skill identifier (e.g. `robot_bringup`).
- **name** in frontmatter must match the folder name.
- **description** is used for triggering; keep it concise and keyword-rich.

## Skills by Category

### ROS 2 core (Clean Architecture–oriented)

| Skill | Purpose |
|-------|---------|
| `ros2_node_creation` | Node templates, QoS, Python & C++ |
| `ros2_launch_config` | Launch composition, parameter management |
| `ros2_service_action` | Service and Action patterns |
| `ros2_messaging` | Pub/Sub, thread-safe buffers |
| `ros2_testing` | Unit / integration / E2E (Clean Arch) |
| `ros2_lifecycle` | Managed (lifecycle) nodes |
| `ros2_transforms` | TF2 and transform handling |
| `ros2_diagnostics` | Health monitoring, diagnostic_updater |
| `ros2_bag` | Bag recording and analysis |

### Bringup, architecture, and design

| Skill | Purpose |
|-------|---------|
| `robot_bringup` | systemd, launch layering, udev, watchdog, graceful shutdown |
| `robot_architecture` | High-level design, BT/FSM, state estimation |
| `robotics_design_patterns` | Behavior trees, HAL, safety patterns, sim-to-real |
| `robotics_software_principles` | SOLID, clean architecture, dependency injection for robotics |

### Perception and sensors

| Skill | Purpose |
|-------|---------|
| `robot_perception` | Multi-sensor pipelines, calibration, detection, fusion |
| `camera_vision` | Cameras, OpenCV, calibration, depth pipelines |
| `lidar_pointcloud` | LiDAR, PCL, Open3D, filtering, ICP |
| `sensor_fusion_slam` | EKF/UKF, slam_toolbox, Cartographer, RTAB-Map |

### Navigation and control

| Skill | Purpose |
|-------|---------|
| `nav2` | Nav2 stack, costmaps, planners, controllers, recovery |
| `path_planning` | A*, RRT, costmaps, waypoint following |
| `control_systems` | PID, LQR, MPC, trajectories |
| `realtime_motor_control` | Motor drivers, PID tuning, PREEMPT_RT |

### Hardware, safety, and security

| Skill | Purpose |
|-------|---------|
| `microcontrollers` | STM32, ESP32, firmware, HAL (e.g. Yahboom ROSMaster) |
| `serial_can_protocols` | UART, CAN, EtherCAT — serial/firmware interfaces |
| `safety_systems` | Watchdogs, functional safety, SROS2 basics |
| `robotics_security` | SROS2, DDS security, hardening, network segmentation |

### Modeling, web, and tooling

| Skill | Purpose |
|-------|---------|
| `robot_modeling` | URDF, Xacro, TF2, robot_state_publisher |
| `ros2_web_integration` | FastAPI/Flask bridges, WebSocket, MJPEG, REST APIs |
| `robotics_testing` | Test pyramid, launch_testing, mock hardware, CI/CD |
| `docker_ros2_development` | Docker, docker-compose, DDS in containers, GPU passthrough |

## Cross-references

- **Testing:** `ros2_testing` (Clean Arch structure) ↔ `robotics_testing` (pyramid, HIL, sim, CI/CD).
- **Perception:** `robot_perception` (umbrella) uses `camera_vision` and `lidar_pointcloud` for modality-specific details.
- **Safety vs security:** `safety_systems` = physical/functional safety; `robotics_security` = cyber hardening and SROS2.

## Source

- ROS 2–focused skills (ros2_*) and rules live in this repo.
- Robotics content came from `skills/robotics-agent-skills` (engineer-curated) and `skills/Agentic-Robotics`; copies were refactored here with consistent naming.

**From robotics-agent-skills, not added:** `ros1` (OrbiBot is ROS 2 only), `ros2` (broad ROS2 skill; we use focused ros2_* skills instead). If you need a single “ROS2 overview” skill, consider adding `skills/robotics-agent-skills/skills/ros2/SKILL.md` as `ros2_development` or similar.
