"""HTTP Chat Server for OrbiBot Agent.

Provides REST API for web GUI integration.
"""

import asyncio
import json
import logging
import threading
from typing import Any, Dict

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor

from aiohttp import web
import aiohttp_cors

from ..agent_node import AgentNode
from ..env_loader import load_dotenv_local

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8082


class ChatServerNode(Node):
    """ROS node with HTTP chat API."""

    def __init__(self):
        super().__init__('orbibot_chat_server')

        self.declare_parameter('port', DEFAULT_PORT)
        self.declare_parameter('config_file', '')
        self._port = self.get_parameter('port').value
        config_file = self.get_parameter('config_file').value

        # Initialize agent components
        self._agent = AgentNode.__new__(AgentNode)
        Node.__init__(self._agent, 'chat_agent')
        self._agent._config = self._agent._load_config(config_file or '')
        from ..core.safety_manager import SafetyManager
        from ..core.ros_bridge import RosBridge
        from ..tools.tool_registry import ToolRegistry
        safety_cfg = self._agent._config.get('safety', {})
        self._agent._safety_manager = SafetyManager(
            max_linear_vel=safety_cfg.get('max_linear_vel'),
            max_angular_vel=safety_cfg.get('max_angular_vel'),
            max_duration=safety_cfg.get('max_duration'),
            sensor_timeout=safety_cfg.get('sensor_timeout'),
        )
        self._agent._ros_bridge = RosBridge(self)
        self._agent._ros_bridge.set_safety_manager(self._agent._safety_manager)
        self._agent._tool_registry = ToolRegistry(self._agent._ros_bridge, self._agent._safety_manager)
        self._agent._providers = {}
        self._agent._init_providers()
        self._agent._system_prompt = self._agent._load_system_prompt()
        self._agent._current_provider = None

        # Chat lock for concurrent requests
        self._chat_lock = asyncio.Lock()

        self.get_logger().info(f'Chat server starting on port {self._port}')

    def _process_message_sync(self, message: str, provider: str = None) -> Dict[str, Any]:
        """Process message synchronously.

        Args:
            message: User message
            provider: Optional provider override

        Returns:
            Response dictionary
        """
        # Set provider if specified
        if provider and provider != self._agent._current_provider:
            if not self._agent.set_provider(provider):
                available = self._agent.get_available_providers()
                return {
                    'reply': f'Provider {provider} not available. Available: {available}',
                    'tool_calls': []
                }

        # Use default if no provider set (from config or fallback to gemini)
        if not self._agent._current_provider:
            default = self._agent._config.get('default_provider', 'gemini')
            if not self._agent.set_provider(default):
                return {
                    'reply': 'No LLM provider available. Set API key.',
                    'tool_calls': []
                }

        # Process message
        response = self._agent.process_message(message)

        return {
            'reply': response.get('text', 'No response'),
            'tool_calls': response.get('tool_calls', [])
        }

    async def handle_chat(self, request: web.Request) -> web.Response:
        """Handle chat request."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({'error': 'Invalid JSON'}, status=400)

        message = body.get('message', '').strip()
        provider = body.get('provider', None)

        if not message:
            return web.json_response({'error': 'Empty message'}, status=400)

        async with self._chat_lock:
            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(
                    None, self._process_message_sync, message, provider
                )
            except Exception as exc:
                logger.error(f'Chat request failed: {exc}')
                return web.json_response(
                    {'reply': f'Error: {exc}', 'tool_calls': []},
                    status=500
                )

        return web.json_response(result)

    async def handle_reset(self, request: web.Request) -> web.Response:
        """Reset chat session."""
        if self._agent._current_provider:
            self._agent._current_provider.start_chat(self._agent._system_prompt)
        return web.json_response({'status': 'ok'})

    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check."""
        providers = self._agent.get_available_providers()
        return web.json_response({
            'status': 'ok',
            'available_providers': providers,
            'current_provider': self._agent._current_provider.name if self._agent._current_provider else None
        })

    async def handle_providers(self, request: web.Request) -> web.Response:
        """Get available providers."""
        providers = self._agent.get_available_providers()
        return web.json_response({
            'providers': providers,
            'current': self._agent._current_provider.name if self._agent._current_provider else None
        })

    def build_app(self) -> web.Application:
        """Build aiohttp app."""
        app = web.Application()

        # CORS
        cors = aiohttp_cors.setup(app, defaults={
            '*': aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers='*',
                allow_headers='*',
                allow_methods='*',
            )
        })

        # Routes
        cors.add(app.router.add_post('/api/chat', self.handle_chat))
        cors.add(app.router.add_post('/api/reset', self.handle_reset))
        cors.add(app.router.add_get('/api/health', self.handle_health))
        cors.add(app.router.add_get('/api/providers', self.handle_providers))

        return app


def main(args=None):
    """Main entry point."""
    load_dotenv_local()
    rclpy.init(args=args)

    node = ChatServerNode()

    # Spin ROS in background
    ros_executor = MultiThreadedExecutor()
    ros_executor.add_node(node)
    ros_executor.add_node(node._agent)
    spin_thread = threading.Thread(target=ros_executor.spin, daemon=True)
    spin_thread.start()

    # Run HTTP server
    app = node.build_app()
    try:
        web.run_app(app, host='0.0.0.0', port=node._port, print=lambda _: None)
    except KeyboardInterrupt:
        pass
    finally:
        node.get_logger().info('Chat server shutting down')
        node.destroy_node()
        node._agent.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()