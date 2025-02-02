from typing import List, Union, Optional

import numpy as np
from loguru import logger
from openai import AsyncOpenAI
from llama_cpp import Llama

from src.core.config import settings
from src.core.defs import EmbeddingProviderType
from src.llm.llm import get_embedding_client, get_llama_model
from src.llm.providers.llama_embeddings import (
    generate_llama_embedding_local,
    generate_embedding_api
)


class EmbeddingGenerator:
    """A class to generate embeddings using multiple provider options."""

    def __init__(
        self,
        provider: EmbeddingProviderType = settings.EMBEDDING_PROVIDER,
        openai_client: Optional[AsyncOpenAI] = None,
        llama_model: Optional[Union[str, Llama]] = None,
    ):
        """
        Initialize the embedding generator.

        Args:
            provider: The embedding provider to use ('openai', 'llama_local', 'llama_api', ...)
            openai_client: Optional pre-configured OpenAI client (default: None)
            llama_model: Optional pre-configured LLama model (default: None)
        """
        self.provider = provider
        logger.debug(f"Using Embedding provider: {self.provider}")
        
        if self.provider == EmbeddingProviderType.OPENAI:
            self.client = openai_client or get_embedding_client(self.provider)
            self.model = settings.OPENAI_EMBEDDING_MODEL
        elif self.provider == EmbeddingProviderType.LLAMA_LOCAL:
            if isinstance(llama_model, Llama):
                self.model = llama_model
            else:
                model_path = llama_model if (isinstance(llama_model, str) and llama_model != "") else settings.LLAMA_MODEL_PATH
                self.model = get_llama_model(model_path)
        elif self.provider == EmbeddingProviderType.LLAMA_API:
            self.client = openai_client or get_embedding_client(self.provider)
            self.model = settings.LLAMA_EMBEDDING_MODEL
        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

    async def get_embedding(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Get embeddings for a single text or list of texts.

        Args:
            text: Single string or list of strings to get embeddings for

        Returns:
            numpy array of embeddings

        Raises:
            ValueError: If input text is empty
            Exception: For API or processing errors
        """
        if not text:
            raise ValueError("Input text cannot be empty")

        try:
            if self.provider in (EmbeddingProviderType.OPENAI, EmbeddingProviderType.LLAMA_API):
                return await generate_embedding_api(self.client, text, self.model)
            elif self.provider == EmbeddingProviderType.LLAMA_LOCAL:
                return await generate_llama_embedding_local(self.model, text)
                
        except Exception as e:
            logger.error(f"Error getting embeddings from {self.provider}: {str(e)}")
            raise
