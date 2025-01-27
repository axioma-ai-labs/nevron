from typing import Dict, List

from loguru import logger
from openai import OpenAI

from src.core.config import settings
from src.core.exceptions import LLMError


async def call_deepseek(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Call the DeepSeek API endpoint.

    Args:
        messages: A list of dicts with 'role' and 'content'.
        kwargs: Additional parameters (e.g., model, temperature).

    Returns:
        str: Response content from DeepSeek.
    """
    model = kwargs.get("model", settings.DEEPSEEK_MODEL)
    temperature = kwargs.get("temperature", 0.7)

    client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url=settings.DEEPSEEK_API_BASE_URL)

    logger.debug(
        f"Calling DeepSeek with model={model}, temperature={temperature}, messages={messages}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
        )
        if not response.choices[0].message.content:
            raise LLMError("No content in DeepSeek response")

        content = response.choices[0].message.content.strip()
        logger.debug(f"DeepSeek response: {content}")
        return content
    except Exception as e:
        logger.error(f"DeepSeek call failed: {e}")
        raise LLMError("Error during DeepSeek API call") from e
