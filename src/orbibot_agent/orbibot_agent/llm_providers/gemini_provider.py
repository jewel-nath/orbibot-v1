"""Google Gemini LLM provider for OrbiBot Agent (google-genai SDK)."""

import logging
from typing import Any, Dict, List, Optional

try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

from .base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'gemini-2.0-flash'


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider with tool calling support."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Gemini provider.

        Args:
            config: Provider configuration with 'model', 'api_key_env'
        """
        super().__init__(config)
        self.model_name = config.get('model', DEFAULT_MODEL)
        self.api_key_env = config.get('api_key_env', 'GEMINI_API_KEY')
        self._api_key: Optional[str] = None
        self._client = None
        self._chat = None
        self._tool_declarations: List = []
        self._system_prompt: Optional[str] = None

    def initialize(self) -> bool:
        """Initialize Gemini client.

        Returns:
            True if successful
        """
        if not GEMINI_AVAILABLE:
            logger.error('google-genai not installed. Install with: pip install google-genai')
            return False

        self._api_key = self._get_api_key(self.api_key_env)
        if not self._api_key:
            logger.error(f'{self.api_key_env} not set and no api_key in config')
            return False

        try:
            self._client = genai.Client(api_key=self._api_key)
            logger.info(f'Gemini provider initialized with model: {self.model_name}')
            return True
        except Exception as e:
            logger.error(f'Failed to initialize Gemini: {e}')
            return False

    def is_available(self) -> bool:
        """Check if Gemini is available.

        Returns:
            True if library is installed and API key is present
        """
        return GEMINI_AVAILABLE and bool(self._get_api_key(self.api_key_env))

    def _make_chat(self) -> None:
        """Create (or recreate) a chat session with current system prompt and tools."""
        if not self._client:
            if not self.initialize():
                raise RuntimeError('Gemini not initialized')

        config = types.GenerateContentConfig(
            system_instruction=self._system_prompt,
            tools=self._tool_declarations or None,
        )
        self._chat = self._client.chats.create(model=self.model_name, config=config)

    def start_chat(self, system_prompt: Optional[str] = None) -> None:
        """Start a new chat session.

        Args:
            system_prompt: System instruction for the chat
        """
        self._system_prompt = system_prompt
        self._make_chat()
        logger.info('Started new Gemini chat session')

    def set_tools(self, tools: List[Dict]) -> None:
        """Set tool declarations for Gemini.

        Args:
            tools: List of tool definitions (OpenAI-compatible function schema)
        """
        if not GEMINI_AVAILABLE:
            return

        declarations = []
        for tool in tools:
            if tool.get('type') == 'function':
                func = tool.get('function', {})
                declarations.append(types.FunctionDeclaration(
                    name=func.get('name'),
                    description=func.get('description'),
                    parameters_json_schema=func.get('parameters', {}),
                ))

        self._tool_declarations = [types.Tool(function_declarations=declarations)] if declarations else []

        # Rebuild the chat so it picks up the new tools
        if self._chat is not None:
            self._make_chat()

    def _parse_response(self, response) -> Dict[str, Any]:
        """Extract text and tool calls from a GenerateContentResponse."""
        try:
            text = response.text or ''
        except Exception:
            text = ''

        tool_calls = []
        if response.function_calls:
            for fc in response.function_calls:
                tool_calls.append({
                    'name': fc.name,
                    'arguments': dict(fc.args),
                })

        return {
            'text': text,
            'tool_calls': tool_calls,
            'raw_response': response,
        }

    def send_message(
        self,
        message: str,
        tools: Optional[List[Dict]] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send message to Gemini.

        Args:
            message: User message
            tools: Optional tool definitions
            system_prompt: Optional system prompt

        Returns:
            Response with 'text' and 'tool_calls'
        """
        if not self._chat:
            self.start_chat(system_prompt)

        if tools and not self._tool_declarations:
            self.set_tools(tools)

        try:
            response = self._chat.send_message(message)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f'Gemini send_message failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}

    def send_tool_results(
        self,
        tool_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Send tool results back to Gemini.

        Args:
            tool_results: List of {'name': str, 'result': dict}

        Returns:
            Response with 'text'
        """
        if not self._chat:
            return {'text': 'Error: No active chat session'}

        try:
            parts = []
            for tr in tool_results:
                result = tr['result']
                if not isinstance(result, dict):
                    result = {'result': result}
                parts.append(types.Part.from_function_response(
                    name=tr['name'],
                    response=result,
                ))

            response = self._chat.send_message(parts)
            return self._parse_response(response)
        except Exception as e:
            logger.error(f'Gemini send_tool_results failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}
