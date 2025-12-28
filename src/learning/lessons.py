"""Lesson Storage - Store and retrieve learned lessons.

Lessons are structured insights learned from experience that can be
applied to future decisions. They link to procedural memory for persistence.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from src.core.config import settings
from src.core.defs import MemoryBackendType
from src.llm.embeddings import EmbeddingGenerator
from src.memory.backends.chroma import ChromaBackend
from src.memory.backends.qdrant import QdrantBackend


@dataclass
class Lesson:
    """Represents a learned lesson from experience."""

    id: str
    summary: str  # Brief summary of the lesson
    situation: str  # What context was this learned in?
    action: str  # The action that was taken
    what_went_wrong: str  # What failed or was suboptimal
    better_approach: str  # What should be done instead
    learned_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reinforcement_count: int = 0  # How many times validated
    context_key: Optional[str] = None  # Context fingerprint
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def age_days(self) -> float:
        """Get age of lesson in days."""
        delta = datetime.now(timezone.utc) - self.learned_at
        return delta.total_seconds() / 86400

    @property
    def reliability(self) -> float:
        """Calculate reliability score based on reinforcement and age."""
        # Base on reinforcement count
        reinforcement_factor = min(1.0, 0.5 + 0.1 * self.reinforcement_count)

        # Decay slightly with age (but reinforced lessons decay slower)
        decay_rate = 0.01 / (1 + self.reinforcement_count * 0.5)
        age_factor = max(0.3, 1.0 - decay_rate * self.age_days)

        return self.confidence * reinforcement_factor * age_factor

    def reinforce(self) -> None:
        """Mark this lesson as validated again."""
        self.reinforcement_count += 1
        # Boost confidence slightly
        self.confidence = min(1.0, self.confidence + 0.05)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "summary": self.summary,
            "situation": self.situation,
            "action": self.action,
            "what_went_wrong": self.what_went_wrong,
            "better_approach": self.better_approach,
            "learned_at": self.learned_at.isoformat(),
            "reinforcement_count": self.reinforcement_count,
            "context_key": self.context_key,
            "tags": self.tags,
            "confidence": self.confidence,
            "reliability": self.reliability,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Lesson":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            summary=data["summary"],
            situation=data.get("situation", ""),
            action=data.get("action", ""),
            what_went_wrong=data.get("what_went_wrong", ""),
            better_approach=data.get("better_approach", ""),
            learned_at=datetime.fromisoformat(data["learned_at"])
            if isinstance(data.get("learned_at"), str)
            else data.get("learned_at", datetime.now(timezone.utc)),
            reinforcement_count=data.get("reinforcement_count", 0),
            context_key=data.get("context_key"),
            tags=data.get("tags", []),
            confidence=data.get("confidence", 0.7),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def create(
        cls,
        summary: str,
        situation: str,
        action: str,
        what_went_wrong: str,
        better_approach: str,
        context_key: Optional[str] = None,
        tags: Optional[List[str]] = None,
        confidence: float = 0.7,
    ) -> "Lesson":
        """Factory method to create a lesson.

        Args:
            summary: Brief summary
            situation: Context description
            action: Action that was taken
            what_went_wrong: What failed
            better_approach: What to do instead
            context_key: Optional context fingerprint
            tags: Optional tags
            confidence: Initial confidence

        Returns:
            New Lesson instance
        """
        return cls(
            id=str(uuid.uuid4()),
            summary=summary,
            situation=situation,
            action=action,
            what_went_wrong=what_went_wrong,
            better_approach=better_approach,
            context_key=context_key,
            tags=tags or [],
            confidence=confidence,
        )

    def __str__(self) -> str:
        """String representation."""
        return f"Lesson({self.summary[:50]}... [{self.action}])"


class LessonRepository:
    """Repository for storing and retrieving lessons.

    Uses vector storage for semantic search and retrieval.

    Features:
    - Semantic search for relevant lessons
    - Context-based filtering
    - Reinforcement tracking
    - Tag-based organization
    """

    def __init__(
        self,
        backend_type: str = settings.MEMORY_BACKEND_TYPE,
        collection_name: str = "lessons",
    ):
        """Initialize lesson repository.

        Args:
            backend_type: Vector store backend type
            collection_name: Name for the lessons collection
        """
        self._embedding_generator = EmbeddingGenerator()
        self._backend: Union[QdrantBackend, ChromaBackend]

        if backend_type == MemoryBackendType.QDRANT:
            self._backend = QdrantBackend(
                collection_name=collection_name,
                host=settings.MEMORY_HOST,
                port=settings.MEMORY_PORT,
                vector_size=settings.MEMORY_VECTOR_SIZE,
            )
        elif backend_type == MemoryBackendType.CHROMA:
            self._backend = ChromaBackend(
                collection_name=collection_name,
                persist_directory=settings.MEMORY_PERSIST_DIRECTORY,
            )
        else:
            raise ValueError(f"Unsupported backend type: {backend_type}")

        # In-memory cache for quick access
        self._cache: Dict[str, Lesson] = {}

        # Index by action for fast lookup
        self._by_action: Dict[str, List[str]] = {}  # action -> [lesson_id]

        # Index by context key
        self._by_context: Dict[str, List[str]] = {}  # context_key -> [lesson_id]

        logger.debug(f"LessonRepository initialized with {backend_type} backend")

    async def store(self, lesson: Lesson) -> str:
        """Store a lesson.

        Args:
            lesson: Lesson to store

        Returns:
            Lesson ID
        """
        # Check for similar existing lessons
        existing = await self._find_similar(lesson)
        if existing:
            # Reinforce existing lesson instead of creating duplicate
            existing.reinforce()
            await self._update_in_backend(existing)
            logger.debug(f"Reinforced existing lesson: {existing.id}")
            return existing.id

        # Generate embedding for semantic search
        text = self._lesson_to_text(lesson)
        embedding = await self._embedding_generator.get_embedding(text)

        # Prepare metadata
        metadata = lesson.to_dict()
        metadata["memory_type"] = "lesson"

        # Store in backend
        await self._backend.store(
            event=lesson.summary,
            action="store_lesson",
            outcome=lesson.better_approach,
            embedding=embedding[0].tolist(),
            metadata=metadata,
        )

        # Update cache and indices
        self._cache[lesson.id] = lesson
        self._index_lesson(lesson)

        logger.debug(f"Stored lesson: {lesson.summary}")
        return lesson.id

    async def _find_similar(
        self,
        lesson: Lesson,
        threshold: float = 0.9,
    ) -> Optional[Lesson]:
        """Find a similar existing lesson.

        Args:
            lesson: Lesson to compare
            threshold: Similarity threshold

        Returns:
            Similar Lesson or None
        """
        # Quick check by action first
        if lesson.action in self._by_action:
            for lesson_id in self._by_action[lesson.action]:
                cached = self._cache.get(lesson_id)
                if cached and self._are_similar(lesson, cached):
                    return cached

        return None

    def _are_similar(self, a: Lesson, b: Lesson) -> bool:
        """Check if two lessons are similar enough to merge.

        Args:
            a: First lesson
            b: Second lesson

        Returns:
            True if should be merged
        """
        # Same action and similar context
        if a.action != b.action:
            return False

        # Similar situation
        if a.context_key and b.context_key:
            if a.context_key != b.context_key:
                return False

        # Similar what went wrong (simple check)
        a_words = set(a.what_went_wrong.lower().split())
        b_words = set(b.what_went_wrong.lower().split())
        if len(a_words & b_words) / max(len(a_words | b_words), 1) < 0.5:
            return False

        return True

    async def _update_in_backend(self, lesson: Lesson) -> None:
        """Update a lesson in the backend.

        Args:
            lesson: Updated lesson
        """
        # Re-store with updated metadata
        text = self._lesson_to_text(lesson)
        embedding = await self._embedding_generator.get_embedding(text)

        metadata = lesson.to_dict()
        metadata["memory_type"] = "lesson"

        await self._backend.store(
            event=lesson.summary,
            action="update_lesson",
            outcome=lesson.better_approach,
            embedding=embedding[0].tolist(),
            metadata=metadata,
        )

        self._cache[lesson.id] = lesson

    def _lesson_to_text(self, lesson: Lesson) -> str:
        """Convert lesson to searchable text.

        Args:
            lesson: Lesson to convert

        Returns:
            Text representation
        """
        parts = [
            lesson.summary,
            f"Situation: {lesson.situation}",
            f"Action: {lesson.action}",
            f"Problem: {lesson.what_went_wrong}",
            f"Solution: {lesson.better_approach}",
        ]
        if lesson.tags:
            parts.append(f"Tags: {', '.join(lesson.tags)}")
        return " | ".join(parts)

    def _index_lesson(self, lesson: Lesson) -> None:
        """Add lesson to indices.

        Args:
            lesson: Lesson to index
        """
        # Index by action
        if lesson.action not in self._by_action:
            self._by_action[lesson.action] = []
        if lesson.id not in self._by_action[lesson.action]:
            self._by_action[lesson.action].append(lesson.id)

        # Index by context
        if lesson.context_key:
            if lesson.context_key not in self._by_context:
                self._by_context[lesson.context_key] = []
            if lesson.id not in self._by_context[lesson.context_key]:
                self._by_context[lesson.context_key].append(lesson.id)

    async def find_relevant(
        self,
        context: Dict[str, Any],
        top_k: int = 5,
        min_reliability: float = 0.3,
    ) -> List[Lesson]:
        """Find lessons applicable to current situation.

        Args:
            context: Current context/state
            top_k: Maximum lessons to return
            min_reliability: Minimum reliability threshold

        Returns:
            List of relevant Lessons
        """
        # Build query from context
        query_parts = []
        if "goal" in context:
            query_parts.append(f"Goal: {context['goal']}")
        if "action" in context:
            query_parts.append(f"Action: {context['action']}")
        if "error" in context:
            query_parts.append(f"Error: {context['error']}")
        if "task" in context:
            query_parts.append(f"Task: {context['task']}")

        if not query_parts:
            query_parts.append(str(context))

        query = " | ".join(query_parts)
        query_embedding = await self._embedding_generator.get_embedding(query)

        # Search backend
        results = await self._backend.search(
            query_vector=query_embedding[0].tolist(),
            top_k=top_k * 2,  # Get more to filter
            filters={"memory_type": "lesson"},
        )

        # Convert and filter
        lessons = []
        for result in results:
            lesson = Lesson.from_dict(result)

            # Check reliability
            if lesson.reliability < min_reliability:
                continue

            lessons.append(lesson)

            # Update cache
            self._cache[lesson.id] = lesson
            self._index_lesson(lesson)

        # Sort by reliability
        lessons.sort(key=lambda lesson: lesson.reliability, reverse=True)

        return lessons[:top_k]

    async def find_by_action(
        self,
        action: str,
        top_k: int = 5,
    ) -> List[Lesson]:
        """Find lessons for a specific action.

        Args:
            action: Action name
            top_k: Maximum lessons

        Returns:
            List of lessons for this action
        """
        # Check cache first
        if action in self._by_action:
            lessons = [self._cache[lid] for lid in self._by_action[action] if lid in self._cache]
            lessons.sort(key=lambda lesson: lesson.reliability, reverse=True)
            return lessons[:top_k]

        # Search backend
        results = await self._backend.search(
            query_vector=(await self._embedding_generator.get_embedding(f"Action: {action}"))[
                0
            ].tolist(),
            top_k=top_k,
            filters={"memory_type": "lesson"},
        )

        lessons = []
        for result in results:
            if result.get("action") == action:
                lesson = Lesson.from_dict(result)
                lessons.append(lesson)
                self._cache[lesson.id] = lesson
                self._index_lesson(lesson)

        return lessons

    async def find_by_context(
        self,
        context_key: str,
        top_k: int = 5,
    ) -> List[Lesson]:
        """Find lessons for a specific context.

        Args:
            context_key: Context fingerprint
            top_k: Maximum lessons

        Returns:
            List of lessons for this context
        """
        if context_key in self._by_context:
            lessons = [
                self._cache[lid] for lid in self._by_context[context_key] if lid in self._cache
            ]
            lessons.sort(key=lambda lesson: lesson.reliability, reverse=True)
            return lessons[:top_k]

        return []

    def get_lesson(self, lesson_id: str) -> Optional[Lesson]:
        """Get a lesson by ID.

        Args:
            lesson_id: Lesson ID

        Returns:
            Lesson or None
        """
        return self._cache.get(lesson_id)

    def get_all_lessons(self) -> List[Lesson]:
        """Get all cached lessons.

        Returns:
            List of all lessons
        """
        return list(self._cache.values())

    def get_lessons_by_tag(self, tag: str) -> List[Lesson]:
        """Get lessons with a specific tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of lessons with this tag
        """
        return [lesson for lesson in self._cache.values() if tag in lesson.tags]

    async def reinforce_lesson(self, lesson_id: str) -> bool:
        """Reinforce a lesson (mark as validated).

        Args:
            lesson_id: Lesson ID

        Returns:
            True if lesson was reinforced
        """
        lesson = self._cache.get(lesson_id)
        if not lesson:
            return False

        lesson.reinforce()
        await self._update_in_backend(lesson)

        logger.debug(f"Reinforced lesson {lesson_id}, count: {lesson.reinforcement_count}")
        return True

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()
        self._by_action.clear()
        self._by_context.clear()
        logger.debug("LessonRepository cache cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics.

        Returns:
            Statistics dictionary
        """
        lessons = list(self._cache.values())

        if not lessons:
            return {
                "total_lessons": 0,
                "avg_reinforcement": 0,
                "avg_reliability": 0,
                "actions_covered": 0,
                "contexts_covered": 0,
            }

        return {
            "total_lessons": len(lessons),
            "avg_reinforcement": sum(lsn.reinforcement_count for lsn in lessons) / len(lessons),
            "avg_reliability": sum(lsn.reliability for lsn in lessons) / len(lessons),
            "actions_covered": len(self._by_action),
            "contexts_covered": len(self._by_context),
            "most_reinforced": max(lessons, key=lambda lsn: lsn.reinforcement_count).summary
            if lessons
            else None,
        }
