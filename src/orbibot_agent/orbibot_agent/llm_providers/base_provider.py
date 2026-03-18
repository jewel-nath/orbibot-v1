"""Base LLM provider interface for OrbiBot Agent."""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Generator, List, Optional


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize provider with configuration.

        Args:
            config: Provider configuration dictionary
        """
        self.config = config
        self.name = config.get('name', 'unknown')
        self.model = config.get('model', 'unknown')

    def _get_api_key(self, env_var: str) -> str:
        """Get API key from the environment variable set by .env.local or shell export.

        Args:
            env_var: Name of the environment variable (e.g. 'GEMINI_API_KEY').

        Returns:
            API key string, or empty string if not set.
        """
        return os.environ.get(env_var, '').strip()

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the provider (load API keys, etc.).

        Returns:
            True if initialization successful
        """
        pass

    @abstractmethod
    def send_message(
        self,
        message: str,
        tools: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a message to the LLM.

        Args:
            message: User message
            tools: Optional list of tool definitions
            system_prompt: Optional system prompt

        Returns:
            Response dictionary with 'text' and optional 'tool_calls'
        """
        pass

    @abstractmethod
    def send_tool_results(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Send tool execution results back to LLM.

        Args:
            tool_results: List of tool result dictionaries

        Returns:
            Response dictionary with 'text'
        """
        pass

    @abstractmethod
    def start_chat(self, system_prompt: Optional[str] = None) -> None:
        """Start a new chat session.

        Args:
            system_prompt: Optional system prompt for the session
        """
        pass

    def send_message_stream(
        self,
        message: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream LLM response as event chunks.

        Yields dicts with 'type' key:
          - {'type': 'text', 'content': '...'} — text token chunk
          - {'type': 'tool_calls', 'tool_calls': [...]} — tool call batch

        Default implementation falls back to non-streaming send_message().
        Override in subclasses for true streaming.

        Args:
            message: User message

        Yields:
            Event dicts
        """
        response = self.send_message(message)
        if response.get('tool_calls'):
            yield {'type': 'tool_calls', 'tool_calls': response['tool_calls']}
        if response.get('text'):
            yield {'type': 'text', 'content': response['text']}

    def send_tool_results_stream(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream LLM response after tool results.

        Default implementation falls back to non-streaming send_tool_results().
        Override in subclasses for true streaming.

        Args:
            tool_results: List of tool result dictionaries

        Yields:
            Event dicts (same format as send_message_stream)
        """
        response = self.send_tool_results(tool_results)
        if response.get('tool_calls'):
            yield {'type': 'tool_calls', 'tool_calls': response['tool_calls']}
        if response.get('text'):
            yield {'type': 'text', 'content': response['text']}

    def inject_history(self, messages: List[Dict[str, str]]) -> None:
        """Inject conversation history into the current session.

        Called when the client sends previous messages for context recovery.
        Default implementation is a no-op; override in stateful providers.

        Args:
            messages: List of {'role': 'user'|'assistant', 'content': str}
        """
        pass

    def is_available(self) -> bool:
        """Check if provider is available (API key set, etc.).

        Returns:
            True if provider can be used
        """
        return True

    def get_tool_schema(self, name: str, description: str, parameters: Dict) -> Dict:
        """Create a tool schema for this provider.

        Args:
            name: Tool name
            description: Tool description
            parameters: Tool parameters schema

        Returns:
            Provider-specific tool schema
        """
        # Default OpenAI-compatible schema
        return {
            'type': 'function',
            'function': {
                'name': name,
                'description': description,
                'parameters': parameters,
            }
        }
