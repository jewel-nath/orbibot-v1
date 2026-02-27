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
pip install google-generativeai anthropic openai

# For rich CLI interface
pip install rich

# For MCP server
pip install mcp
```

## Configuration

Set API keys as environment variables:
```bash
export GEMINI_API_KEY="your-key-here"      # For Gemini
export ANTHROPIC_API_KEY="your-key-here"   # For Claude
export MOONSHOT_API_KEY="your-key-here"    # For Kimi
```

Or create a config file at `~/orbibot_ws/src/orbibot_agent/config/agent_params.yaml`.

## Usage

### 1. HTTP Chat Server (for Web GUI)

```bash
ros2 launch orbibot_agent chat_server.launch.py
```

API endpoints:
- `POST /api/chat` - Send message, get response
- `POST /api/reset` - Reset chat session
- `GET /api/health` - Health check
- `GET /api/providers` - List available providers

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

### 3. MCP Server (for Claude Desktop/Cline)

Add to your MCP config (Claude Desktop: `~/.claude/settings.json`):
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

## Architecture

```
┌─────────────────────────────────────────┐
│         User Interfaces                  │
│  Web GUI │ Terminal │ Claude/Cline      │
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
│  │ (Multi-LLM)  │ │ (15 robot tools)│  │
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

## Available Tools

### Motion Tools
| Tool | Description |
|------|-------------|
| `move_robot` | Move with velocities for duration |
| `stop_robot` | Emergency stop |

### Sensor Tools
| Tool | Description |
|------|-------------|
| `get_battery` | Battery voltage and status |
| `get_imu` | IMU orientation and velocities |
| `get_odometry` | Full odometry data |
| `get_robot_position` | Simplified position (x, y, yaw) |
| `get_lidar_summary` | LiDAR scan with obstacles |

### System Tools
| Tool | Description |
|------|-------------|
| `list_topics` | List ROS topics |
| `get_system_status` | CPU, RAM, temperature, battery |

### Service Tools ✅ NEW
| Tool | Description |
|------|-------------|
| `list_services` | List all ROS services with types |
| `ros2_service_call` | Call any ROS service |

### Action Tools ✅ NEW
| Tool | Description |
|------|-------------|
| `ros2_list_actions` | List available action servers |
| `ros2_send_action_goal` | Send action goal (e.g., navigate_to_pose) |
| `ros2_cancel_action_goal` | Cancel an action goal |
| `ros2_action_request_result` | Get action result |
| `ros2_action_subscribe_status` | Get action server status |
| `ros2_list_active_goals` | List all active goals |

## Nav2 Navigation Example

The agent can now control Nav2 navigation through actions:

```bash
# User: "Navigate to position x=2.0, y=1.0"
# Agent will use:
# 1. ros2_list_actions - Find /navigate_to_pose
# 2. ros2_send_action_goal - Send navigation goal
# 3. ros2_action_request_result - Check completion
```

Example goal for NavigateToPose:
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
# Clear global costmap
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