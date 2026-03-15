# OrbiBot Agent

Unified AI agent for OrbiBot with multi-LLM support (Gemini, Claude, Kimi, Ollama) and multiple interfaces (Web GUI, Terminal CLI, MCP).

## Features

- **Multi-LLM Support**: Switch between Gemini, Claude, Kimi, and local Ollama models
- **Native ROS 2**: Direct rclpy integration (no rosbridge overhead)
- **Three Interfaces**:
  - HTTP API for web GUI (`chat_server`)
  - Terminal CLI with rich interface (`chat_cli`)
  - MCP server for Claude Desktop/Cline (`mcp_server`)
- **Safety First**: Built-in velocity limits, duration caps, emergency stop
- **Unified Tools**: Same tools work across all interfaces

## Installation

```bash
cd ~/orbibot_ws
colcon build --packages-select orbibot_agent
source install/setup.bash
```

Install optional dependencies:
```bash
# For all LLM providers
pip install google-genai anthropic openai

# For rich CLI interface
pip install rich

# For MCP server
pip install mcp
```

## Configuration

### 1. Set up your LLM provider(s)

**Recommended: `.env.local`** – keeps keys out of the repo and works from any launch context:

```bash
cd src/orbibot_agent
cp .env.local.example .env.local
# Edit .env.local and add your keys (do not commit .env.local)
```

Format: one `KEY=value` per line. Example:

```
GEMINI_API_KEY=your-gemini-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
```

**Search order** (first found wins):

1. `~/.orbibot/.env.local` – most reliable; symlink: `ln -sf ~/orbibot_ws/src/orbibot_agent/.env.local ~/.orbibot/.env.local`
2. `~/orbibot_ws/src/orbibot_agent/.env.local`
3. `$ORBIBOT_WS/src/orbibot_agent/.env.local` (if set)
4. Package root, cwd

**Alternative: environment variables** – in the same shell before starting:

```bash
export GEMINI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
```

**Ollama (local)** – no key needed; ensure Ollama is running and the default URL is `http://localhost:11434`. Configure in `config/agent_params.yaml` if different.

### 2. Choose default provider and options

The package config is used by default: `config/agent_params.yaml`. Key options:

- **`default_provider`** – which provider to use when none is specified (e.g. `gemini`, `anthropic`, `moonshot`, `ollama`).
- **`llm_providers`** – model names and API key env vars per provider.
- **`safety`** – velocity/duration limits.

Example to use Claude as default:

```yaml
default_provider: "anthropic"
```

To use a custom config file when launching:

```bash
ros2 launch orbibot_agent chat_server.launch.py config:=/path/to/your_agent_params.yaml
```

### 3. Choosing provider when using the HTTP API

- **Default**: The server uses `default_provider` from the config (or `gemini` if not set).
- **Per request**: Send `provider` in the JSON body to use a specific provider for that request:
  ```bash
  curl -X POST http://localhost:8082/api/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Hello", "provider": "anthropic"}'
  ```
- **List providers**: `GET http://localhost:8082/api/providers` returns available providers and the current one.

## Usage

### 1. HTTP Chat Server (for Web GUI)

```bash
ros2 launch orbibot_agent chat_server.launch.py
```

API endpoints:
- `POST /api/chat` - Send message, get response (optional body: `provider`)
- `POST /api/reset` - Reset chat session
- `GET /api/health` - Health check
- `GET /api/providers` - List available providers and current

### 2. Terminal CLI

```bash
# Use default provider
ros2 run orbibot_agent chat_cli

# Specify provider
ros2 run orbibot_agent chat_cli --provider claude

# Switch providers interactively
/provider gemini
/provider anthropic
/provider moonshot
/provider ollama
```

CLI commands:
- `/help` - Show help
- `/providers` - List available providers
- `/provider <name>` - Switch provider
- `/reset` - Reset chat
- `/tools` - List available tools
- `exit` or `quit` - Exit

### 3. MCP Server (Claude Desktop, Cline, Cursor)

The MCP server speaks stdio and exposes OrbiBot tools (move, sensors, ROS services/actions) to any MCP client.

**Cursor** (this workspace): A project config is already in `.cursor/mcp.json`. Restart Cursor and the **orbibot** server will appear under Tools & MCP. Agent can then use OrbiBot tools when chatting in this project.

**Claude Desktop**: Add to `~/.claude/settings.json`:
```json
{
  "mcpServers": {
    "orbibot": {
      "command": "bash",
      "args": [
        "-lc",
        "source /opt/ros/jazzy/setup.bash && source ~/orbibot_ws/install/setup.bash && ros2 run orbibot_agent mcp_server"
      ]
    }
  }
}
```

**Global Cursor / other projects**: Use `~/.cursor/mcp.json` with the same `orbibot` entry as above.

## Architecture

