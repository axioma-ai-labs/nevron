from typing import Any, Dict, List, Optional, Union

from loguru import logger
from openai import AsyncOpenAI

from src.core.config import settings
from src.core.defs import MemoryBackendType
from src.llm.embeddings import EmbeddingGenerator
from src.memory.backends.chroma import ChromaBackend
from src.memory.backends.qdrant import QdrantBackend


class MemoryModule:
    def __init__(
        self,
        backend_type: str = settings.MEMORY_BACKEND_TYPE,
        collection_name: str = settings.MEMORY_COLLECTION_NAME,
        host: str = settings.MEMORY_HOST,
        port: int = settings.MEMORY_PORT,
        vector_size: int = settings.MEMORY_VECTOR_SIZE,
        persist_directory: str = settings.MEMORY_PERSIST_DIRECTORY,
    ):
        """
        Initialize the memory module with the specified backend.

        Args:
            backend_type: Type of memory backend to use (qdrant or chroma)
            collection_name: Name of the vector store collection
            host: Vector store host for Qdrant. Will be ignored for ChromaDB.
            port: Vector store port for Qdrant. Will be ignored for ChromaDB.
            vector_size: Size of embedding vectors for Qdrant. Will be set automatically for ChromaDB.
            persist_directory: Directory to persist ChromaDB data. Will be ignored for Qdrant.
        """
        # Initialize embedding generator
        self.embedding_generator = EmbeddingGenerator()

        # Setup the vector store backend
        self.backend: Union[QdrantBackend, ChromaBackend]
        if backend_type == MemoryBackendType.QDRANT:
            self.backend = QdrantBackend(
                collection_name=collection_name,
                host=host,
                port=port,
                vector_size=vector_size,
            )
        elif backend_type == MemoryBackendType.CHROMA:
            self.backend = ChromaBackend(
                collection_name=collection_name,
                persist_directory=persist_directory,
            )
        else:
            raise ValueError(f"Unsupported backend type: {backend_type}")
        logger.debug(f"Memory backend initialized: {self.backend}")

    async def store(
        self, event: str, action: str, outcome: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store a memory entry with the specified backend.

        Args:
            event: Event description
            action: Action taken (is fromed from the ActionName enum)
            outcome: Result of the action
            metadata: Additional metadata to store
        """
        logger.debug(f"Storing memory: {event} {action} {outcome}")
        text_to_embed = f"{event} {action} {outcome}"
        embedding = await self.embedding_generator.get_embedding(text_to_embed)
        await self.backend.store(
            event=event,
            action=action,
            outcome=outcome,
            embedding=embedding[0].tolist(),
            metadata=metadata,
        )

    async def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search for similar memories using the specified backend.

        Args:
            query: Query to search for
            top_k: Number of results to return

        Returns:
            List[Dict[str, Any]]: List of similar memories
        """
        logger.debug(f"Searching for memories: {query}")
        query_vector = await self.embedding_generator.get_embedding(query)
        return await self.backend.search(
            query_vector=query_vector[0].tolist(),
            top_k=top_k,
        )


def get_memory_module(
    backend_type: str = settings.MEMORY_BACKEND_TYPE,
) -> MemoryModule:
    """Get a memory module instance with the specified backend."""
    return MemoryModule(backend_type=backend_type)
