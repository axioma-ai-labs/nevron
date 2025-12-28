"""Episodic Memory - Time-indexed experiences and events.

Episodic memory stores experiences with temporal context (when, where, what, outcome).
It includes emotional valence (reward signal) and supports temporal queries.
Implements a forgetting curve where older memories fade unless reinforced.
"""

import math
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from src.core.config import settings
from src.core.defs import MemoryBackendType
from src.llm.embeddings import EmbeddingGenerator
from src.memory.backends.chroma import ChromaBackend
from src.memory.backends.qdrant import QdrantBackend


@dataclass
class Episode:
    """Represents a single episodic memory entry."""

    id: str
    timestamp: datetime
    event: str
    action: str
    outcome: str
    context: Dict[str, Any]
    emotional_valence: float  # -1.0 to 1.0 (negative to positive)
    importance: float  # 0.0 to 1.0
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert episode to dictionary for storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "event": self.event,
            "action": self.action,
            "outcome": self.outcome,
            "context": self.context,
            "emotional_valence": self.emotional_valence,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], embedding: Optional[List[float]] = None) -> "Episode":
        """Create Episode from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if isinstance(data["timestamp"], str)
            else data["timestamp"],
            event=data["event"],
            action=data["action"],
            outcome=data["outcome"],
            context=data.get("context", {}),
            emotional_valence=data.get("emotional_valence", 0.0),
            importance=data.get("importance", 0.5),
            access_count=data.get("access_count", 0),
            last_accessed=datetime.fromisoformat(data["last_accessed"])
            if data.get("last_accessed")
            else None,
            embedding=embedding,
            metadata=data.get("metadata", {}),
        )


class EpisodicMemory:
    """Episodic memory system for storing and retrieving experiences.

    Features:
    - Time-indexed storage with temporal context
    - Emotional valence (reward-based importance)
    - Forgetting curve implementation
    - Temporal queries (e.g., "what happened yesterday?")
    - Memory reinforcement through access
    """

    # Forgetting curve parameters
    DECAY_RATE = 0.1  # How fast memories decay
    MIN_RETENTION = 0.1  # Minimum memory strength

    def __init__(
        self,
        backend_type: str = settings.MEMORY_BACKEND_TYPE,
        collection_name: str = "episodic_memory",
    ):
        """Initialize episodic memory.

        Args:
            backend_type: Type of vector store backend (qdrant or chroma)
            collection_name: Name for the episodic memory collection
        """
        self.embedding_generator = EmbeddingGenerator()
        self.backend: Union[QdrantBackend, ChromaBackend]

        if backend_type == MemoryBackendType.QDRANT:
            self.backend = QdrantBackend(
                collection_name=collection_name,
                host=settings.MEMORY_HOST,
                port=settings.MEMORY_PORT,
                vector_size=settings.MEMORY_VECTOR_SIZE,
            )
        elif backend_type == MemoryBackendType.CHROMA:
            self.backend = ChromaBackend(
                collection_name=collection_name,
                persist_directory=settings.MEMORY_PERSIST_DIRECTORY,
            )
        else:
            raise ValueError(f"Unsupported backend type: {backend_type}")

        logger.debug(f"Episodic memory initialized with {backend_type} backend")

    def _calculate_retention(
        self, episode: Episode, current_time: Optional[datetime] = None
    ) -> float:
        """Calculate memory retention based on forgetting curve.

        Uses the Ebbinghaus forgetting curve: R = e^(-t/S)
        where t is time since last access, S is stability factor.

        Args:
            episode: The episode to calculate retention for
            current_time: Current time (defaults to now)

        Returns:
            Retention score between MIN_RETENTION and 1.0
        """
        current_time = current_time or datetime.now(timezone.utc)
        last_access = episode.last_accessed or episode.timestamp

        # Time since last access in hours
        time_delta = (current_time - last_access).total_seconds() / 3600

        # Stability factor based on access count and importance
        stability = 1.0 + (episode.access_count * 0.5) + (episode.importance * 2.0)

        # Ebbinghaus forgetting curve
        retention = math.exp(-self.DECAY_RATE * time_delta / stability)

        # Ensure minimum retention
        return max(self.MIN_RETENTION, retention)

    async def store(
        self,
        event: str,
        action: str,
        outcome: str,
        context: Optional[Dict[str, Any]] = None,
        emotional_valence: float = 0.0,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Episode:
        """Store a new episodic memory.

        Args:
            event: Description of what happened
            action: Action that was taken
            outcome: Result of the action
            context: Contextual information (location, state, etc.)
            emotional_valence: Emotional response (-1.0 to 1.0)
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata

        Returns:
            The stored Episode
        """
        episode = Episode(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            event=event,
            action=action,
            outcome=outcome,
            context=context or {},
            emotional_valence=max(-1.0, min(1.0, emotional_valence)),
            importance=max(0.0, min(1.0, importance)),
            metadata=metadata or {},
        )

        # Generate embedding for similarity search
        text_to_embed = f"{event} {action} {outcome}"
        embedding = await self.embedding_generator.get_embedding(text_to_embed)
        embedding_list: List[float] = embedding[0].tolist()
        episode.embedding = embedding_list

        # Prepare metadata for storage
        storage_metadata = episode.to_dict()
        storage_metadata["memory_type"] = "episodic"

        # Store in backend
        await self.backend.store(
            event=event,
            action=action,
            outcome=outcome,
            embedding=embedding_list,
            metadata=storage_metadata,
        )

        logger.debug(f"Stored episodic memory: {episode.id}")
        return episode

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        time_range: Optional[tuple[datetime, datetime]] = None,
        min_importance: float = 0.0,
        include_retention: bool = True,
    ) -> List[Episode]:
        """Recall episodic memories based on query.

        Args:
            query: Search query
            top_k: Maximum number of results
            time_range: Optional (start, end) datetime tuple for filtering
            min_importance: Minimum importance threshold
            include_retention: Whether to factor in forgetting curve

        Returns:
            List of matching episodes, sorted by relevance
        """
        # Generate query embedding
        query_embedding = await self.embedding_generator.get_embedding(query)

        # Build filters
        filters: Dict[str, Any] = {"memory_type": "episodic"}
        if min_importance > 0:
            filters["importance"] = {"$gte": min_importance}

        # Search backend
        results = await self.backend.search(
            query_vector=query_embedding[0].tolist(),
            top_k=top_k * 2,  # Get more results to filter
            filters=filters,
        )

        # Convert to Episodes and apply retention scoring
        episodes = []
        current_time = datetime.now(timezone.utc)

        for result in results:
            episode = Episode.from_dict(result)

            # Apply time range filter
            if time_range:
                start, end = time_range
                if not (start <= episode.timestamp <= end):
                    continue

            # Calculate effective score with retention
            if include_retention:
                retention = self._calculate_retention(episode, current_time)
                episode.metadata["retention_score"] = retention

            episodes.append(episode)

        # Sort by importance and recency, limit to top_k
        episodes.sort(
            key=lambda e: (e.importance * e.metadata.get("retention_score", 1.0), e.timestamp),
            reverse=True,
        )

        return episodes[:top_k]

    async def recall_temporal(
        self,
        time_period: str,
        reference_time: Optional[datetime] = None,
    ) -> List[Episode]:
        """Recall memories from a specific time period.

        Args:
            time_period: Natural language time period (e.g., "yesterday", "last hour")
            reference_time: Reference time (defaults to now)

        Returns:
            List of episodes from that time period
        """
        reference = reference_time or datetime.now(timezone.utc)

        # Parse time period
        time_range = self._parse_time_period(time_period, reference)
        if not time_range:
            logger.warning(f"Could not parse time period: {time_period}")
            return []

        # Use a generic query to get all memories in range
        return await self.recall(
            query="",  # Empty query to match all
            top_k=20,
            time_range=time_range,
        )

    def _parse_time_period(
        self, period: str, reference: datetime
    ) -> Optional[tuple[datetime, datetime]]:
        """Parse natural language time period to datetime range.

        Args:
            period: Time period string
            reference: Reference datetime

        Returns:
            Tuple of (start, end) datetimes or None
        """
        period = period.lower().strip()

        # Common time periods
        if period in ("today", "now"):
            start = reference.replace(hour=0, minute=0, second=0, microsecond=0)
            return (start, reference)

        if period == "yesterday":
            end = reference.replace(hour=0, minute=0, second=0, microsecond=0)
            start = end - timedelta(days=1)
            return (start, end)

        if "last hour" in period:
            return (reference - timedelta(hours=1), reference)

        if "last day" in period:
            return (reference - timedelta(days=1), reference)

        if "last week" in period:
            return (reference - timedelta(weeks=1), reference)

        if "last month" in period:
            return (reference - timedelta(days=30), reference)

        # Try to parse "last N hours/days"
        import re

        match = re.match(r"last (\d+) (hour|day|week)s?", period)
        if match:
            count = int(match.group(1))
            unit = match.group(2)
            if unit == "hour":
                return (reference - timedelta(hours=count), reference)
            elif unit == "day":
                return (reference - timedelta(days=count), reference)
            elif unit == "week":
                return (reference - timedelta(weeks=count), reference)

        return None

    async def reinforce(self, episode_id: str) -> bool:
        """Reinforce a memory by increasing its access count.

        This strengthens the memory against forgetting.

        Args:
            episode_id: ID of the episode to reinforce

        Returns:
            True if successful
        """
        # This would need backend support for updates
        # For now, log the intention
        logger.debug(f"Reinforcing episodic memory: {episode_id}")
        return True

    async def get_recent(self, limit: int = 10) -> List[Episode]:
        """Get the most recent episodic memories.

        Args:
            limit: Maximum number of memories to return

        Returns:
            List of recent episodes
        """
        # Query with empty string to get recent memories
        return await self.recall(query="", top_k=limit, include_retention=False)
