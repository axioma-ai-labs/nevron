import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from qdrant_client.http.models import Distance

from src.core.config import settings
from src.llm.embeddings import EmbeddingGenerator
from src.llm.oai_client import get_oai_client


class MemoryModule:
    def __init__(
        self,
        openai_client: AsyncOpenAI = get_oai_client(),
        collection_name: str = settings.MEMORY_COLLECTION_NAME or "agent_memory",
        host: str = settings.MEMORY_HOST or "localhost",
        port: int = settings.MEMORY_PORT or 6333,
        vector_size: int = settings.MEMORY_VECTOR_SIZE or 1536,
    ):
        """
        Initializes the connection to Qdrant and ensures that
        the specified collection exists.

        Args:
            openai_client: AsyncOpenAI client instance
            collection_name: Name of the Qdrant collection
            host: Qdrant host
            port: Qdrant port
            vector_size: Size of embedding vectors
        ## Memory Module Configuration

            The `MemoryModule` is now configurable via the `settings` module. Update the following settings in `core/config.py`:

            - `MEMORY_COLLECTION_NAME`: Name of the Qdrant collection.
            - `MEMORY_HOST`: Host of the Qdrant service.
            - `MEMORY_PORT`: Port of the Qdrant service.
            - `MEMORY_VECTOR_SIZE`: Size of the embedding vectors.

            Example:
            MEMORY_COLLECTION_NAME = "custom_memory"
            MEMORY_HOST = "qdrant.example.com"
            MEMORY_PORT = 6333
            MEMORY_VECTOR_SIZE = 1536
        """

        settings.validate_memory_settings(
            {
                "MEMORY_COLLECTION_NAME": collection_name,
                "MEMORY_HOST": host,
                "MEMORY_PORT": port,
                "MEMORY_VECTOR_SIZE": vector_size,
            },
            {
                "MEMORY_COLLECTION_NAME": str,
                "MEMORY_HOST": str,
                "MEMORY_PORT": int,
                "MEMORY_VECTOR_SIZE": int,
            },
        )
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.embedding_generator = EmbeddingGenerator(openai_client)

        # Create collection if not exists
        try:
            self.client.get_collection(collection_name)
            logger.info(f"Collection '{collection_name}' already exists in Qdrant.")
        except Exception:
            logger.info(f"Creating collection '{collection_name}' in Qdrant.")
            self.client.recreate_collection(
                collection_name=collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size, distance=Distance.COSINE
                ),
            )

    async def store(
        self, event: str, action: str, outcome: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Embed the event-action-outcome triple and store it in Qdrant with optional metadata.
        """
        text_to_embed = f"{event} {action} {outcome}"
        embedding = await self.embedding_generator.get_embedding(text_to_embed)
        point_id = str(uuid.uuid4())  # unique identifier
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
                        vector=embedding[0].tolist(),
                        payload=payload,
                    )
                ],
            )
            logger.info(f"Stored memory in Qdrant: {point_id}")
        except Exception as e:
            logger.error(f"Error storing memory: {e}")

    async def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Search the memory by embedding the query and retrieving the top_k most similar points.
        Returns a list of payloads with event-action-outcome and metadata.
        """
        query_vector = await self.embedding_generator.get_embedding(query)
        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector[0].tolist(),
                limit=top_k,
            )
            results = []
            for scored_point in search_result:
                if scored_point.payload:
                    results.append(scored_point.payload)
            return results
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []


def get_memory_module(openai_client: AsyncOpenAI = get_oai_client()) -> MemoryModule:
    """Get a memory module instance."""
    return MemoryModule(openai_client=openai_client)
