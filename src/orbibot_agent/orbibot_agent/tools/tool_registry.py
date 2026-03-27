"""Tool registry for OrbiBot Agent.

Thin dispatcher that registers tools from focused modules and
provides schema/execution access for the LLM providers.
"""

import logging
from typing import Any, Callable, Dict, List

from ..core.ros_bridge import RosBridge
from ..core.safety_manager import SafetyManager

from . import (
    motion_tools,
    sensor_tools,
    firmware_tools,
    ros_tools,
    navigation_tools,
    diagnostics_tools,
    analysis_tools,
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Registry for all robot tools.

    Each tool module provides a register(registry, ros_bridge, safety_manager)
    function that calls registry.register_tool() for each tool it defines.
    """

    def __init__(self, ros_bridge: RosBridge, safety_manager: SafetyManager):
        self._ros_bridge = ros_bridge
        self._safety_manager = safety_manager
        self._tools: Dict[str, Dict] = {}
        self._handlers: Dict[str, Callable] = {}

        self._register_all_tools()

    def _register_all_tools(self) -> None:
        """Register tools from all modules."""
        modules = [
            motion_tools,
            sensor_tools,
            firmware_tools,
            ros_tools,
            navigation_tools,
            diagnostics_tools,
            analysis_tools,
        ]
        for mod in modules:
            mod.register(self, self._ros_bridge, self._safety_manager)

        logger.info(f'Registered {len(self._tools)} tools')

    def register_tool(
        self,
        name: str,
        description: str,
        parameters: Dict,
        handler: Callable,
    ) -> None:
        """Register a single tool."""
        self._tools[name] = {
            'type': 'function',
            'function': {
                'name': name,
                'description': description,
                'parameters': parameters,
            },
        }
        self._handlers[name] = handler

    def get_tool_schemas(self) -> List[Dict]:
        """Get all tool schemas for LLM function calling."""
        return list(self._tools.values())

    def execute_tool(self, name: str, arguments: Dict) -> Dict:
        """Execute a tool by name."""
        if name not in self._handlers:
            return {'error': f'Unknown tool: {name}'}
        try:
            return self._handlers[name](**arguments)
        except Exception as e:
            logger.error(f'Tool {name} execution failed: {e}')
            return {'error': str(e)}
