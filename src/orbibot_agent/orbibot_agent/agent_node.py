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

# Default system prompt path (relative to this package's config directory)
_DEFAULT_PROMPT_FILE = os.path.join(
    os.path.dirname(__file__), '..', 'config', 'system_prompt.txt'
)

# Built-in fallback prompt if system_prompt.txt is missing
_FALLBACK_PROMPT = """You are OrbiBot, an AI assistant for a Mecanum-wheeled ROS 2 mobile robot.
You can control the robot, read sensors, run tests, and diagnose problems through natural conversation.
Always explain what you are doing before calling tools. If a command is unsafe or unclear, ask for clarification.
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
        """Load system prompt from config/system_prompt.txt, fallback to built-in."""
        prompt_path = os.path.normpath(_DEFAULT_PROMPT_FILE)
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, 'r') as f:
                    return f.read()
            except Exception as e:
                self.get_logger().warning(f'Failed to load system_prompt.txt: {e}')
        return _FALLBACK_PROMPT

    def get_available_providers(self) -> List[str]:
        return [name for name, provider in self._providers.items() if provider.is_available()]

    def set_provider(self, provider_name: str) -> bool:
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
        self._current_provider.start_chat(self._system_prompt)
        self._current_provider.set_tools(self._tool_registry.get_tool_schemas())

        self.get_logger().info(f'Switched to provider: {provider_name}')
        return True

    def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message.

        Args:
            message: User message

        Returns:
            Response dictionary with 'text' and 'tool_calls'
        """
        provider_name = self._config.get('default_provider', 'gemini')

        # Switch provider or re-init if needed
        if not self._current_provider or self._current_provider_name != provider_name:
            if not self.set_provider(provider_name):
                return {
                    'text': f'Error: No LLM provider available. Tried {provider_name}',
                    'tool_calls': []
                }
        else:
            self._current_provider.start_chat(self._system_prompt)
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

                result = self._tool_registry.execute_tool(tool_name, tool_args)
                tool_results.append({
                    'name': tool_name,
                    'result': result,
                    'tool_use_id': tool_use_id,
                })

            response = self._current_provider.send_tool_results(tool_results)

        return response

    def process_message_stream(
        self,
        message: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """Process a user message and yield SSE event dicts as the agent works.

        Event types yielded:
          {'event': 'text_chunk', 'content': '...'}
          {'event': 'tool_start', 'name': '...', 'args': {...}}
          {'event': 'tool_result', 'name': '...', 'result': {...}}
          {'event': 'done', 'tool_calls': [...]}
          {'event': 'error', 'message': '...'}

        Args:
            message: User message

        Yields:
            SSE event dicts
        """
        provider_name = self._config.get('default_provider', 'gemini')

        # Switch provider or re-init if needed
        if not self._current_provider or self._current_provider_name != provider_name:
            if not self.set_provider(provider_name):
                yield {'event': 'error', 'message': f'No LLM provider available. Tried {provider_name}'}
                return
        else:
            self._current_provider.start_chat(self._system_prompt)
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

    # -- Public properties --

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
