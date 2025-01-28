from typing import Dict, List

from loguru import logger
from openai import OpenAI

from src.core.config import settings
from src.core.exceptions import LLMError


async def call_qwen(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Call the Qwen API endpoint.

    Args:
        messages: A list of dicts with 'role' and 'content'.
        kwargs: Additional parameters (e.g., model, temperature).

    Returns:
        str: Response content from Qwen.
    """
    model = kwargs.get("model", settings.QWEN_MODEL)
    temperature = kwargs.get("temperature", 0.7)

    client = OpenAI(api_key=settings.QWEN_API_KEY, base_url=settings.QWEN_API_BASE_URL)

    logger.debug(f"Calling Qwen with model={model}, temperature={temperature}, messages={messages}")

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
        )
        if not response.choices or not response.choices[0].message.content:
            raise LLMError("No content in Qwen response")

        content = response.choices[0].message.content.strip()
        logger.debug(f"Qwen response: {content}")
        return content
    except Exception as e:
        logger.error(f"Qwen call failed: {e}")
        raise LLMError("Error during Qwen API call") from e