```
┌─────────────────────────────────────────┐
│         User Interfaces                  │
│  Web GUI │ Terminal │ Claude/Cline/Cursor │
└──────────┴──────────┴───────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│   Chat Server │ MCP Server │ CLI        │
│        (HTTP) │ (stdio)    │ (terminal) │
└───────────────┴────────────┴────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│      Agent Node (ROS 2)                 │
│  ┌──────────────┐ ┌─────────────────┐  │
│  │ LLM Provider │ │ Tool Registry   │  │
│  │ (Multi-LLM)  │ │ (53 robot tools)│  │
│  └──────────────┘ └─────────────────┘  │
└─────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────┐
│   Safety Manager │ ROS Bridge (rclpy)   │
└─────────────────────────────────────────┘
           │
           ▼
         ROS 2
```

## Available Tools (53 total)

### Motion Tools
| Tool | Description |
|------|-------------|
| `move_robot` | Move with velocities (vx, vy, wz) for a duration |
| `stop_robot` | Immediately publish zero velocity |
| `set_motor_enable` | Enable/disable motors via `/orbibot/set_motor_enable` |
| `reset_firmware_state` | Emergency: stop motors, clear odometry, reset agent e-stop |

### GET — Sensor Tools
| Tool | Description |
|------|-------------|
| `get_battery` | Battery voltage and level |
| `get_imu` | Filtered IMU orientation (roll, pitch, yaw) and angular velocities |
| `get_imu_raw` | Raw ICM-20948 gyro (rad/s) and accel (m/s²) before Madgwick |
| `get_magnetometer` | ICM-20948 AK09916 compass in µT |
| `get_encoder_counts` | Raw encoder ticks [FL, BL, FR, BR] |
| `get_joint_states` | Wheel positions (rad) and velocities (rad/s) |
| `get_odometry` | Full odometry: position, yaw, velocity |
| `get_robot_position` | Simplified position (x, y, yaw) |
| `get_lidar_summary` | LiDAR scan with obstacle detection |
| `get_safety_status` | E-stop, faults, cmd_timeout, battery warnings |
| `get_system_enriched` | Battery + CPU%, RAM%, temp°C, disk% |
| `get_firmware_version` | STM32 firmware version (major.minor) |
| `get_all_firmware_data` | One-shot snapshot of ALL firmware values |

### GET — System / ROS Tools
| Tool | Description |
|------|-------------|
| `list_topics` | List all active ROS topics |
| `get_system_status` | CPU, RAM, temperature via /proc |
| `list_services` | List all ROS services |
| `ros2_list_actions` | List available ROS action servers |
| `ros2_list_active_goals` | List currently active action goals |

### SET — Firmware Command Tools
| Tool | Description |
|------|-------------|
| `set_motor_pid` | Set motor PID (Kp, Ki, Kd) — temporary, lost on reboot |
| `save_motor_pid` | Save motor PID to firmware flash — persists after reboot |
| `set_yaw_pid` | Set yaw PID (Kp, Ki, Kd) — temporary |
| `save_yaw_pid` | Save yaw PID to firmware flash — persists after reboot |
| `set_beep` | Control buzzer: 0=off, 1=continuous, ≥10=N ms |
| `reset_odometry` | Reset firmware odometry to zero (encoder counts unchanged) |
| `reset_encoders` | Reset encoder counts to zero on MCU |
| `calibrate_imu` | Trigger magnetometer auto-calibration (zero hard-iron) |
| `set_mag_calibration` | Set explicit magnetometer offsets in µT |

### Service / Action Tools
| Tool | Description |
|------|-------------|
| `ros2_service_call` | Call any ROS service dynamically |
| `ros2_send_action_goal` | Send a goal to a ROS action server |
| `ros2_cancel_action_goal` | Cancel an active goal |
| `ros2_action_request_result` | Get action result |
| `ros2_action_subscribe_status` | Get action server status |

### PID Tuning Tools
| Tool | Description |
|------|-------------|
| `run_pid_test` | Drive at target velocity, record /odom response — returns MAE and overshoot |

### Hardware Testing Tools
| Tool | Description |
|------|-------------|
| `run_motor_test` | Spin motor(s) and compare encoder response vs expected ticks |
| `run_imu_test` | Sample IMU 20×, check gyro bias and gravity magnitude |
| `run_encoder_test` | Drive N cm, compare encoder-measured vs commanded distance |
| `run_mag_test` | Sample magnetometer 15×, check field magnitude and stability |
| `run_battery_test` | Monitor voltage 10× over 5 s, flag high-swing cells |
| `run_beep_test` | 3-beep confirmation pattern |
| `run_full_hardware_test` | Run all subsystem tests in sequence, return pass/fail report |

### SLAM Tools (Phase 2)
| Tool | Description |
|------|-------------|
| `slam_save_map` | Save pose graph + pgm/yaml to disk (e.g. `/home/orbibot/maps/my_map`) |
| `slam_serialize_map` | Save pose graph only for later localization-mode reload |
| `slam_get_map_info` | Map width/height, resolution, origin, explored% |

