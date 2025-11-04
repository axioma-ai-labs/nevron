from typing import Dict, List

import openai
from loguru import logger

from src.core.config import settings
from src.core.exceptions import LLMError


async def call_xai(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Call the xAI ChatCompletion endpoint.

    Args:
        messages: A list of dicts with 'role' and 'content'.
        kwargs: Additional parameters (e.g., model, temperature).

    Returns:
        str: Response content from xAI.
    """
    #: OpenAI client (since )
    client = openai.AsyncOpenAI(api_key=settings.XAI_API_KEY)

    model = kwargs.get("model", settings.XAI_MODEL)
    temperature = kwargs.get("temperature", 0.2)

    logger.debug(f"Calling xAI with model={model}, temperature={temperature}, messages={messages}")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
        )
        if not response.choices[0].message.content:
            raise LLMError("No content in xAI response")

        content = response.choices[0].message.content.strip()
        logger.debug(f"xAI response: {content}")
        return content
    except Exception as e:
        logger.error(f"xAI call failed: {e}")
        raise LLMError("Error during xAI API call") from e
