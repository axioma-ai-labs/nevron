import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import chromadb
from chromadb.config import Settings
from loguru import logger

from src.core.config import settings


class MemoryBackend(ABC):
    """Abstract base class for memory backends."""

    @abstractmethod
    async def store(
        self,
        event: str,
        action: str,
        outcome: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store a memory entry with its embedding."""
        pass

    @abstractmethod
    async def search(self, query_vector: List[float], top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for similar memories using a query vector."""
        pass


class ChromaBackend(MemoryBackend):
    """ChromaDB-based memory backend."""

    def __init__(
        self,
        collection_name: str = settings.MEMORY_COLLECTION_NAME,
        persist_directory: str = settings.MEMORY_PERSIST_DIRECTORY,
    ):
        """Initialize ChromaDB backend."""
        self.client = chromadb.Client(
            Settings(persist_directory=persist_directory, is_persistent=True)
        )

        # Get or create collection
        try:
            self.collection = self.client.get_or_create_collection(
                name=collection_name, metadata={"hnsw:space": "cosine"}
            )
            logger.debug(f"Using ChromaDB collection: {collection_name}")
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {e}")
            raise

    async def store(
        self,
        event: str,
        action: str,
        outcome: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store a memory entry in ChromaDB.

        Args:
            event: Event description
            action: Action taken (is fromed from the ActionName enum)
            outcome: Result of the action
            embedding: Embedding of the memory
            metadata: Additional metadata to store
        """
        point_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        document = f"{event} {action} {outcome}"
        metadata = metadata or {}
        metadata.update(
            {"event": event, "action": action, "outcome": outcome, "timestamp": timestamp}
        )

        try:
            # Convert embedding to the expected type
            embedding_seq: Sequence[float] = embedding
            self.collection.add(
                ids=[point_id],
                embeddings=[embedding_seq],
                documents=[document],
                metadatas=[metadata],
            )
            logger.debug(f"Stored memory in ChromaDB: {point_id}")
        except Exception as e:
            logger.error(f"Error storing memory in ChromaDB: {e}")
            raise

    async def search(
        self, query_vector: List[float], top_k: int = 3, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories in ChromaDB with optional filters.

        Args:
            query_vector: Query vector
            top_k: Number of results to return
            filters: Optional metadata filters (e.g., {"type": "tweet"})

        Returns:
            List[Dict[str, Any]]: List of similar memories
        """
        try:
            query_vector_seq: Sequence[float] = query_vector

            where: Optional[Dict[str, Any]] = None
            if filters:
                where = {}
                for key, value in filters.items():
                    if isinstance(value, list):
                        where[key] = {"$in": value}
                    else:
                        where[key] = {"$eq": value}

            results = self.collection.query(
                query_embeddings=[query_vector_seq], n_results=top_k, where=where
            )

            # Format results to match the expected output
            formatted_results = []
            if results and "metadatas" in results and results["metadatas"]:
                metadatas = results["metadatas"]
                if isinstance(metadatas, list) and len(metadatas) > 0:
                    for metadata in metadatas[0]:
                        if isinstance(metadata, dict):
                            formatted_results.append(metadata)

            return formatted_results
        except Exception as e:
            logger.error(f"Error searching memory in ChromaDB: {e}")
            return []
