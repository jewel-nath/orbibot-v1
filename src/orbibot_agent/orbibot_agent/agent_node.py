"""Main agent node for OrbiBot Agent.

Ties together LLM providers, tools, and ROS integration.
"""

import logging
import os
from typing import Any, Dict, Generator, List, Optional

import rclpy
from rclpy.node import Node
import yaml

from .core.ros_bridge import RosBridge
from .core.safety_manager import SafetyManager
from .tools.tool_registry import ToolRegistry

# LLM Providers
from .llm_providers.gemini_provider import GeminiProvider
from .llm_providers.anthropic_provider import AnthropicProvider
from .llm_providers.moonshot_provider import MoonshotProvider
from .llm_providers.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)

# Built-in RobotTester system prompt (used when no prompt_file is configured)
_ROBOT_TESTER_PROMPT = """You are OrbiBot RobotTester — a systematic hardware and software test engineer for the OrbiBot Mecanum-wheeled mobile robot.

BEHAVIOUR RULES:
1. Always state your test plan BEFORE calling any tools.
   Format: "Test plan: (1) <step>, (2) <step>, ..."

2. After EACH tool call, immediately report:
   - What was measured or what happened
   - PASS or FAIL with the specific reason
   - Expected vs actual values where applicable

3. For MOTOR/ENCODER tests: get_encoder_counts (baseline) → move_robot → get_encoder_counts (after) → compare delta.

4. For PID TUNING: get_firmware_state → run_pid_test → interpret MAE/overshoot → suggest new PID → set_motor_pid → run_pid_test again → compare.

5. For IMU/MAGNETOMETER: get_imu_data → check for NaN/extreme values. get_magnetometer_data → check heading consistency.

6. For BATTERY: get_battery_status → PASS if voltage > 10.5 V, FAIL otherwise.

7. For SLAM/NAV: slam_get_map_info → set_initial_pose → navigate_to_pose → report final pose vs target.

8. For FULL HARDWARE TEST: run_full_hardware_test → interpret each sub-result → list failures → suggest fixes.

9. END every test session with a SUMMARY TABLE:
   | Test | Result | Expected | Actual | Notes |
   |------|--------|----------|--------|-------|

STYLE: Be concise. Use bullet points. Never skip PASS/FAIL. Suggest fixes for failures.
SAFETY: Max linear 0.2 m/s for tests. Max duration 5 s per move. Call stop_robot on unexpected behaviour.
"""


