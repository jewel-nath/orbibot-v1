"""Moonshot AI (Kimi) LLM provider for OrbiBot Agent."""

import logging
import os
from typing import Any, Dict, List, Optional

try:
    from openai import OpenAI
    MOONSHOT_AVAILABLE = True
except ImportError:
    MOONSHOT_AVAILABLE = False

from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'kimi-latest'
DEFAULT_BASE_URL = 'https://api.moonshot.cn/v1'


class MoonshotProvider(BaseLLMProvider):
    """Moonshot AI Kimi LLM provider with tool calling support."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Moonshot provider.

        Args:
            config: Provider configuration with 'model', 'api_key_env', 'base_url'
        """
        super().__init__(config)
        self.model_name = config.get('model', DEFAULT_MODEL)
        self.api_key_env = config.get('api_key_env', 'MOONSHOT_API_KEY')
        self.base_url = config.get('base_url', DEFAULT_BASE_URL)
        self._client = None
        self._messages = []
        self._system_prompt = None
        self._tools = None

    def initialize(self) -> bool:
        """Initialize Moonshot client.

        Returns:
            True if successful
        """
        if not MOONSHOT_AVAILABLE:
            logger.error('openai not installed. Install with: pip install openai')
            return False

        api_key = os.environ.get(self.api_key_env, '')
        if not api_key:
            logger.error(f'{self.api_key_env} not set')
            return False

        try:
            self._client = OpenAI(
                api_key=api_key,
                base_url=self.base_url,
            )
            logger.info(f'Moonshot provider initialized with model: {self.model_name}')
            return True
        except Exception as e:
            logger.error(f'Failed to initialize Moonshot: {e}')
            return False

    def is_available(self) -> bool:
        """Check if Moonshot is available.

        Returns:
            True if API key is set
        """
        return MOONSHOT_AVAILABLE and bool(os.environ.get(self.api_key_env, ''))

    def start_chat(self, system_prompt: Optional[str] = None) -> None:
        """Start a new chat session.

        Args:
            system_prompt: System instruction for the chat
        """
        if not self._client:
            if not self.initialize():
                raise RuntimeError('Moonshot not initialized')

        self._messages = []
        self._system_prompt = system_prompt
        logger.info('Started new Moonshot chat session')

    def set_tools(self, tools: List[Dict]) -> None:
        """Set tool declarations for Moonshot.

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
        """Send message to Kimi.

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
                    result['tool_calls'].append({
                        'name': tc.function.name,
                        'arguments': tc.function.arguments,
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
            logger.error(f'Moonshot send_message failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}

    def send_tool_results(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Send tool results back to Kimi.

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
                    result['tool_calls'].append({
                        'name': tc.function.name,
                        'arguments': tc.function.arguments,
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
            logger.error(f'Moonshot send_tool_results failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}