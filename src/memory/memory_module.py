from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from src.core.config import settings
from src.core.defs import MemoryBackendType
from src.llm.embeddings import EmbeddingGenerator
<<<<<<< HEAD
from src.llm.llm import LLM
=======
>>>>>>> e4f134c (Integrate llama embeddings (#116))
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
<<<<<<< HEAD
        # Initialize LLM
        self.llm = LLM()
=======
>>>>>>> e4f134c (Integrate llama embeddings (#116))

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

    async def llm_filter(
        self, raw_data: str, metadata_filters: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Use LLM to filter and summarize raw data based on metadata filters.

        Args:
            raw_data: The raw data to evaluate
            metadata_filters: Filters to consider when evaluating importance (e.g., {"type": "...", "topic": "Project X"})

        Returns:
            Optional[str]: Summary if data is worth remembering, None otherwise
        """
        filter_context = ""
        if metadata_filters:
            filter_context = " Consider these important criteria when evaluating:\n"
            for key, value in metadata_filters.items():
                if isinstance(value, list):
                    filter_context += f"- {key}: {', '.join(value)}\n"
                else:
                    filter_context += f"- {key}: {value}\n"

        prompt = (
            f"Evaluate this data for its importance and relevance. {filter_context}\n"
            f"1. Analyze the content and context of the data\n"
            f"2. Compare it against the evaluation criteria\n"
            f"3. If it's relevant and worth remembering, extract the most important information as a concise summary\n"
            f"4. If it's not relevant or important, return exactly 'None'\n\n"
            f"Data to evaluate:\n{raw_data}\n\n"
            f"Your response should be either:\n"
            f"- A concise summary of the most important information (if relevant)\n"
            f"- Exactly 'None' (if not relevant or important)\n"
            f"Do not include any additional comments or explanations in your response."
        )

        response = await self.llm.generate_response([{"role": "user", "content": prompt}])
        return response if response != "None" else None

    async def filter_and_store(
        self, raw_data: str, data_type: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Filter raw data using LLM and store only the meaningful summary.

        Args:
            raw_data: The raw data to evaluate
            data_type: Type of data (e.g., tweet, news finding, slack post etc.)
            metadata: Additional metadata to store with the memory
        """
        summary = await self.llm_filter(raw_data)
        if summary:
            # Add timestamp and type to metadata
            metadata = metadata or {}
            metadata.update(
                {"timestamp": datetime.now(timezone.utc).isoformat(), "type": data_type}
            )
            await self.store(
                event="Filtered Memory", action="Store", outcome=summary, metadata=metadata
            )

    async def store(
        self, event: str, action: str, outcome: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store a memory entry with the specified backend.

        Args:
            event: Event description
            action: Action taken
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

    async def search(
        self, query: str, top_k: int = 3, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories with optional filters.

        Args:
            query: Query to search for
            top_k: Number of results to return
            filters: Optional metadata filters (e.g., {"type": "tweet", "topic": "Project X"})

        Returns:
            List[Dict[str, Any]]: List of similar memories
        """
        logger.debug(f"Searching for memories: {query}")
        query_vector = await self.embedding_generator.get_embedding(query)
        return await self.backend.search(
            query_vector=query_vector[0].tolist(), top_k=top_k, filters=filters
        )


def get_memory_module(
    backend_type: str = settings.MEMORY_BACKEND_TYPE,
) -> MemoryModule:
    """Get a memory module instance with the specified backend."""
    return MemoryModule(backend_type=backend_type)
