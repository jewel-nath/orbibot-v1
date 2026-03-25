"""Moonshot AI (Kimi) LLM provider for OrbiBot Agent."""

import logging
from typing import Any, Dict

from .openai_compat_provider import OpenAICompatProvider, OPENAI_SDK_AVAILABLE

logger = logging.getLogger(__name__)

DEFAULT_MODEL = 'kimi-latest'
DEFAULT_BASE_URL = 'https://api.moonshot.cn/v1'


class MoonshotProvider(OpenAICompatProvider):
    """Moonshot AI Kimi provider — wraps the OpenAI-compatible Moonshot API."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.model_name = config.get('model', DEFAULT_MODEL)
        self.api_key_env = config.get('api_key_env', 'MOONSHOT_API_KEY')
        self.base_url = config.get('base_url', DEFAULT_BASE_URL)

    def initialize(self) -> bool:
        api_key = self._get_api_key(self.api_key_env)
        if not api_key:
            logger.error(f'{self.api_key_env} not set')
            return False
        return self._create_client(api_key, self.base_url)

    def is_available(self) -> bool:
        return OPENAI_SDK_AVAILABLE and bool(self._get_api_key(self.api_key_env))
