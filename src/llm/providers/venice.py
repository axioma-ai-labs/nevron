from typing import Dict, List

import aiohttp
from loguru import logger

from src.core.config import settings
from src.core.exceptions import LLMError


async def call_venice(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Call the Venice AI API to generate a response.

    Args:
        messages: A list of dicts with 'role' and 'content'.
        kwargs: Additional parameters (e.g., model, temperature).

    Returns:
        str: Response content from Venice AI.

    Raises:
        LLMError: If the API call fails or returns no content.
    """
    url = f"{settings.VENICE_API_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.VENICE_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": kwargs.get("model", settings.VENICE_MODEL),
        "messages": messages,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error = await response.text()
                    raise LLMError(f"Venice API returned status {response.status}: {error}")

                data = await response.json()
                if not data.get("choices") or not data["choices"][0].get("message", {}).get(
                    "content"
                ):
                    raise LLMError("Venice AI returned empty response")

                return data["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logger.error(f"Error during Venice AI API call: {str(e)}")
        raise LLMError(f"Venice AI API call failed: {str(e)}")
