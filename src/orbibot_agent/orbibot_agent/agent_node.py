"""Main agent node for OrbiBot Agent.

Ties together LLM providers, tools, and ROS integration.
"""

import logging
import os
from typing import Any, Dict, List, Optional

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


class AgentNode(Node):
    """Main agent node managing LLM and tool interactions."""

    def __init__(self):
        super().__init__('orbibot_agent')

        # Declare parameters
        self.declare_parameter('config_file', '')
        self.declare_parameter('default_provider', 'gemini')

        # Load configuration
        config_file = self.get_parameter('config_file').value
        self._config = self._load_config(config_file)

        # Initialize core components
        self._safety_manager = SafetyManager(
            max_linear_vel=self._config.get('safety', {}).get('max_linear_vel'),
            max_angular_vel=self._config.get('safety', {}).get('max_angular_vel'),
            max_duration=self._config.get('safety', {}).get('max_duration'),
            sensor_timeout=self._config.get('safety', {}).get('sensor_timeout'),
        )

        self._ros_bridge = RosBridge(self)
        self._ros_bridge.set_safety_manager(self._safety_manager)

        self._tool_registry = ToolRegistry(self._ros_bridge, self._safety_manager)

        # Initialize LLM providers
        self._providers: Dict[str, Any] = {}
        self._init_providers()

        self._current_provider = None
        self._system_prompt = self._load_system_prompt()

        self.get_logger().info('OrbiBot Agent node initialized')

    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file.

        Args:
            config_file: Path to config file

        Returns:
            Configuration dictionary
        """
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
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = yaml.safe_load(f)
                # Merge with defaults
                default_config.update(user_config)
                self.get_logger().info(f'Loaded config from {config_file}')
            except Exception as e:
                self.get_logger().error(f'Failed to load config: {e}')

        return default_config

    def _init_providers(self) -> None:
        """Initialize all LLM providers."""
        providers_config = self._config.get('llm_providers', {})

        # Gemini
        if 'gemini' in providers_config:
            self._providers['gemini'] = GeminiProvider(providers_config['gemini'])

        # Anthropic
        if 'anthropic' in providers_config:
            self._providers['anthropic'] = AnthropicProvider(providers_config['anthropic'])

        # Moonshot
        if 'moonshot' in providers_config:
            self._providers['moonshot'] = MoonshotProvider(providers_config['moonshot'])

        # Ollama
        if 'ollama' in providers_config:
            self._providers['ollama'] = OllamaProvider(providers_config['ollama'])

        self.get_logger().info(f'Initialized {len(self._providers)} LLM providers')

    def _load_system_prompt(self) -> str:
        """Load system prompt for the agent.

        Returns:
            System prompt string
        """
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

    def get_available_providers(self) -> List[str]:
        """Get list of available providers.

        Returns:
            List of provider names
        """
        return [name for name, provider in self._providers.items() if provider.is_available()]

    def set_provider(self, provider_name: str) -> bool:
        """Set the active LLM provider.

        Args:
            provider_name: Name of the provider

        Returns:
            True if successful
        """
        if provider_name not in self._providers:
            self.get_logger().error(f'Unknown provider: {provider_name}')
            return False

        provider = self._providers[provider_name]
        if not provider.is_available():
            self.get_logger().error(f'Provider {provider_name} is not available')
            return False

        self._current_provider = provider
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
        if not self._current_provider:
            default_provider = self.get_parameter('default_provider').value
            if not self.set_provider(default_provider):
                return {
                    'text': f'Error: No LLM provider available. Tried {default_provider}',
                    'tool_calls': []
                }

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

    def get_safety_manager(self) -> SafetyManager:
        """Get safety manager.

        Returns:
            SafetyManager instance
        """
        return self._safety_manager

    def get_ros_bridge(self) -> RosBridge:
        """Get ROS bridge.

        Returns:
            RosBridge instance
        """
        return self._ros_bridge

    def get_tool_registry(self) -> ToolRegistry:
        """Get tool registry.

        Returns:
            ToolRegistry instance
        """
        return self._tool_registry


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