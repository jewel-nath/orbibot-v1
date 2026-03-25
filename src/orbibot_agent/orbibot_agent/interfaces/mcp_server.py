"""MCP Server for OrbiBot Agent.

Provides Model Context Protocol interface for Claude Desktop, Cline, etc.
"""

import asyncio
import json
import logging
import sys
from typing import Any, List, Optional

import rclpy

try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent
    from mcp.server.stdio import stdio_server
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

from ..agent_node import AgentNode
from ..env_loader import load_dotenv_local

logger = logging.getLogger(__name__)


class McpServerNode:
    """MCP server node for OrbiBot Agent."""

    def __init__(self):
        self._node = None
        self._agent = None
        self._server = Server("orbibot-agent")
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP handlers."""

        @self._server.list_tools()
        async def list_tools() -> List[Tool]:
            """List available tools."""
            if not self._agent:
                return []

            tools = self._agent.tool_registry.get_tool_schemas()
            mcp_tools = []

            for tool in tools:
                func = tool.get('function', {})
                mcp_tools.append(Tool(
                    name=func.get('name', 'unknown'),
                    description=func.get('description', ''),
                    inputSchema=func.get('parameters', {'type': 'object'})
                ))

            return mcp_tools

        @self._server.call_tool()
        async def call_tool(name: str, arguments: Any) -> List[TextContent]:
            """Execute a tool."""
            if not self._agent:
                return [TextContent(
                    type="text",
                    text=json.dumps({'error': 'Agent not initialized'})
                )]

            try:
                # Run tool in thread pool so the event loop keeps running and
                # _spin_ros can process ROS callbacks (e.g. wait_for_message in
                # get_odometry / get_battery / get_imu would otherwise block and
                # prevent spin_once from running, causing timeouts).
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: self._agent.tool_registry.execute_tool(name, arguments or {}),
                )
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
            except Exception as e:
                return [TextContent(
                    type="text",
                    text=json.dumps({'error': str(e)})
                )]

    def initialize(self) -> bool:
        """Initialize ROS node and agent."""
        if not MCP_AVAILABLE:
            logger.error('MCP SDK not installed. Install with: pip install mcp')
            return False

        load_dotenv_local()
        rclpy.init()

        # Create ROS node — used for subscriptions/publishers
        self._node = rclpy.create_node('orbibot_mcp_server')

        # Agent uses the MCP node for ROS I/O
        self._agent = AgentNode(ros_node=self._node)

        # Set default provider
        available = self._agent.get_available_providers()
        if available:
            self._agent.set_provider(available[0])

        logger.info(f'MCP server initialized. Available providers: {available}')
        return True

    async def run(self):
        """Run MCP server."""
        if not MCP_AVAILABLE:
            print("ERROR: MCP SDK not installed", file=sys.stderr)
            return

        # Spin ROS in background
        loop = asyncio.get_event_loop()
        ros_task = loop.create_task(self._spin_ros())

        try:
            async with stdio_server() as (read_stream, write_stream):
                await self._server.run(
                    read_stream,
                    write_stream,
                    self._server.create_initialization_options()
                )
        finally:
            ros_task.cancel()
            try:
                await ros_task
            except asyncio.CancelledError:
                pass

            if self._node:
                self._node.destroy_node()
            if self._agent:
                self._agent.destroy_node()
            rclpy.shutdown()

    async def _spin_ros(self):
        """Spin ROS node."""
        while rclpy.ok():
            rclpy.spin_once(self._node, timeout_sec=0.05)
            await asyncio.sleep(0.01)


def main():
    """Main entry point."""
    logging.basicConfig(level=logging.INFO)

    server = McpServerNode()
    if not server.initialize():
        sys.exit(1)

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\nShutting down MCP server...")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()