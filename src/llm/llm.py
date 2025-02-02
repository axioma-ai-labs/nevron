from typing import Any, Dict, List

import openai
from llama_cpp import Llama
from loguru import logger

from src.core.config import settings
from src.core.defs import EmbeddingProviderType, LLMProviderType
from src.core.exceptions import LLMError
from src.llm.providers.anthropic import call_anthropic
from src.llm.providers.llama import call_llama
from src.llm.providers.oai import call_openai
from src.llm.providers.xai import call_xai


class LLM:
    """
    LLM class for generating responses from the LLM backend.
    """

    def __init__(self):
        """
        Initialize the LLM class based on the selected provider from settings.
        Supported providers: 'openai', 'anthropic', 'xai'
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
        elif self.provider == LLMProviderType.XAI:
            return await call_xai(messages, **kwargs)
        elif self.provider == LLMProviderType.LLAMA:
            return await call_llama(messages, **kwargs)
        else:
            raise LLMError(f"Unknown LLM provider: {self.provider}")


#: Embedding client. Used for embedding generation.
def get_embedding_client(provider: EmbeddingProviderType = EmbeddingProviderType.OPENAI):
    """
    Initialize and return an embedding client for either OpenAI or Llama API.

    Args:
        provider: The provider to initialize client for (default: OPENAI)

    Returns:
        AsyncOpenAI: Configured OpenAI client

    Raises:
        ValueError: If provider is unsupported
    """
    if provider == EmbeddingProviderType.OPENAI:
        return openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    elif provider == EmbeddingProviderType.LLAMA_API:
        return openai.AsyncOpenAI(
            api_key=settings.LLAMA_API_KEY, base_url=settings.LLAMA_API_BASE_URL
        )
    else:
        raise ValueError(f"Unsupported provider for embedding client: {provider}")


def get_llama_model(model_path: str) -> Llama:
    """
    Initialize and return a local Llama model client.

    Args:
        model_path: Path to the Llama model.

    Returns:
        Llama: Initialized Llama model instance.
    """
    return Llama(
        model_path=model_path,
        embedding=True,
        n_ctx=2048,
        pooling_type=settings.EMBEDDING_POOLING_TYPE,  # Default pooling type, change for different model
    )
