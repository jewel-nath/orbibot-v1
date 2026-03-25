"""HTTP Chat Server for OrbiBot Agent.

Provides REST API for web GUI integration.

Endpoints:
  POST /api/chat          — blocking JSON response (backward-compatible)
  POST /api/chat/stream   — Server-Sent Events stream (new)
  POST /api/reset         — reset chat session
  POST /api/run_test_suite — run structured hardware tests (no LLM)
  GET  /api/health        — health check
  GET  /api/providers     — list available providers
"""

import asyncio
import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import rclpy
from rclpy.node import Node
from rclpy.executors import MultiThreadedExecutor  # noqa: F401 — used in main()

from aiohttp import web
import aiohttp_cors

from ..agent_node import AgentNode
from ..core.test_suite_runner import TestSuiteRunner
from ..env_loader import load_dotenv_local

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8082
DEFAULT_MAX_WORKERS = 2


class ChatServerNode(Node):
    """ROS node with HTTP chat API."""

    def __init__(self):
        super().__init__('orbibot_chat_server')

        self.declare_parameter('port', DEFAULT_PORT)
        self.declare_parameter('config_file', '')
        self._port = self.get_parameter('port').value
        config_file = self.get_parameter('config_file').value

        # Agent uses this node's subscriptions/publishers via ros_node param
        self._agent = AgentNode(ros_node=self, config_file=config_file or '')

        # Dedicated thread pool for chat work (Phase 4)
        max_workers = self._agent._config.get('chat_server', {}).get('max_workers', DEFAULT_MAX_WORKERS)
        self._chat_executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix='orbibot_chat',
        )

        # Test suite runner (Phase 6)
        self._test_suite_runner = TestSuiteRunner(self._agent._tool_registry)

        # Chat lock for concurrent requests
        self._chat_lock = asyncio.Lock()

        self.get_logger().info(f'Chat server starting on port {self._port}')

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_message_sync(
        self,
        message: str,
        provider: Optional[str] = None,
        mode: str = 'chat',
        client_history: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """Process message synchronously (runs in thread pool).

        Args:
            message: User message
            provider: Optional provider override
            mode: 'chat' or 'robot_tester'
            client_history: Optional list of previous messages from client

        Returns:
            Response dictionary
        """
        # Override provider if requested
        if provider and provider != self._agent._current_provider_name:
            if not self._agent.set_provider(provider):
                available = self._agent.get_available_providers()
                return {
                    'reply': f'Provider {provider} not available. Available: {available}',
                    'tool_calls': []
                }

        # Inject client history if provided (Phase 7)
        if client_history and self._agent._current_provider:
            self._agent._current_provider.inject_history(client_history)

        # Process message with mode support (Phase 5)
        response = self._agent.process_message(message, mode=mode)

        return {
            'reply': response.get('text', 'No response'),
            'tool_calls': response.get('tool_calls', [])
        }

    # ------------------------------------------------------------------
    # HTTP handlers
    # ------------------------------------------------------------------

    async def handle_chat(self, request: web.Request) -> web.Response:
        """Handle blocking chat request (backward-compatible)."""
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.json_response({'error': 'Invalid JSON'}, status=400)

        message = body.get('message', '').strip()
        provider = body.get('provider', None)
        mode = body.get('mode', 'chat')                    # Phase 5
        client_history = body.get('messages', None)        # Phase 7

        if not message:
            return web.json_response({'error': 'Empty message'}, status=400)

        async with self._chat_lock:
            loop = asyncio.get_event_loop()
            try:
                result = await loop.run_in_executor(
                    self._chat_executor,                   # Phase 4
                    self._process_message_sync,
                    message, provider, mode, client_history
                )
            except Exception as exc:
                logger.error(f'Chat request failed: {exc}')
                return web.json_response(
                    {'reply': f'Error: {exc}', 'tool_calls': []},
                    status=500
                )

        return web.json_response(result)

    async def handle_chat_stream(self, request: web.Request) -> web.StreamResponse:
        """Handle streaming chat request via Server-Sent Events (Phase 1).

        The client should read the response body as a stream of SSE events.
        Each event is a JSON object on a line prefixed with 'data: '.

        Event types:
          {'event': 'text_chunk', 'content': '...'}
          {'event': 'tool_start', 'name': '...', 'args': {...}}
          {'event': 'tool_result', 'name': '...', 'result': {...}}
          {'event': 'done', 'tool_calls': [...]}
          {'event': 'error', 'message': '...'}
        """
        try:
            body = await request.json()
        except json.JSONDecodeError:
            return web.Response(text='Invalid JSON', status=400)

        message = body.get('message', '').strip()
        provider = body.get('provider', None)
        mode = body.get('mode', 'chat')
        client_history = body.get('messages', None)

        if not message:
            return web.Response(text='Empty message', status=400)

        # Prepare SSE response
        resp = web.StreamResponse(headers={
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Access-Control-Allow-Origin': '*',
        })
        await resp.prepare(request)

        async def send_event(data: dict) -> None:
            try:
                await resp.write(f'data: {json.dumps(data)}\n\n'.encode('utf-8'))
            except Exception:
                pass

        loop = asyncio.get_event_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def run_stream() -> None:
            """Run process_message_stream in thread pool and push events to queue."""
            try:
                # Set provider if requested
                if provider and provider != self._agent._current_provider_name:
                    self._agent.set_provider(provider)

                # Inject client history
                if client_history and self._agent._current_provider:
                    self._agent._current_provider.inject_history(client_history)

                for event in self._agent.process_message_stream(message, mode=mode):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception as e:
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {'event': 'error', 'message': str(e)}
                )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)  # sentinel

        async with self._chat_lock:
            loop.run_in_executor(self._chat_executor, run_stream)

            while True:
                event = await queue.get()
                if event is None:
                    break
                await send_event(event)

        try:
            await resp.write_eof()
        except Exception:
            pass
        return resp

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
            'current_provider': self._agent._current_provider_name,
        })

    async def handle_providers(self, request: web.Request) -> web.Response:
        """Get available providers (Phase 3)."""
        providers = self._agent.get_available_providers()
        return web.json_response({
            'providers': providers,
            'current': self._agent._current_provider_name,
        })

    async def handle_run_test_suite(self, request: web.Request) -> web.Response:
        """Run structured hardware test suite without LLM (Phase 6).

        Optionally accepts a JSON body with:
          {'tests': ['battery_test', 'imu_test', ...]}  — run selected tests only
          {}  — run all tests

        Returns:
          {'status': 'ok', 'report': {...}}
        """
        try:
            body = await request.json()
        except Exception:
            body = {}

        selected_tests = body.get('tests', None)

        loop = asyncio.get_event_loop()
        try:
            if selected_tests:
                report = await loop.run_in_executor(
                    self._chat_executor,
                    self._test_suite_runner.run_selected,
                    selected_tests,
                )
            else:
                report = await loop.run_in_executor(
                    self._chat_executor,
                    self._test_suite_runner.run_all,
                )
            return web.json_response({'status': 'ok', 'report': report})
        except Exception as exc:
            logger.error(f'Test suite failed: {exc}')
            return web.json_response(
                {'status': 'error', 'message': str(exc)},
                status=500
            )

    # ------------------------------------------------------------------
    # App builder
    # ------------------------------------------------------------------

    def build_app(self) -> web.Application:
        """Build aiohttp app with all routes."""
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
        cors.add(app.router.add_post('/api/chat/stream', self.handle_chat_stream))   # Phase 1
        cors.add(app.router.add_post('/api/reset', self.handle_reset))
        cors.add(app.router.add_post('/api/run_test_suite', self.handle_run_test_suite))  # Phase 6
        cors.add(app.router.add_get('/api/health', self.handle_health))
        cors.add(app.router.add_get('/api/providers', self.handle_providers))        # Phase 3

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
        node._chat_executor.shutdown(wait=False)
        node.destroy_node()
        node._agent.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
