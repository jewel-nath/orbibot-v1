"""Ollama local LLM provider for OrbiBot Agent."""

import logging
from typing import Any, Dict

from .openai_compat_provider import OpenAICompatProvider, OPENAI_SDK_AVAILABLE

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'llama3.1:8b'
DEFAULT_BASE_URL = 'http://localhost:11434/v1'


class OllamaProvider(OpenAICompatProvider):
    """Ollama local LLM provider — wraps the OpenAI-compatible Ollama API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get('model', DEFAULT_MODEL)
        self.base_url = config.get('base_url', DEFAULT_BASE_URL)

    def initialize(self) -> bool:
        # Ollama doesn't need a real API key
        return self._create_client('ollama', self.base_url)

    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        if not OPENAI_SDK_AVAILABLE or not self._client:
            return False
        try:
            self._client.models.list()
            return True
        except Exception:
            return False
