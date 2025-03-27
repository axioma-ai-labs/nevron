from typing import List, Union

import numpy as np
from llama_cpp import Llama
from loguru import logger
from openai import AsyncOpenAI


async def generate_llama_embedding_local(model: Llama, text: Union[str, List[str]]) -> np.ndarray:
    """Generate embeddings using local LLama model.

    Args:
        model: Initialized local LLama model
        text: Single string or list of strings to embed

    Returns:
        numpy array of embeddings
    """
    try:
        texts = [text] if isinstance(text, str) else text
        embeddings = [np.array(model.embed(text_input, normalize=True)) for text_input in texts]
        return np.stack(embeddings)
    except Exception as e:
        logger.error(f"Error generating local LLama embeddings: {str(e)}")
        raise


async def generate_embedding_api(
    client: AsyncOpenAI, text: Union[str, List[str]], model: str
) -> np.ndarray:
    """Generate embeddings using OpenAI-compatible API (supports both OpenAI and Llama API).

    Args:
        client: AsyncOpenAI client instance
        text: Single string or list of strings to embed
        model: Model name to use for embeddings

    Returns:
        numpy array of embeddings
    """
    try:
        texts = [text] if isinstance(text, str) else text
        logger.debug(f"Getting embeddings for {len(texts)} texts")

        # Generate embeddings
        response = await client.embeddings.create(
            model=model,
            input=texts,
        )
        embeddings = [data.embedding for data in response.data]
        return np.array(embeddings)
    except Exception as e:
        # Add more detailed error logging
        logger.error(f"Error generating API embeddings: {str(e)}")
        logger.debug(f"API Details - Base URL: {client.base_url}, Model: {model}")

        if hasattr(e, "response"):
            logger.debug(f"Response status: {e.response.status_code}")
            logger.debug(f"Response text: {e.response.text}")
        raise
