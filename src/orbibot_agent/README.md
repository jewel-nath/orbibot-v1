# OrbiBot Agent

AI agent for OrbiBot — a Mecanum-wheeled ROS 2 mobile robot (Raspberry Pi 5 + Yahboom ROSMaster V3.0). Supports multiple LLM providers (Gemini, Claude, Kimi, Ollama) and exposes 65 robot tools through three interfaces: HTTP API, terminal CLI, and MCP server.

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
ToolRegistry (65 tools)
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
| **ToolRegistry** | Registers 65 tools with JSON schemas for LLM function calling |
| **LLM Providers** | Pluggable backends — each handles chat history and streaming |

### Data Flow

1. User sends message via any interface
2. AgentNode selects the LLM provider (based on mode and config)
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

RosBridge (`core/ros_bridge.py`) creates subscriptions and publishers on the host ROS node. It does **not** use rosbridge_suite or WebSocket — it's direct rclpy.

**Subscribed topics:** `/odom`, `/imu/data`, `/imu/data_raw`, `/imu/mag`, `/scan`, `/orbibot/system_status`, `/orbibot/encoders`, `/joint_states`, etc.

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

robot_tester:
  provider: "anthropic"       # Stronger model for testing
  model: "claude-3-5-sonnet-20241022"
```

## Key Modules

### `agent_node.py` — Orchestrator

Central class that ties everything together. Manages provider switching, system prompts (chat vs. robot_tester mode), and the tool-call loop. Supports both blocking (`process_message`) and streaming (`process_message_stream`) execution.

### `core/ros_bridge.py` — ROS 2 Communication

The largest file (~1900 lines). Handles all ROS 2 I/O: topic subscriptions, service calls, action goals, and a `wait_for_message` pattern for synchronous sensor reads. Also implements higher-level operations like `move_for_duration`, `run_pid_test`, and Nav2 wrappers.

### `core/safety_manager.py` — Safety Layer

Validates and clamps velocity/duration before any motion command. Manages emergency stop state. All motion goes through safety validation.

### `tools/tool_registry.py` — Tool Definitions

Registers 65 tools with JSON schemas (OpenAI function-calling format). Each tool has a name, description, parameter schema, and handler function. The registry is provider-agnostic.

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
| `/api/run_test_suite` | POST | LLM-free hardware tests — `{tests: [...]}` or `{}` for all |
| `/api/health` | GET | Status + available providers |
| `/api/providers` | GET | List providers + current |

**Request body** (chat endpoints):
```json
{
  "message": "What's the battery level?",
  "provider": "anthropic",
  "mode": "chat",
  "messages": []
}
```

All fields except `message` are optional.

## Modes

| Mode | System Prompt | Use Case |
|------|--------------|----------|
| `chat` (default) | General robot assistant | Normal interaction |
| `robot_tester` | Systematic test engineer with pass/fail reporting | Hardware validation |

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

1. Add a handler method to `tool_registry.py`:
   ```python
   def _handle_my_tool(self, param: str) -> Dict:
       return self._ros_bridge.some_method(param)
   ```

2. Register it in `_register_default_tools()`:
   ```python
   self.register_tool(
       name='my_tool',
       description='What it does',
       parameters={'type': 'object', 'properties': {...}, 'required': [...]},
       handler=self._handle_my_tool,
   )
   ```

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
    agent_node.py              # Orchestrator (AgentNode)
    env_loader.py              # .env.local loader
    core/
      ros_bridge.py            # Native ROS 2 bridge (~1900 lines)
      safety_manager.py        # Velocity/duration safety
      test_suite_runner.py     # LLM-free hardware tests
    llm_providers/
      base_provider.py         # Abstract base
      openai_compat_provider.py # Shared OpenAI-compatible base
      gemini_provider.py       # Google Gemini
      anthropic_provider.py    # Claude
      moonshot_provider.py     # Kimi
      ollama_provider.py       # Ollama local
    tools/
      tool_registry.py         # 65 tools (~1700 lines)
    interfaces/
      chat_server.py           # HTTP + SSE server
      chat_cli.py              # Terminal CLI
      mcp_server.py            # MCP stdio server
  launch/
    chat_server.launch.py
    mcp_server.launch.py
  config/
    agent_params.yaml
    robot_tester_prompt.txt
```

## Limitations

- **Single concurrent session** — the chat server uses a lock; only one chat request at a time
- **No vision tools yet** — camera image capture and object detection are planned
- **RosBridge is large** — `ros_bridge.py` (~1900 lines) handles too many concerns; future refactor should split it
- **No persistent conversation** — chat history resets on server restart
- **Ollama tool calling** — depends on model support; not all local models handle function calling well

## License

MIT