### Navigation Tools — Nav2 (Phase 2)
| Tool | Description |
|------|-------------|
| `set_initial_pose` | Tell AMCL where the robot is: x, y, yaw_deg in map frame |
| `amcl_reinitialize` | Scatter AMCL particles globally when robot is completely lost |
| `navigate_to_pose` | Navigate to target x, y, yaw_deg using Nav2 NavigateToPose action |
| `navigate_through_poses` | Navigate through an ordered list of poses |
| `follow_waypoints` | Patrol route through ordered waypoints (FollowWaypoints action) |
| `nav_cancel` | Cancel all active Nav2 navigation goals |
| `nav_clear_costmaps` | Clear local, global, or both costmaps |
| `nav_spin` | In-place rotation recovery (Nav2 Spin action) |
| `nav_backup` | Short reverse recovery (Nav2 BackUp action) |
| `nav_get_plan` | Read current /plan path: waypoint count, start/end coords |

### Exploration Tools (Phase 2)
| Tool | Description |
|------|-------------|
| `exploration_start` | Start autonomous frontier exploration |
| `exploration_stop` | Stop exploration |
| `exploration_pause` | Pause exploration (robot stays in place) |
| `exploration_resume` | Resume exploration after pause |
| `get_exploration_status` | Current state: idle/exploring/navigating/complete/stopped |
| `get_exploration_frontiers` | Frontier count and centroid positions in map frame |

### Generic Interface Tool (Phase 2)
| Tool | Description |
|------|-------------|
| `ros2_topic_publish` | Publish to any ROS topic (one-shot, for interfaces without a dedicated tool) |

---

## Quick-Start Conversation Examples

```
# Get full robot snapshot
"Show me everything about the current robot state"
→ Uses get_all_firmware_data

# PID tuning workflow
"Set motor PID to Kp=1.0, Ki=0.1, Kd=0.3 then test it"
→ Uses set_motor_pid + run_pid_test

# Make PID permanent
"Save the current PID values to flash"
→ Uses save_motor_pid (with values from tuning session)

# Hardware self-check
"Run the full hardware test"
→ Uses run_full_hardware_test

# Buzzer
"Beep three times"
→ Uses set_beep with 200ms, 0, 200ms, 0, 200ms

# Encoder reset + distance test
"Reset encoders and drive 30 cm forward to check accuracy"
→ Uses reset_encoders + run_encoder_test

# Calibrate magnetometer
"Calibrate the compass"
→ Uses calibrate_imu

# Navigate to a target (Phase 2 — replaces manual action goal construction)
"Navigate to x=2.0, y=1.0 facing north"
→ Uses navigate_to_pose(x=2.0, y=1.0, yaw_deg=90)

# Set robot position on map
"The robot is at position 1.5, 0.8 facing east"
→ Uses set_initial_pose(x=1.5, y=0.8, yaw_deg=0)

# Robot is lost
"Re-initialise localisation globally"
→ Uses amcl_reinitialize()

# Save the map after exploring
"Save the current map as kitchen_map"
→ Uses slam_save_map("/home/orbibot/maps/kitchen_map")

# Check map coverage
"How much of the map have we explored?"
→ Uses slam_get_map_info()

# Start autonomous exploration
"Start autonomous exploration"
→ Uses exploration_start()

# Patrol route
"Patrol: bedroom, kitchen, living room"
→ Uses follow_waypoints([{x:1.5,y:0},{x:3.2,y:1.1},{x:0.5,y:2.0}])

# Get unstuck
"The robot is stuck — back up and try again"
→ Uses nav_backup() + nav_clear_costmaps() + navigate_to_pose(...)
```

## Nav2 Navigation Examples

### Simple navigation (use the dedicated tool)
```
navigate_to_pose(x=2.0, y=1.0, yaw_deg=0)
```

### Low-level action goal (if needed)
```json
{
  "action_name": "/navigate_to_pose",
  "action_type": "nav2_msgs/action/NavigateToPose",
  "goal": {
    "pose": {
      "header": {"frame_id": "map"},
      "pose": {
        "position": {"x": 2.0, "y": 1.0, "z": 0.0},
        "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
      }
    }
  }
}
```

## Service Call Examples

```bash
# Clear global costmap (use nav_clear_costmaps tool instead)
ros2_service_call({
  "service_name": "/global_costmap/clear_entirely_global_costmap",
  "service_type": "nav2_msgs/srv/ClearEntireCostmap",
  "request": {}
})

# Load map
ros2_service_call({
  "service_name": "/map_server/load_map",
  "service_type": "nav2_msgs/srv/LoadMap",
  "request": {"map_url": "/path/to/map.yaml"}
})
```

## Package Structure

```
orbibot_agent/
├── core/               # Safety manager, ROS bridge
├── llm_providers/      # Gemini, Claude, Kimi, Ollama
├── tools/              # Tool registry and implementations
├── interfaces/         # Chat server, MCP server, CLI
├── launch/             # Launch files
└── config/             # Configuration YAML
```

## License

MIT