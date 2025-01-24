from typing import Dict, List

import requests
from loguru import logger
from openai import OpenAI

from src.core.config import settings
from src.core.defs import LlamaProviderType
from src.core.exceptions import LLMError


def _format_messages_for_ollama(messages: List[Dict[str, str]]) -> str:
    """
    Format messages for Ollama API.

    Args:
        messages: List of message dictionaries with 'role' and 'content'.

    Returns:
        str: Formatted prompt string.
    """
    formatted_messages = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            formatted_messages.append(f"System: {content}")
        elif role == "user":
            formatted_messages.append(f"User: {content}")
        elif role == "assistant":
            formatted_messages.append(f"Assistant: {content}")
    return "\n".join(formatted_messages)


async def _call_fireworks(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Call the Fireworks.ai Llama endpoint.

    Args:
        messages: A list of dicts with 'role' and 'content'.
        kwargs: Additional parameters (e.g., model, temperature).

    Returns:
        str: Response content from Llama.
    """
    url = f"{settings.LLAMA_FIREWORKS_URL}/v1/chat/completions"
    model = kwargs.get("model", settings.LLAMA_MODEL_NAME)
    temperature = kwargs.get("temperature", 0.6)

    payload = {
        "model": model,
        "max_tokens": 16384,
        "top_p": 1,
        "top_k": 40,
        "presence_penalty": 0,
        "frequency_penalty": 0,
        "temperature": temperature,
        "messages": messages,
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.LLAMA_API_KEY}",
    }

    logger.debug(
        f"Calling Fireworks Llama with model={model}, temperature={temperature}, messages={messages}"
    )

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        if not data.get("choices") or not data["choices"][0].get("message", {}).get("content"):
            raise LLMError("No content in Fireworks Llama response")

        content = data["choices"][0]["message"]["content"].strip()
        logger.debug(f"Fireworks Llama response: {content}")
        return content
    except Exception as e:
        logger.error(f"Fireworks Llama call failed: {e}")
        raise LLMError("Error during Fireworks Llama API call") from e


async def _call_ollama(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Call the local Ollama endpoint.

    Args:
        messages: A list of dicts with 'role' and 'content'.
        kwargs: Additional parameters (e.g., model, temperature).

    Returns:
        str: Response content from Ollama.
    """
    url = f"{settings.LLAMA_OLLAMA_URL}/api/generate"
    model = kwargs.get("model", settings.LLAMA_OLLAMA_MODEL)
    temperature = kwargs.get("temperature", 0.6)

    # Format messages into a prompt
    prompt = _format_messages_for_ollama(messages)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "temperature": temperature,
    }

    headers = {"Content-Type": "application/json"}

    logger.debug(f"Calling Ollama with model={model}, temperature={temperature}, prompt={prompt}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        if not data.get("response"):
            raise LLMError("No content in Ollama response")

        content = data["response"].strip()
        logger.debug(f"Ollama response: {content}")
        return content
    except Exception as e:
        logger.error(f"Ollama call failed: {e}")
        raise LLMError("Error during Ollama API call") from e


async def _call_llama_api(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Call the Llama API endpoint.

    Args:
        messages: A list of dicts with 'role' and 'content'.
        kwargs: Additional parameters (e.g., model, temperature).

    Returns:
        str: Response content from Llama API.
    """
    model = kwargs.get("model", settings.LLAMA_API_MODEL)
    temperature = kwargs.get("temperature", 0.6)

    client = OpenAI(api_key=settings.LLAMA_API_KEY, base_url=settings.LLAMA_API_BASE_URL)

    logger.debug(
        f"Calling Llama API with model={model}, temperature={temperature}, messages={messages}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
        )

        if not response.choices or not response.choices[0].message.content:
            raise LLMError("No content in Llama API response")

        content = response.choices[0].message.content.strip()
        logger.debug(f"Llama API response: {content}")
        return content
    except Exception as e:
        logger.error(f"Llama API call failed: {e}")
        raise LLMError("Error during Llama API call") from e


async def _call_openrouter(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Call the OpenRouter endpoint.

    Args:
        messages: A list of dicts with 'role' and 'content'.
        kwargs: Additional parameters (e.g., model, temperature).

    Returns:
        str: Response content from OpenRouter.
    """
    model = kwargs.get("model", settings.LLAMA_OPENROUTER_MODEL)
    temperature = kwargs.get("temperature", 0.6)

    client = OpenAI(api_key=settings.LLAMA_API_KEY, base_url=settings.LLAMA_OPENROUTER_URL)

    logger.debug(
        f"Calling OpenRouter with model={model}, temperature={temperature}, messages={messages}"
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,  # type: ignore
            temperature=temperature,
        )

        if not response.choices or not response.choices[0].message.content:
            raise LLMError("No content in OpenRouter response")

        content = response.choices[0].message.content.strip()
        logger.debug(f"OpenRouter response: {content}")
        return content
    except Exception as e:
        logger.error(f"OpenRouter call failed: {e}")
        raise LLMError("Error during OpenRouter API call") from e


async def call_llama(messages: List[Dict[str, str]], **kwargs) -> str:
    """
    Call the Llama model based on the configured provider.

    Args:
        messages: A list of dicts with 'role' and 'content'.
        kwargs: Additional parameters (e.g., model, temperature).

    Returns:
        str: Response content from Llama.

    Raises:
        LLMError: If the provider is not supported or if the API call fails.
    """
    provider = settings.LLAMA_PROVIDER

    provider_map = {
        LlamaProviderType.FIREWORKS: _call_fireworks,
        LlamaProviderType.OLLAMA: _call_ollama,
        LlamaProviderType.LLAMA_API: _call_llama_api,
        LlamaProviderType.OPENROUTER: _call_openrouter,
    }
    if provider in provider_map:
        return await provider_map[provider](messages, **kwargs)
    else:
        raise LLMError(f"Unsupported Llama provider: {provider}")
