# OrbiBot Agent

AI agent for OrbiBot — a Mecanum-wheeled ROS 2 mobile robot (Raspberry Pi 5 + Yahboom ROSMaster V3.0). Supports multiple LLM providers (Gemini, Claude, Kimi, Ollama) and exposes 58 robot tools through three interfaces: HTTP API, terminal CLI, and MCP server.

**Status:** runs on the robot; its chat server is what the web dashboard's chat panel talks to.
It talks to ROS 2 through its own rclpy bridge (`core/ros_bridge/`), not through rosbridge.
`core/ros_bridge/motion.py` publishes `/cmd_vel` directly, so the agent is one of four
unarbitrated `/cmd_vel` sources; in the [command pipeline design](../../docs/architecture/command-pipeline.md)
it gets its own topic at a priority below the dashboard, so a person can always override it.

## What This Package Does

`orbibot_agent` sits between **users** and the **robot's ROS 2 stack**. A user sends a natural language message (e.g., "move forward 30 cm"), the LLM decides which tool(s) to call, and the agent executes them through a native ROS 2 bridge — no rosbridge overhead.

```
User (web / terminal / Claude Desktop)
  |
  v
Interface (HTTP API / CLI / MCP)
  |
  v
AgentNode  ─── LLM Provider (Gemini / Claude / Kimi / Ollama)
  |                  |
  |          tool call decisions
  |                  |
  v                  v
ToolRegistry (58 tools)
  |
  v
RosBridge (native rclpy)  ───>  ROS 2 topics, services, actions
  |
  v
SafetyManager (velocity/duration limits, e-stop)
```

## System Architecture

### Node Structure

| Component | Role |
|-----------|------|
| **AgentNode** | Orchestrator — manages providers, tools, and message processing |
| **RosBridge** | Native rclpy bridge to ROS 2 (pub/sub, services, actions) |
| **SafetyManager** | Enforces velocity limits (0.5 m/s), duration caps (10s), e-stop |
| **ToolRegistry** | Registers 58 tools with JSON schemas for LLM function calling |
| **LLM Providers** | Pluggable backends — each handles chat history and streaming |

### Data Flow

1. User sends message via any interface
2. AgentNode activates the configured LLM provider
3. LLM returns text and/or tool calls
4. ToolRegistry executes each tool through RosBridge
5. Results are sent back to the LLM for the next round (up to 10 iterations)
6. Final text response is returned to the user

### Interfaces

| Interface | Protocol | Port | Use Case |
|-----------|----------|------|----------|
| **Chat Server** | HTTP + SSE | 8082 | Web GUI integration |
| **Chat CLI** | Terminal | — | Interactive debugging |
| **MCP Server** | stdio | — | Claude Desktop, Cline, Cursor |

## ROS 2 Integration

### How the Agent Talks to the Robot

RosBridge (`core/ros_bridge/`) creates subscriptions and publishers on the host ROS node. It does **not** use rosbridge_suite or WebSocket — it's direct rclpy.

**Subscribed topics:** `/odom`, `/imu/data`, `/imu/data_raw`, `/scan`, `/orbibot/system_status`, `/orbibot/encoders`, `/joint_states`, etc.

**Published topics:** `/cmd_vel` (velocity commands)

**Services called:** `/orbibot/set_motor_enable`, `/slam_toolbox/save_map`, any service via `ros2_service_call`

**Actions used:** `/navigate_to_pose`, `/navigate_through_poses`, `/follow_waypoints`, `/spin`, `/backup`

### Launch Files

```bash
# HTTP chat server (main interface for web GUI)
ros2 launch orbibot_agent chat_server.launch.py

# With custom config
ros2 launch orbibot_agent chat_server.launch.py config:=/path/to/agent_params.yaml

# MCP server for Claude Desktop
ros2 run orbibot_agent mcp_server

# Terminal CLI
ros2 run orbibot_agent chat_cli --provider anthropic
```

## Firmware Communication

The agent does **not** talk to firmware directly. It goes through the ROS 2 stack:

```
Agent  ──>  RosBridge  ──>  /cmd_vel topic  ──>  orbibot_hardware_node  ──>  USB serial  ──>  STM32
```

- **Motion:** publishes `Twist` on `/cmd_vel`
- **Sensor reads:** subscribes to topics published by `orbibot_hardware_node` (battery, IMU, encoders, odometry)
- **Firmware commands:** calls ROS services exposed by `orbibot_hardware_node` (PID set/save, beep, calibrate, reset)

## Configuration

### API Keys (`.env.local`)

```bash
# Copy example and edit
cp .env.local.example .env.local

# Add your keys (never commit this file)
GEMINI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
MOONSHOT_API_KEY=your-key
```

