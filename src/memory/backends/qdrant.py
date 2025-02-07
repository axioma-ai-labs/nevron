import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import Distance

from src.core.config import settings
from src.memory.backends.chroma import MemoryBackend


class QdrantBackend(MemoryBackend):
    """Qdrant-based memory backend."""

    def __init__(
        self,
        collection_name: str = settings.MEMORY_COLLECTION_NAME,
        host: str = settings.MEMORY_HOST,
        port: int = settings.MEMORY_PORT,
        vector_size: int = settings.MEMORY_VECTOR_SIZE,
    ):
        """Initialize Qdrant backend."""
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.vector_size = vector_size

        # Create collection if not exists
        try:
            self.client.get_collection(collection_name)
            logger.debug(f"Collection '{collection_name}' already exists in Qdrant.")
        except Exception:
            logger.debug(f"Creating collection '{collection_name}' in Qdrant.")
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size, distance=Distance.COSINE
                ),
            )

    async def store(
        self,
        event: str,
        action: str,
        outcome: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Store a memory entry in Qdrant.

        Args:
            event: Event description
            action: Action taken (is fromed from the ActionName enum)
            outcome: Result of the action
            embedding: Embedding of the memory
            metadata: Additional metadata to store
        """
        point_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        payload = {
            "event": event,
            "action": action,
            "outcome": outcome,
            "timestamp": timestamp,
        }
        if metadata:
            payload.update(metadata)

        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    qdrant_models.PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload=payload,
                    )
                ],
            )
            logger.debug(f"Stored memory in Qdrant: {point_id}")
        except Exception as e:
            logger.error(f"Error storing memory in Qdrant: {e}")
            raise

    async def search(
        self, query_vector: List[float], top_k: int = 3, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar memories in Qdrant with optional filters.

        Args:
            query_vector: Query vector
            top_k: Number of results to return
            filters: Optional metadata filters (e.g., {"type": "tweet"})

        Returns:
            List[Dict[str, Any]]: List of similar memories
        """
        try:
            qdrant_filters = None
            if filters:
                must_conditions: List[
                    Union[
                        qdrant_models.FieldCondition,
                        qdrant_models.IsEmptyCondition,
                        qdrant_models.IsNullCondition,
                        qdrant_models.HasIdCondition,
                        qdrant_models.HasVectorCondition,
                        qdrant_models.NestedCondition,
                        qdrant_models.Filter,
                    ]
                ] = []

                for key, value in filters.items():
                    if isinstance(value, list):
                        must_conditions.append(
                            qdrant_models.FieldCondition(
                                key=key, match=qdrant_models.MatchAny(any=value)
                            )
                        )
                    else:
                        must_conditions.append(
                            qdrant_models.FieldCondition(
                                key=key, match=qdrant_models.MatchValue(value=value)
                            )
                        )

                qdrant_filters = qdrant_models.Filter(must=must_conditions)

            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=qdrant_filters,
            )
            return [point.payload for point in search_result if point.payload]
        except Exception as e:
            logger.error(f"Error searching memory in Qdrant: {e}")
            return []
