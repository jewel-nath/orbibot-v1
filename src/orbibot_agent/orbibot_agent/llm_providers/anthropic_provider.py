"""Anthropic Claude LLM provider for OrbiBot Agent."""

import logging
from typing import Any, Dict, Generator, List, Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'claude-3-5-sonnet-20241022'


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude LLM provider with tool calling support."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Anthropic provider.

        Args:
            config: Provider configuration with 'model', 'api_key_env'
        """
        super().__init__(config)
        self.model_name = config.get('model', DEFAULT_MODEL)
        self.api_key_env = config.get('api_key_env', 'ANTHROPIC_API_KEY')
        self._client = None
        self._messages = []
        self._system_prompt = None
        self._tools = None

    def initialize(self) -> bool:
        """Initialize Anthropic client.

        Returns:
            True if successful
        """
        if not ANTHROPIC_AVAILABLE:
            logger.error('anthropic not installed. Install with: pip install anthropic')
            return False

        api_key = self._get_api_key(self.api_key_env)
        if not api_key:
            logger.error(f'{self.api_key_env} not set and no api_key in config')
            return False

        try:
            self._client = anthropic.Anthropic(api_key=api_key)
            logger.info(f'Anthropic provider initialized with model: {self.model_name}')
            return True
        except Exception as e:
            logger.error(f'Failed to initialize Anthropic: {e}')
            return False

    def is_available(self) -> bool:
        """Check if Anthropic is available.

        Returns:
            True if API key is set
        """
        return ANTHROPIC_AVAILABLE and bool(self._get_api_key(self.api_key_env))

    def start_chat(self, system_prompt: Optional[str] = None) -> None:
        """Start a new chat session.

        Args:
            system_prompt: System instruction for the chat
        """
        if not self._client:
            if not self.initialize():
                raise RuntimeError('Anthropic not initialized')

        self._messages = []
        self._system_prompt = system_prompt
        logger.info('Started new Anthropic chat session')

    def set_tools(self, tools: List[Dict]) -> None:
        """Set tool declarations for Anthropic.

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
        """Send message to Claude.

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

        self._messages.append({'role': 'user', 'content': message})

        try:
            kwargs = {
                'model': self.model_name,
                'messages': self._messages,
                'max_tokens': 4096,
            }

            if self._system_prompt:
                kwargs['system'] = self._system_prompt

            if self._tools:
                kwargs['tools'] = self._tools

            response = self._client.messages.create(**kwargs)

            result = {
                'text': '',
                'tool_calls': [],
                'raw_response': response,
            }

            # Process response content
            for content in response.content:
                if content.type == 'text':
                    result['text'] += content.text
                elif content.type == 'tool_use':
                    result['tool_calls'].append({
                        'name': content.name,
                        'arguments': content.input,
                        'tool_use_id': content.id,
                    })

            # Add assistant response to history
            self._messages.append({
                'role': 'assistant',
                'content': response.content,
            })

            return result

        except Exception as e:
            logger.error(f'Anthropic send_message failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}

    def send_tool_results(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Send tool results back to Claude.

        Args:
            tool_results: List of {'name': str, 'result': dict}

        Returns:
            Response with 'text'
        """
        if not self._client:
            return {'text': 'Error: No active chat session'}

        try:
            # Add tool results as user messages
            for tr in tool_results:
                self._messages.append({
                    'role': 'user',
                    'content': [{
                        'type': 'tool_result',
                        'tool_use_id': tr.get('tool_use_id', 'unknown'),
                        'content': str(tr['result']),
                    }],
                })

            kwargs = {
                'model': self.model_name,
                'messages': self._messages,
                'max_tokens': 4096,
            }

            if self._system_prompt:
                kwargs['system'] = self._system_prompt

            if self._tools:
                kwargs['tools'] = self._tools

            response = self._client.messages.create(**kwargs)

            result = {
                'text': '',
                'tool_calls': [],
                'raw_response': response,
            }

            for content in response.content:
                if content.type == 'text':
                    result['text'] += content.text
                elif content.type == 'tool_use':
                    result['tool_calls'].append({
                        'name': content.name,
                        'arguments': content.input,
                        'tool_use_id': content.id,
                    })

            self._messages.append({
                'role': 'assistant',
                'content': response.content,
            })

            return result

        except Exception as e:
            logger.error(f'Anthropic send_tool_results failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}

    def send_message_stream(
        self,
        message: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream Claude response as event chunks using the streaming API.

        Args:
            message: User message

        Yields:
            Event dicts with 'type': 'text' | 'tool_calls'
        """
        if not self._client:
            self.start_chat()

        self._messages.append({'role': 'user', 'content': message})

        try:
            kwargs = {
                'model': self.model_name,
                'messages': self._messages,
                'max_tokens': 4096,
            }
            if self._system_prompt:
                kwargs['system'] = self._system_prompt
            if self._tools:
                kwargs['tools'] = self._tools

            tool_calls_batch = []
            full_content = []

            with self._client.messages.stream(**kwargs) as stream:
                for text_chunk in stream.text_stream:
                    yield {'type': 'text', 'content': text_chunk}

                # After streaming, get the final message for tool calls
                final_message = stream.get_final_message()
                full_content = final_message.content

                for content in final_message.content:
                    if content.type == 'tool_use':
                        tool_calls_batch.append({
                            'name': content.name,
                            'arguments': content.input,
                            'tool_use_id': content.id,
                        })

            # Add assistant response to history
            self._messages.append({
                'role': 'assistant',
                'content': full_content,
            })

            if tool_calls_batch:
                yield {'type': 'tool_calls', 'tool_calls': tool_calls_batch}

        except Exception as e:
            logger.error(f'Anthropic send_message_stream failed: {e}')
            yield {'type': 'text', 'content': f'Error: {e}'}

    def send_tool_results_stream(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream Claude response after tool results.

        Args:
            tool_results: List of {'name': str, 'result': dict, 'tool_use_id': str}

        Yields:
            Event dicts
        """
        if not self._client:
            yield {'type': 'text', 'content': 'Error: No active chat session'}
            return

        try:
            for tr in tool_results:
                self._messages.append({
                    'role': 'user',
                    'content': [{
                        'type': 'tool_result',
                        'tool_use_id': tr.get('tool_use_id', 'unknown'),
                        'content': str(tr['result']),
                    }],
                })

            kwargs = {
                'model': self.model_name,
                'messages': self._messages,
                'max_tokens': 4096,
            }
            if self._system_prompt:
                kwargs['system'] = self._system_prompt
            if self._tools:
                kwargs['tools'] = self._tools

            tool_calls_batch = []
            full_content = []

            with self._client.messages.stream(**kwargs) as stream:
                for text_chunk in stream.text_stream:
                    yield {'type': 'text', 'content': text_chunk}

                final_message = stream.get_final_message()
                full_content = final_message.content

                for content in final_message.content:
                    if content.type == 'tool_use':
                        tool_calls_batch.append({
                            'name': content.name,
                            'arguments': content.input,
                            'tool_use_id': content.id,
                        })

            self._messages.append({
                'role': 'assistant',
                'content': full_content,
            })

            if tool_calls_batch:
                yield {'type': 'tool_calls', 'tool_calls': tool_calls_batch}

        except Exception as e:
            logger.error(f'Anthropic send_tool_results_stream failed: {e}')
            yield {'type': 'text', 'content': f'Error: {e}'}

    def inject_history(self, messages: List[Dict[str, str]]) -> None:
        """Inject conversation history into the current session.

        Args:
            messages: List of {'role': 'user'|'assistant', 'content': str}
        """
        # Prepend history before any existing messages (but after system prompt)
        # Only inject if the session is fresh (no messages yet)
        if not self._messages:
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role in ('user', 'assistant') and content:
                    self._messages.append({'role': role, 'content': content})