**Search order** (first found wins):
1. `~/.orbibot/.env.local`
2. `~/orbibot_ws/src/orbibot_agent/.env.local`
3. `$ORBIBOT_WS/src/orbibot_agent/.env.local`
4. Package root / CWD

### Config File (`config/agent_params.yaml`)

```yaml
safety:
  max_linear_vel: 0.5        # m/s
  max_angular_vel: 2.0       # rad/s
  max_duration: 10.0         # seconds

llm_providers:
  gemini:
    model: "gemini-2.0-flash"
    api_key_env: "GEMINI_API_KEY"
  anthropic:
    model: "claude-3-5-sonnet-20241022"
    api_key_env: "ANTHROPIC_API_KEY"
  moonshot:
    model: "kimi-latest"
    api_key_env: "MOONSHOT_API_KEY"
  ollama:
    model: "llama3.1:8b"
    base_url: "http://localhost:11434/v1"

default_provider: "gemini"
```

### System Prompt (`config/system_prompt.txt`)

Edit this file to customize the LLM's behavior and knowledge. The unified prompt covers all capabilities: motion, sensors, testing, diagnostics, analysis, SLAM, and navigation. Loaded automatically at startup.

## Key Modules

### `agent_node.py` — Orchestrator

Central class that ties everything together. Manages provider switching, loads the unified system prompt, and runs the tool-call loop. Supports both blocking (`process_message`) and streaming (`process_message_stream`) execution.

### `core/ros_bridge/` — ROS 2 Communication

Split into 7 focused modules composed via mixins:

| Module | Responsibility |
|--------|---------------|
| `base.py` | Shared state, `wait_for_message`, quaternion utils |
| `motion.py` | Velocity publishing, `move_for_duration` |
| `sensors.py` | Battery, IMU, encoders, odometry, LiDAR reads |
| `firmware.py` | PID set/save, beep, calibration, reset, version |
| `services.py` | Dynamic service calling, topic listing/publishing |
| `actions.py` | Action client management, goal tracking |
| `navigation.py` | Nav2, SLAM, AMCL, exploration wrappers |

Import as `from orbibot_agent.core.ros_bridge import RosBridge` — the facade class composes all mixins.

### `core/safety_manager.py` — Safety Layer

Validates and clamps velocity/duration before any motion command. Manages emergency stop state. All motion goes through safety validation.

### `core/test_suite_runner.py` — Deterministic Tests

Runs fixed, reproducible hardware test sequences using the tool registry directly (no LLM). Used by the `run_health_check` tool. Tests: battery, IMU, encoders, motors.

### `tools/` — Tool Definitions

Split into 7 focused modules:

| Module | Tools |
|--------|-------|
| `tool_registry.py` | Thin dispatcher (register, get_schemas, execute) |
| `motion_tools.py` | move, stop, motor enable, firmware reset (4) |
| `sensor_tools.py` | battery, IMU, encoders, odometry, LiDAR (13) |
| `firmware_tools.py` | PID set/save, beep, calibration, reset (7) |
| `ros_tools.py` | topics, services, actions, generic publish (10) |
| `navigation_tools.py` | SLAM, Nav2, AMCL, exploration (19) |
| `diagnostics_tools.py` | run_health_check, record_timeseries, get_ros_diagnostics (3) |
| `analysis_tools.py` | compare_values, compute_statistics (2) |

Each module exports `register(registry, ros_bridge, safety_manager)`. All tools use OpenAI function-calling JSON schemas.

### `llm_providers/` — LLM Backends

| File | Provider | SDK |
|------|----------|-----|
| `gemini_provider.py` | Google Gemini | google-genai |
| `anthropic_provider.py` | Claude | anthropic |
| `openai_compat_provider.py` | Base class for OpenAI-compatible APIs | openai |
| `moonshot_provider.py` | Kimi (extends OpenAI compat) | openai |
| `ollama_provider.py` | Ollama local (extends OpenAI compat) | openai |

All providers implement streaming (`send_message_stream`, `send_tool_results_stream`).

### `interfaces/` — User-Facing Endpoints

- **`chat_server.py`** — aiohttp server with blocking + SSE streaming endpoints. Runs ROS spin in a background thread.
- **`chat_cli.py`** — Rich terminal interface with `/provider`, `/tools`, `/reset` commands.
- **`mcp_server.py`** — MCP stdio server that exposes tools to Claude Desktop/Cline.

