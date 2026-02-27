"""Ollama local LLM provider for OrbiBot Agent."""

import logging
import os
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'llama3.1:8b'
DEFAULT_BASE_URL = 'http://localhost:11434/v1'


class OllamaProvider(BaseLLMProvider):
    """Ollama local LLM provider with tool calling support."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Ollama provider.

        Args:
            config: Provider configuration with 'model', 'base_url'
        """
        super().__init__(config)
        self.model_name = config.get('model', DEFAULT_MODEL)
        self.base_url = config.get('base_url', DEFAULT_BASE_URL)
        self._client = None
        self._messages = []
        self._system_prompt = None
        self._tools = None

    def initialize(self) -> bool:
        """Initialize Ollama client.

        Returns:
            True if successful
        """
        if not OLLAMA_AVAILABLE:
            logger.error('openai not installed. Install with: pip install openai')
            return False

        try:
            self._client = OpenAI(
                api_key='ollama',  # Ollama doesn't need a real API key
                base_url=self.base_url,
            )
            logger.info(f'Ollama provider initialized with model: {self.model_name}')
            return True
        except Exception as e:
            logger.error(f'Failed to initialize Ollama: {e}')
            return False

    def is_available(self) -> bool:
        """Check if Ollama is available.

        Returns:
            True if Ollama server is reachable
        """
        if not OLLAMA_AVAILABLE or not self._client:
            return False

        try:
            # Try a simple request to check if server is up
            self._client.models.list()
            return True
        except Exception:
            return False

    def start_chat(self, system_prompt: Optional[str] = None) -> None:
        """Start a new chat session.

        Args:
            system_prompt: System instruction for the chat
        """
        if not self._client:
            if not self.initialize():
                raise RuntimeError('Ollama not initialized')

        self._messages = []
        self._system_prompt = system_prompt
        logger.info('Started new Ollama chat session')

    def set_tools(self, tools: List[Dict]) -> None:
        """Set tool declarations for Ollama.

        Args:
            tools: List of tool definitions
        """
        self._tools = tools

    def send_message(
        self,
        message: str,
        tools: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send message to Ollama.

        Args:
            message: User message
            tools: Optional tool definitions
            system_prompt: Optional system prompt

        Returns:
            Response with 'text' and 'tool_calls'
        """
        if not self._client:
            self.start_chat(system_prompt)

        if system_prompt:
            self._system_prompt = system_prompt

        if tools:
            self._tools = tools

        # Add system prompt if set
        messages = []
        if self._system_prompt:
            messages.append({'role': 'system', 'content': self._system_prompt})

        messages.extend(self._messages)
        messages.append({'role': 'user', 'content': message})

        try:
            kwargs = {
                'model': self.model_name,
                'messages': messages,
            }

            if self._tools:
                kwargs['tools'] = self._tools

            response = self._client.chat.completions.create(**kwargs)

            result = {
                'text': '',
                'tool_calls': [],
                'raw_response': response,
            }

            message_content = response.choices[0].message

            # Extract text
            if message_content.content:
                result['text'] = message_content.content

            # Extract tool calls
            if message_content.tool_calls:
                for tc in message_content.tool_calls:
                    try:
                        # Parse arguments as JSON
                        import json
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except json.JSONDecodeError:
                        args = {}

                    result['tool_calls'].append({
                        'name': tc.function.name,
                        'arguments': args,
                    })

            # Update message history
            self._messages.append({'role': 'user', 'content': message})
            self._messages.append({
                'role': 'assistant',
                'content': message_content.content or '',
                'tool_calls': [
                    {
                        'id': tc.id,
                        'type': 'function',
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments,
                        }
                    }
                    for tc in (message_content.tool_calls or [])
                ],
            })

            return result

        except Exception as e:
            logger.error(f'Ollama send_message failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}

    def send_tool_results(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Send tool results back to Ollama.

        Args:
            tool_results: List of {'name': str, 'result': dict, 'tool_call_id': str}

        Returns:
            Response with 'text'
        """
        if not self._client:
            return {'text': 'Error: No active chat session'}

        try:
            # Add tool results to messages
            for tr in tool_results:
                self._messages.append({
                    'role': 'tool',
                    'tool_call_id': tr.get('tool_call_id', 'unknown'),
                    'content': str(tr['result']),
                })

            messages = []
            if self._system_prompt:
                messages.append({'role': 'system', 'content': self._system_prompt})
            messages.extend(self._messages)

            kwargs = {
                'model': self.model_name,
                'messages': messages,
            }

            if self._tools:
                kwargs['tools'] = self._tools

            response = self._client.chat.completions.create(**kwargs)

            result = {
                'text': '',
                'tool_calls': [],
                'raw_response': response,
            }

            message_content = response.choices[0].message

            if message_content.content:
                result['text'] = message_content.content

            if message_content.tool_calls:
                for tc in message_content.tool_calls:
                    try:
                        import json
                        args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    except json.JSONDecodeError:
                        args = {}

                    result['tool_calls'].append({
                        'name': tc.function.name,
                        'arguments': args,
                    })

            self._messages.append({
                'role': 'assistant',
                'content': message_content.content or '',
                'tool_calls': [
                    {
                        'id': tc.id,
                        'type': 'function',
                        'function': {
                            'name': tc.function.name,
                            'arguments': tc.function.arguments,
                        }
                    }
                    for tc in (message_content.tool_calls or [])
                ],
            })

            return result

        except Exception as e:
            logger.error(f'Ollama send_tool_results failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}