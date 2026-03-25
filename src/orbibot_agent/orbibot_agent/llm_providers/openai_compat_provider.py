"""OpenAI-compatible base provider for OrbiBot Agent.

Shared implementation for any LLM that exposes an OpenAI-compatible API
(Moonshot/Kimi, Ollama, OpenRouter, etc.). Subclasses only need to override
__init__ to set model name, base URL, and API key logic.
"""

import json
import logging
from typing import Any, Dict, Generator, List, Optional

try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False

from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class OpenAICompatProvider(BaseLLMProvider):
    """Base class for LLM providers using the OpenAI-compatible API.

    Handles chat completions, tool calling, streaming, and history management.
    Subclasses must set self.model_name, self.base_url, and call _create_client().
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name: str = config.get('model', 'unknown')
        self.base_url: str = config.get('base_url', '')
        self._client: Optional[OpenAI] = None
        self._messages: List[Dict] = []
        self._system_prompt: Optional[str] = None
        self._tools: Optional[List[Dict]] = None

    def _create_client(self, api_key: str, base_url: str) -> bool:
        """Create the OpenAI client. Returns True on success."""
        if not OPENAI_SDK_AVAILABLE:
            logger.error('openai SDK not installed. Install with: pip install openai')
            return False
        try:
            self._client = OpenAI(api_key=api_key, base_url=base_url)
            logger.info(f'{self.__class__.__name__} initialized with model: {self.model_name}')
            return True
        except Exception as e:
            logger.error(f'Failed to initialize {self.__class__.__name__}: {e}')
            return False

    # -- Chat session management --

    def start_chat(self, system_prompt: Optional[str] = None) -> None:
        if not self._client:
            if not self.initialize():
                raise RuntimeError(f'{self.__class__.__name__} not initialized')
        self._messages = []
        self._system_prompt = system_prompt
        logger.info(f'Started new {self.__class__.__name__} chat session')

    def set_tools(self, tools: List[Dict]) -> None:
        self._tools = tools

    def _build_messages(self, extra_user_message: Optional[str] = None) -> List[Dict]:
        """Build full message list with system prompt, history, and optional new message."""
        messages = []
        if self._system_prompt:
            messages.append({'role': 'system', 'content': self._system_prompt})
        messages.extend(self._messages)
        if extra_user_message:
            messages.append({'role': 'user', 'content': extra_user_message})
        return messages

    def _build_kwargs(self, messages: List[Dict], stream: bool = False) -> Dict:
        """Build kwargs for chat.completions.create()."""
        kwargs: Dict[str, Any] = {'model': self.model_name, 'messages': messages}
        if self._tools:
            kwargs['tools'] = self._tools
        if stream:
            kwargs['stream'] = True
        return kwargs

    # -- Response parsing --

    def _parse_tool_args(self, raw_arguments: str) -> Any:
        """Parse tool call arguments from JSON string."""
        try:
            return json.loads(raw_arguments) if raw_arguments else {}
        except json.JSONDecodeError:
            return raw_arguments

    def _parse_response(self, response) -> Dict[str, Any]:
        """Parse a non-streaming chat completion response."""
        message = response.choices[0].message
        result: Dict[str, Any] = {
            'text': message.content or '',
            'tool_calls': [],
            'raw_response': response,
        }
        if message.tool_calls:
            for tc in message.tool_calls:
                result['tool_calls'].append({
                    'name': tc.function.name,
                    'arguments': self._parse_tool_args(tc.function.arguments),
                    'tool_call_id': tc.id,
                })
        return result

    def _append_assistant_message(self, message) -> None:
        """Append assistant response to conversation history."""
        assistant_msg: Dict[str, Any] = {
            'role': 'assistant',
            'content': message.content or '',
        }
        if message.tool_calls:
            assistant_msg['tool_calls'] = [
                {
                    'id': tc.id,
                    'type': 'function',
                    'function': {
                        'name': tc.function.name,
                        'arguments': tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ]
        self._messages.append(assistant_msg)

    # -- Non-streaming API --

    def send_message(
        self,
        message: str,
        tools: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self._client:
            self.start_chat(system_prompt)
        if system_prompt:
            self._system_prompt = system_prompt
        if tools:
            self._tools = tools

        messages = self._build_messages(extra_user_message=message)
        try:
            response = self._client.chat.completions.create(
                **self._build_kwargs(messages)
            )
            result = self._parse_response(response)

            # Update history
            self._messages.append({'role': 'user', 'content': message})
            self._append_assistant_message(response.choices[0].message)
            return result
        except Exception as e:
            logger.error(f'{self.__class__.__name__} send_message failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}

    def send_tool_results(self, tool_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self._client:
            return {'text': 'Error: No active chat session'}
        try:
            for tr in tool_results:
                self._messages.append({
                    'role': 'tool',
                    'tool_call_id': tr.get('tool_call_id', 'unknown'),
                    'content': str(tr['result']),
                })
            messages = self._build_messages()
            response = self._client.chat.completions.create(
                **self._build_kwargs(messages)
            )
            result = self._parse_response(response)
            self._append_assistant_message(response.choices[0].message)
            return result
        except Exception as e:
            logger.error(f'{self.__class__.__name__} send_tool_results failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}

    # -- Streaming API --

    def _stream_response(self, kwargs: Dict) -> Generator[Dict[str, Any], None, None]:
        """Stream a chat completion and yield event dicts.

        Handles text chunks and incremental tool call assembly.
        Updates conversation history after streaming completes.
        """
        text_buffer = ''
        tool_calls_raw: Dict[int, Dict[str, str]] = {}

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

        # Update history
        assistant_msg: Dict[str, Any] = {'role': 'assistant', 'content': text_buffer or ''}
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
                tool_calls_batch.append({
                    'name': v['name'],
                    'arguments': self._parse_tool_args(v['arguments']),
                    'tool_call_id': v['id'],
                })
            yield {'type': 'tool_calls', 'tool_calls': tool_calls_batch}

    def send_message_stream(self, message: str) -> Generator[Dict[str, Any], None, None]:
        if not self._client:
            self.start_chat()

        messages = self._build_messages(extra_user_message=message)
        try:
            self._messages.append({'role': 'user', 'content': message})
            yield from self._stream_response(self._build_kwargs(messages, stream=True))
        except Exception as e:
            logger.error(f'{self.__class__.__name__} send_message_stream failed: {e}')
            yield {'type': 'text', 'content': f'Error: {e}'}

    def send_tool_results_stream(
        self, tool_results: List[Dict[str, Any]]
    ) -> Generator[Dict[str, Any], None, None]:
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
            yield from self._stream_response(self._build_kwargs(messages, stream=True))
        except Exception as e:
            logger.error(f'{self.__class__.__name__} send_tool_results_stream failed: {e}')
            yield {'type': 'text', 'content': f'Error: {e}'}

    def inject_history(self, messages: List[Dict[str, str]]) -> None:
        """Inject conversation history (only into fresh sessions)."""
        if not self._messages:
            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if role in ('user', 'assistant') and content:
                    self._messages.append({'role': role, 'content': content})