## HTTP API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Blocking chat — returns `{reply, tool_calls}` |
| `/api/chat/stream` | POST | SSE stream — yields `text_chunk`, `tool_start`, `tool_result`, `done` events |
| `/api/reset` | POST | Reset chat session |
| `/api/health` | GET | Status + available providers |
| `/api/providers` | GET | List providers + current |

**Request body** (chat endpoints):
```json
{
  "message": "What's the battery level?",
  "provider": "anthropic",
  "messages": []
}
```

All fields except `message` are optional. `messages` is a list of `{role, content}` for context recovery.

## How to Run

```bash
# 1. Build
cd ~/orbibot_ws
colcon build --packages-select orbibot_agent
source install/setup.bash

# 2. Set API key
export GEMINI_API_KEY="your-key"

# 3. Launch (pick one)
ros2 launch orbibot_agent chat_server.launch.py   # HTTP server
ros2 run orbibot_agent chat_cli                     # Terminal
ros2 run orbibot_agent mcp_server                   # MCP
```

## How to Extend

### Adding a New Tool

1. Pick the right module (e.g., `sensor_tools.py` for a new sensor read)
2. Add a handler and registration inside the `register()` function:
   ```python
   def _handle_my_tool(param: str) -> Dict:
       return ros_bridge.some_method(param)

   registry.register_tool(
       name='my_tool',
       description='What it does',
       parameters={'type': 'object', 'properties': {...}, 'required': [...]},
       handler=_handle_my_tool,
   )
   ```
3. If creating a new category, add a new `*_tools.py` module and import it in `tool_registry.py`.

### Adding a New LLM Provider

If OpenAI-compatible: subclass `OpenAICompatProvider` (see `moonshot_provider.py` — ~30 lines).

If not: subclass `BaseLLMProvider` and implement `initialize`, `send_message`, `send_tool_results`, `start_chat`, and optionally the streaming methods.

Register in `agent_node.py` `_init_providers`.

### What NOT to Break

- **RosBridge** is the single point of ROS 2 communication — don't create parallel publishers
- **SafetyManager** must validate all motion — don't bypass it
- **Tool schemas** must be valid JSON Schema — LLMs depend on them for function calling
- The chat server's `_chat_lock` prevents concurrent LLM calls — don't remove it

## Package Structure

```
orbibot_agent/
  orbibot_agent/
    __init__.py
    agent_node.py                  # Orchestrator (AgentNode)
    env_loader.py                  # .env.local loader
    core/
      safety_manager.py            # Velocity/duration safety
      test_suite_runner.py         # LLM-free hardware tests (used by run_health_check)
      ros_bridge/                  # ROS 2 bridge (mixin architecture)
        __init__.py                #   Facade — composes all mixins
        base.py                    #   Shared state, wait_for_message
        motion.py                  #   cmd_vel, move_for_duration
        sensors.py                 #   Battery, IMU, encoders, odometry, LiDAR
        firmware.py                #   PID, beep, calibration, reset
        services.py                #   Dynamic service/topic calls
        actions.py                 #   Action client management
        navigation.py              #   Nav2, SLAM, AMCL, exploration
    llm_providers/
      base_provider.py             # Abstract base
      openai_compat_provider.py    # Shared OpenAI-compatible base
      gemini_provider.py           # Google Gemini
      anthropic_provider.py        # Claude
      moonshot_provider.py         # Kimi (extends OpenAI compat)
      ollama_provider.py           # Ollama (extends OpenAI compat)
    tools/
      tool_registry.py             # Thin dispatcher
      motion_tools.py              # 4 motion tools
      sensor_tools.py              # 15 sensor/GET tools
      firmware_tools.py            # 9 firmware command tools
      ros_tools.py                 # 11 ROS interface tools
      navigation_tools.py          # 18 nav/SLAM/exploration tools
      diagnostics_tools.py         # 3 diagnostics tools (health check, timeseries, ROS diagnostics)
      analysis_tools.py            # 2 analysis tools (compare, statistics)
    interfaces/
      chat_server.py               # HTTP + SSE server
      chat_cli.py                  # Terminal CLI
      mcp_server.py                # MCP stdio server
  launch/
    chat_server.launch.py
    mcp_server.launch.py
  config/
    agent_params.yaml
    system_prompt.txt              # Unified system prompt (edit to customize LLM behavior)
```

## Limitations

- **Single concurrent session** — the chat server uses a lock; only one chat request at a time
- **No vision tools yet** — camera image capture and object detection are planned
- **No persistent conversation** — chat history resets on server restart
- **No unit tests** — test infrastructure needed (see [known-issues.md](known-issues.md))
- **Ollama tool calling** — depends on model support; not all local models handle function calling well

## License

Apache-2.0, as the rest of the repository.
