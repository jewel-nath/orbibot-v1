"""Moonshot AI (Kimi) LLM provider for OrbiBot Agent."""

import json
import logging
from typing import Any, Dict, Generator, List, Optional

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

        api_key = self._get_api_key(self.api_key_env)
        if not api_key:
            logger.error(f'{self.api_key_env} not set and no api_key in config')
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
        return MOONSHOT_AVAILABLE and bool(self._get_api_key(self.api_key_env))

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

    def _build_messages(self, extra_user_message: str = None) -> List[Dict]:
        """Build the full messages list including system prompt and history."""
        messages = []
        if self._system_prompt:
            messages.append({'role': 'system', 'content': self._system_prompt})
        messages.extend(self._messages)
        if extra_user_message:
            messages.append({'role': 'user', 'content': extra_user_message})
        return messages

    def send_message_stream(
        self,
        message: str,
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream Kimi response using OpenAI-compatible streaming.

        Args:
            message: User message

        Yields:
            Event dicts with 'type': 'text' | 'tool_calls'
        """
        if not self._client:
            self.start_chat()

        messages = self._build_messages(extra_user_message=message)

        try:
            kwargs = {
                'model': self.model_name,
                'messages': messages,
                'stream': True,
            }
            if self._tools:
                kwargs['tools'] = self._tools

            text_buffer = ''
            tool_calls_raw = {}  # index → partial tool call

            stream = self._client.chat.completions.create(**kwargs)
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                # Text chunk
                if delta.content:
                    text_buffer += delta.content
                    yield {'type': 'text', 'content': delta.content}

                # Tool call chunks (streamed incrementally)
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        idx = tc_chunk.index
                        if idx not in tool_calls_raw:
                            tool_calls_raw[idx] = {
                                'id': '',
                                'name': '',
                                'arguments': '',
                            }
                        if tc_chunk.id:
                            tool_calls_raw[idx]['id'] += tc_chunk.id
                        if tc_chunk.function:
                            if tc_chunk.function.name:
                                tool_calls_raw[idx]['name'] += tc_chunk.function.name
                            if tc_chunk.function.arguments:
                                tool_calls_raw[idx]['arguments'] += tc_chunk.function.arguments

            # Update history
            self._messages.append({'role': 'user', 'content': message})
            assistant_msg: Dict[str, Any] = {
                'role': 'assistant',
                'content': text_buffer or '',
            }
            if tool_calls_raw:
                assistant_msg['tool_calls'] = [
                    {
                        'id': v['id'],
                        'type': 'function',
                        'function': {'name': v['name'], 'arguments': v['arguments']},
                    }
                    for v in tool_calls_raw.values()
                ]
            self._messages.append(assistant_msg)

            # Yield tool calls batch
            if tool_calls_raw:
                tool_calls_batch = []
                for v in tool_calls_raw.values():
                    try:
                        args = json.loads(v['arguments']) if v['arguments'] else {}
                    except json.JSONDecodeError:
                        args = v['arguments']
                    tool_calls_batch.append({
                        'name': v['name'],
                        'arguments': args,
                        'tool_call_id': v['id'],
                    })
                yield {'type': 'tool_calls', 'tool_calls': tool_calls_batch}

        except Exception as e:
            logger.error(f'Moonshot send_message_stream failed: {e}')
            yield {'type': 'text', 'content': f'Error: {e}'}

    def send_tool_results_stream(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> Generator[Dict[str, Any], None, None]:
        """Stream Kimi response after tool results.

        Args:
            tool_results: List of {'name': str, 'result': dict, 'tool_call_id': str}

        Yields:
            Event dicts
        """
        if not self._client:
            yield {'type': 'text', 'content': 'Error: No active chat session'}
            return

        try:
            for tr in tool_results:
                self._messages.append({
                    'role': 'tool',
                    'tool_call_id': tr.get('tool_call_id', 'unknown'),
                    'content': str(tr['result']),
                })

            messages = self._build_messages()

            kwargs = {
                'model': self.model_name,
                'messages': messages,
                'stream': True,
            }
            if self._tools:
                kwargs['tools'] = self._tools

            text_buffer = ''
            tool_calls_raw = {}

            stream = self._client.chat.completions.create(**kwargs)
            for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue
                if delta.content:
                    text_buffer += delta.content
                    yield {'type': 'text', 'content': delta.content}
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        idx = tc_chunk.index
                        if idx not in tool_calls_raw:
                            tool_calls_raw[idx] = {'id': '', 'name': '', 'arguments': ''}
                        if tc_chunk.id:
                            tool_calls_raw[idx]['id'] += tc_chunk.id
                        if tc_chunk.function:
                            if tc_chunk.function.name:
                                tool_calls_raw[idx]['name'] += tc_chunk.function.name
                            if tc_chunk.function.arguments:
                                tool_calls_raw[idx]['arguments'] += tc_chunk.function.arguments

            assistant_msg: Dict[str, Any] = {'role': 'assistant', 'content': text_buffer or ''}
            if tool_calls_raw:
                assistant_msg['tool_calls'] = [
                    {'id': v['id'], 'type': 'function',
                     'function': {'name': v['name'], 'arguments': v['arguments']}}
                    for v in tool_calls_raw.values()
                ]
            self._messages.append(assistant_msg)

            if tool_calls_raw:
                tool_calls_batch = []
                for v in tool_calls_raw.values():
                    try:
                        args = json.loads(v['arguments']) if v['arguments'] else {}
                    except json.JSONDecodeError:
                        args = v['arguments']
                    tool_calls_batch.append({
                        'name': v['name'],
                        'arguments': args,
                        'tool_call_id': v['id'],
                    })
                yield {'type': 'tool_calls', 'tool_calls': tool_calls_batch}

        except Exception as e:
            logger.error(f'Moonshot send_tool_results_stream failed: {e}')
            yield {'type': 'text', 'content': f'Error: {e}'}

    def inject_history(self, messages: List[Dict[str, str]]) -> None:
        """Inject conversation history into the current session.

        Args:
            messages: List of {'role': 'user'|'assistant', 'content': str}
        """
        if not self._messages:
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role in ('user', 'assistant') and content:
                    self._messages.append({'role': role, 'content': content})