class AgentNode(Node):
    """Main agent node managing LLM and tool interactions.

    Can be used standalone (creates its own ROS node) or embedded inside
    another node by passing ros_node and config_file.
    """

    def __init__(
        self,
        ros_node: Optional[Node] = None,
        config_file: str = '',
    ):
        """Initialize the agent.

        Args:
            ros_node: External ROS node for subscriptions/publishers.
                      If None, this instance acts as its own node.
            config_file: Path to YAML config file. When None, reads
                         from the 'config_file' ROS parameter.
        """
        if ros_node is None:
            # Standalone mode — this object IS the ROS node
            super().__init__('orbibot_agent')
            self.declare_parameter('config_file', '')
            self.declare_parameter('default_provider', 'gemini')
            config_file = self.get_parameter('config_file').value
            bridge_node = self
        else:
            # Embedded mode — use the caller's node for ROS I/O
            super().__init__('orbibot_agent_core')
            bridge_node = ros_node

        self._config = self._load_config(config_file)

        safety_cfg = self._config.get('safety', {})
        self._safety_manager = SafetyManager(
            max_linear_vel=safety_cfg.get('max_linear_vel'),
            max_angular_vel=safety_cfg.get('max_angular_vel'),
            max_duration=safety_cfg.get('max_duration'),
            sensor_timeout=safety_cfg.get('sensor_timeout'),
        )

        self._ros_bridge = RosBridge(bridge_node)
        self._ros_bridge.set_safety_manager(self._safety_manager)

        self._tool_registry = ToolRegistry(self._ros_bridge, self._safety_manager)

        self._providers: Dict[str, Any] = {}
        self._init_providers()

        self._current_provider = None
        self._current_provider_name: Optional[str] = None
        self._system_prompt = self._load_system_prompt()

        self.get_logger().info('OrbiBot Agent initialized')

    def _load_config(self, config_file: str) -> Dict:
        """Load config from YAML file, merged with defaults."""
        default_config = {
            'safety': {
                'max_linear_vel': 0.5,
                'max_angular_vel': 2.0,
                'max_duration': 10.0,
                'sensor_timeout': 3.0,
            },
            'llm_providers': {
                'gemini': {
                    'model': 'gemini-2.0-flash',
                    'api_key_env': 'GEMINI_API_KEY',
                },
                'anthropic': {
                    'model': 'claude-3-5-sonnet-20241022',
                    'api_key_env': 'ANTHROPIC_API_KEY',
                },
                'moonshot': {
                    'model': 'kimi-latest',
                    'api_key_env': 'MOONSHOT_API_KEY',
                },
                'ollama': {
                    'model': 'llama3.1:8b',
                    'base_url': 'http://localhost:11434/v1',
                },
            },
            'robot_tester': {
                'provider': 'anthropic',
                'model': 'claude-3-5-sonnet-20241022',
                'prompt_file': '',
            },
            'chat_server': {
                'max_workers': 2,
            },
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = yaml.safe_load(f)
                # Deep merge with defaults
                for key, value in user_config.items():
                    if isinstance(value, dict) and key in default_config and isinstance(default_config[key], dict):
                        default_config[key].update(value)
                    else:
                        default_config[key] = value
                self.get_logger().info(f'Loaded config from {config_file}')
            except Exception as e:
                self.get_logger().error(f'Failed to load config: {e}')

        return default_config

    def _init_providers(self) -> None:
        """Initialize all configured LLM providers."""
        providers_config = self._config.get('llm_providers', {})
        provider_classes = {
            'gemini': GeminiProvider,
            'anthropic': AnthropicProvider,
            'moonshot': MoonshotProvider,
            'ollama': OllamaProvider,
        }
        for name, cls in provider_classes.items():
            if name in providers_config:
                self._providers[name] = cls(providers_config[name])

        self.get_logger().info(f'Initialized {len(self._providers)} LLM providers')

    def _load_system_prompt(self) -> str:
        """Build the default chat system prompt."""
        return """You are OrbiBot, a helpful AI assistant for a Mecanum-wheeled ROS 2 mobile robot (Raspberry Pi 5 + Yahboom ROSMaster V3.0).

You can control the robot using natural language commands. Available capabilities:

MOTION
- Move the robot (forward, backward, turn, strafe with mecanum drive)
- stop_robot for emergency stop

SENSORS & SYSTEM
- Battery, IMU, magnetometer, encoder counts, joint states, odometry, LiDAR scan
- System enriched (CPU, RAM, temperature), safety status, full firmware snapshot
- Firmware version query

FIRMWARE CONFIGURATION (SET)
- Motor PID parameters (set + save persistently)
- Yaw PID parameters (set + save persistently)
- Magnetometer calibration (calibrate + set hard-iron offsets)
- Motor enable/disable, buzzer beep, odometry and encoder reset

HARDWARE TESTING
- Individual tests: motor, IMU, encoder, magnetometer, battery, beep
- Full hardware test suite (run_full_hardware_test)

SLAM MAPPING
- slam_save_map — save pose graph + pgm/yaml to disk
- slam_serialize_map — save pose graph only for localization reload
- slam_get_map_info — map size, resolution, explored percentage

NAVIGATION (Nav2)
- set_initial_pose — tell AMCL where the robot is on the map
- amcl_reinitialize — scatter AMCL particles globally when robot is completely lost
- navigate_to_pose — send robot to a target x,y,yaw
- navigate_through_poses — sequence of poses in one action
- follow_waypoints — patrol route through ordered waypoints
- nav_cancel — cancel all active navigation goals
- nav_clear_costmaps — clear local, global, or both costmaps
- nav_spin — in-place spin recovery action
- nav_backup — short reverse recovery action
- nav_get_plan — get current planned path info

AUTONOMOUS EXPLORATION
- exploration_start / stop / pause / resume
- get_exploration_status — current state (idle/exploring/navigating/complete/stopped)
- get_exploration_frontiers — unexplored frontier regions and their positions

ROS 2 INTERFACE
- ros2_topic_publish — publish to any topic (one-shot, for interfaces without dedicated tools)
- ros2_service_call — call any service with arbitrary fields
- ros2_send_action_goal — send any action goal
- ros2_action_request_result — poll active goal status
- list_topics, list_services, list_active_nodes, get_node_info

SAFETY CONSTRAINTS
- Maximum linear velocity: 0.5 m/s
- Maximum angular velocity: 2.0 rad/s
- Maximum movement duration: 10 seconds

Always explain what you are doing before calling tools. If a command is unsafe or unclear, ask for clarification before acting.
"""

    def _get_system_prompt(self, mode: str = 'chat') -> str:
        """Return system prompt for 'chat' or 'robot_tester' mode."""
        if mode == 'robot_tester':
            # Try to load from file first
            prompt_file = self._config.get('robot_tester', {}).get('prompt_file', '')
            if prompt_file and os.path.exists(prompt_file):
                try:
                    with open(prompt_file, 'r') as f:
                        return f.read()
                except Exception as e:
                    logger.warning(f'Failed to load robot_tester prompt file: {e}')
            # Fall back to built-in prompt
            return _ROBOT_TESTER_PROMPT
        return self._system_prompt

    def _get_provider_name_for_mode(self, mode: str) -> str:
        """Return provider name: robot_tester overrides default if configured."""
        if mode == 'robot_tester':
            tester_cfg = self._config.get('robot_tester', {})
            provider = tester_cfg.get('provider', '')
            if provider and provider in self._providers:
                return provider
        return self._config.get('default_provider', 'gemini')

    def get_available_providers(self) -> List[str]:
        return [name for name, provider in self._providers.items() if provider.is_available()]

    def set_provider(self, provider_name: str, system_prompt: Optional[str] = None) -> bool:
        """Activate a provider by name. Returns True on success."""
        if provider_name not in self._providers:
            self.get_logger().error(f'Unknown provider: {provider_name}')
            return False

        provider = self._providers[provider_name]
        if not provider.is_available():
            self.get_logger().error(f'Provider {provider_name} is not available')
            return False

        self._current_provider = provider
        self._current_provider_name = provider_name
        prompt = system_prompt if system_prompt is not None else self._system_prompt
        self._current_provider.start_chat(prompt)
        self._current_provider.set_tools(self._tool_registry.get_tool_schemas())

        self.get_logger().info(f'Switched to provider: {provider_name}')
        return True

    def process_message(self, message: str, mode: str = 'chat') -> Dict[str, Any]:
        """Process a user message.

        Args:
            message: User message
            mode: 'chat' (default) or 'robot_tester'

        Returns:
            Response dictionary with 'text' and 'tool_calls'
        """
        provider_name = self._get_provider_name_for_mode(mode)
        system_prompt = self._get_system_prompt(mode)

        # Switch provider or re-init if mode changed
        if not self._current_provider or self._current_provider_name != provider_name:
            if not self.set_provider(provider_name, system_prompt):
                return {
                    'text': f'Error: No LLM provider available. Tried {provider_name}',
                    'tool_calls': []
                }
        else:
            # Same provider but may need different system prompt for mode
            # Re-start chat with new prompt if mode differs from last call
            self._current_provider.start_chat(system_prompt)
            self._current_provider.set_tools(self._tool_registry.get_tool_schemas())

        # Send message to LLM
        response = self._current_provider.send_message(message)

        # Handle tool calls
        max_iterations = 10
        iteration = 0

        while response.get('tool_calls') and iteration < max_iterations:
            iteration += 1
            tool_results = []

            for tool_call in response['tool_calls']:
                tool_name = tool_call['name']
                tool_args = tool_call['arguments']
                tool_use_id = tool_call.get('tool_use_id', 'unknown')

                self.get_logger().info(f'Executing tool: {tool_name}')

                # Execute tool
                result = self._tool_registry.execute_tool(tool_name, tool_args)
                tool_results.append({
                    'name': tool_name,
                    'result': result,
                    'tool_use_id': tool_use_id,
                })

            # Send results back to LLM
            response = self._current_provider.send_tool_results(tool_results)

        return response

    def process_message_stream(
        self,
        message: str,
        mode: str = 'chat',
    ) -> Generator[Dict[str, Any], None, None]:
        """Process a user message and yield SSE event dicts as the agent works.

        This is the streaming version of process_message(). It yields events
        that the chat server can forward to the client as Server-Sent Events.

        Event types yielded:
          {'event': 'text_chunk', 'content': '...'}
          {'event': 'tool_start', 'name': '...', 'args': {...}}
          {'event': 'tool_result', 'name': '...', 'result': {...}}
          {'event': 'done', 'tool_calls': [...]}
          {'event': 'error', 'message': '...'}

        Args:
            message: User message
            mode: 'chat' or 'robot_tester'

        Yields:
            SSE event dicts
        """
        provider_name = self._get_provider_name_for_mode(mode)
        system_prompt = self._get_system_prompt(mode)

        # Switch provider or re-init if needed
        if not self._current_provider or self._current_provider_name != provider_name:
            if not self.set_provider(provider_name, system_prompt):
                yield {'event': 'error', 'message': f'No LLM provider available. Tried {provider_name}'}
                return
        else:
            self._current_provider.start_chat(system_prompt)
            self._current_provider.set_tools(self._tool_registry.get_tool_schemas())

        all_tool_calls = []
        max_iterations = 10
        iteration = 0

        try:
            # First streaming call
            pending_tool_calls = []
            for chunk in self._current_provider.send_message_stream(message):
                if chunk.get('type') == 'text':
                    yield {'event': 'text_chunk', 'content': chunk['content']}
                elif chunk.get('type') == 'tool_calls':
                    pending_tool_calls = chunk['tool_calls']

            # Tool call loop
            while pending_tool_calls and iteration < max_iterations:
                iteration += 1
                tool_results = []

                for tc in pending_tool_calls:
                    tool_name = tc['name']
                    tool_args = tc.get('arguments', {})
                    tool_use_id = tc.get('tool_use_id', tc.get('tool_call_id', 'unknown'))

                    yield {'event': 'tool_start', 'name': tool_name, 'args': tool_args}

                    self.get_logger().info(f'Executing tool (stream): {tool_name}')
                    result = self._tool_registry.execute_tool(tool_name, tool_args)

                    yield {'event': 'tool_result', 'name': tool_name, 'result': result}

                    tool_results.append({
                        'name': tool_name,
                        'result': result,
                        'tool_use_id': tool_use_id,
                        'tool_call_id': tool_use_id,
                    })
                    all_tool_calls.append({'tool': tool_name, 'args': tool_args, 'result': result})

                # Stream next LLM response after tool results
                pending_tool_calls = []
                for chunk in self._current_provider.send_tool_results_stream(tool_results):
                    if chunk.get('type') == 'text':
                        yield {'event': 'text_chunk', 'content': chunk['content']}
                    elif chunk.get('type') == 'tool_calls':
                        pending_tool_calls = chunk['tool_calls']

            yield {'event': 'done', 'tool_calls': all_tool_calls}

        except Exception as e:
            logger.error(f'process_message_stream failed: {e}')
            yield {'event': 'error', 'message': str(e)}

    # -- Public properties (avoid direct _private access from interfaces) --

    @property
    def current_provider_name(self) -> Optional[str]:
        return self._current_provider_name

    @property
    def config(self) -> Dict:
        return self._config

    @property
    def system_prompt(self) -> str:
        return self._system_prompt

    @property
    def tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    @property
    def current_provider(self):
        return self._current_provider

    def reset_chat(self) -> None:
        """Reset the current chat session."""
        if self._current_provider:
            self._current_provider.start_chat(self._system_prompt)


def main(args=None):
    """Main entry point."""
    from .env_loader import load_dotenv_local
    load_dotenv_local()
    rclpy.init(args=args)

    node = AgentNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
