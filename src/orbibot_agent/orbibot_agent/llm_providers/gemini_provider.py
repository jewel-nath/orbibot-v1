"""Google Gemini LLM provider for OrbiBot Agent."""

import logging
import os
from typing import Any, Dict, List, Optional

try:
    import google.generativeai as genai
    from google.generativeai.types import FunctionDeclaration, Tool
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
        self._api_key = None
        self._model = None
        self._chat = None
        self._tool_declarations = None

    def initialize(self) -> bool:
        """Initialize Gemini client.

        Returns:
            True if successful
        """
        if not GEMINI_AVAILABLE:
            logger.error('google-generativeai not installed. Install with: pip install google-generativeai')
            return False

        self._api_key = os.environ.get(self.api_key_env, '')
        if not self._api_key:
            logger.error(f'{self.api_key_env} not set')
            return False

        try:
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(self.model_name)
            logger.info(f'Gemini provider initialized with model: {self.model_name}')
            return True
        except Exception as e:
            logger.error(f'Failed to initialize Gemini: {e}')
            return False

    def is_available(self) -> bool:
        """Check if Gemini is available.

        Returns:
            True if API key is set
        """
        return GEMINI_AVAILABLE and bool(os.environ.get(self.api_key_env, ''))

    def start_chat(self, system_prompt: Optional[str] = None) -> None:
        """Start a new chat session.

        Args:
            system_prompt: System instruction for the chat
        """
        if not self._model:
            if not self.initialize():
                raise RuntimeError('Gemini not initialized')

        # Rebuild model with system instruction if provided
        if system_prompt:
            self._model = genai.GenerativeModel(
                self.model_name,
                system_instruction=system_prompt,
                tools=self._tool_declarations,
            )

        self._chat = self._model.start_chat()
        logger.info('Started new Gemini chat session')

    def set_tools(self, tools: List[Dict]) -> None:
        """Set tool declarations for Gemini.

        Args:
            tools: List of tool definitions
        """
        if not GEMINI_AVAILABLE:
            return

        gemini_tools = []
        for tool in tools:
            if tool.get('type') == 'function':
                func = tool.get('function', {})
                declaration = FunctionDeclaration(
                    name=func.get('name'),
                    description=func.get('description'),
                    parameters=func.get('parameters', {}),
                )
                gemini_tools.append(Tool(function_declarations=[declaration]))

        self._tool_declarations = gemini_tools

        # Rebuild model with tools
        if self._model:
            self._model = genai.GenerativeModel(
                self.model_name,
                tools=self._tool_declarations,
            )

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

            result = {
                'text': '',
                'tool_calls': [],
                'raw_response': response,
            }

            # Extract text
            for part in response.parts:
                if part.text:
                    result['text'] += part.text

            # Extract function calls
            for part in response.parts:
                if part.function_call:
                    result['tool_calls'].append({
                        'name': part.function_call.name,
                        'arguments': dict(part.function_call.args),
                    })

            return result

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
                parts.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tr['name'],
                            response=tr['result'],
                        )
                    )
                )

            response = self._chat.send_message(genai.protos.Content(parts=parts))

            result = {
                'text': '',
                'tool_calls': [],
                'raw_response': response,
            }

            # Extract text
            for part in response.parts:
                if part.text:
                    result['text'] += part.text

            # Extract function calls (for multi-turn)
            for part in response.parts:
                if part.function_call:
                    result['tool_calls'].append({
                        'name': part.function_call.name,
                        'arguments': dict(part.function_call.args),
                    })

            return result

        except Exception as e:
            logger.error(f'Gemini send_tool_results failed: {e}')
            return {'text': f'Error: {e}', 'tool_calls': [], 'error': str(e)}