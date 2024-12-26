from typing import Any, Dict, List

import openai
from loguru import logger

from src.core.config import settings
from src.core.defs import LLMProviderType
from src.core.exceptions import LLMError
from src.llm.providers.anthropic import call_anthropic
from src.llm.providers.oai import call_openai


class LLM:
    """
    LLM class for generating responses from the LLM backend.
    """

    def __init__(self):
        """
        Initialize the LLM class based on the selected provider from settings.
        Supported providers: 'openai', 'anthropic'
        """
        self.provider = settings.LLM_PROVIDER
        logger.debug(f"Using LLM provider: {self.provider}")

    async def generate_response(self, messages: List[Dict[str, Any]], **kwargs) -> str:
        """
        Generate a response from the LLM backend based on the provider.

        Args:
            messages: A list of dicts, each containing 'role' and 'content'.
            kwargs: Additional parameters (e.g., model, temperature).

        Returns:
            str: LLM response text
        """
        # Add system message with agent's personality and goal if not present
        if not messages or messages[0].get("role") != "system":
            system_message = {
                "role": "system",
                "content": f"{settings.AGENT_PERSONALITY}\n\n{settings.AGENT_GOAL}",
            }
            messages = [system_message] + messages

        if self.provider == LLMProviderType.OPENAI:
            return await call_openai(messages, **kwargs)
        elif self.provider == LLMProviderType.ANTHROPIC:
            return await call_anthropic(messages, **kwargs)
        else:
            raise LLMError(f"Unknown LLM provider: {self.provider}")


#: OpenAI client. Used for embedding generation.
def get_oai_client():
    return openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
