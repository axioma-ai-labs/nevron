"""Tri-Memory System - Unified interface for all memory types.

Provides a unified interface for interacting with:
- Episodic Memory: Time-indexed experiences
- Semantic Memory: Facts and knowledge
- Procedural Memory: Skills and patterns

Also manages memory consolidation in the background.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.config import settings
from src.memory.consolidation import ConsolidationResult, MemoryConsolidator
from src.memory.episodic import Episode, EpisodicMemory
from src.memory.procedural import ProceduralMemory, Skill
from src.memory.semantic import Concept, Fact, SemanticMemory


@dataclass
class MemoryRecall:
    """Combined recall result from all memory types."""

    query: str
    timestamp: datetime
    episodes: List[Episode]
    facts: List[Fact]
    concepts: List[Concept]
    skills: List[Skill]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "timestamp": self.timestamp.isoformat(),
            "episodes": [e.to_dict() for e in self.episodes],
            "facts": [f.to_dict() for f in self.facts],
            "concepts": [c.to_dict() for c in self.concepts],
            "skills": [s.to_dict() for s in self.skills],
        }

    def to_prompt_format(self) -> str:
        """Format recall results for use in prompts.

        Returns:
            Formatted string for LLM prompts
        """
        sections = []

        if self.episodes:
            episode_text = "\n".join(
                [
                    f"- [{e.timestamp.strftime('%Y-%m-%d %H:%M')}] {e.event}: {e.outcome}"
                    for e in self.episodes[:5]
                ]
            )
            sections.append(f"Recent Experiences:\n{episode_text}")

        if self.facts:
            fact_text = "\n".join([f"- {f.to_statement()}" for f in self.facts[:5]])
            sections.append(f"Known Facts:\n{fact_text}")

        if self.concepts:
            concept_text = "\n".join([f"- {c.name}: {c.description}" for c in self.concepts[:3]])
            sections.append(f"Related Concepts:\n{concept_text}")

        if self.skills:
            skill_text = "\n".join(
                [
                    f"- {s.name}: {s.description} (confidence: {s.confidence:.0%})"
                    for s in self.skills[:3]
                ]
            )
            sections.append(f"Available Skills:\n{skill_text}")

        if not sections:
            return "No relevant memories found."

        return "\n\n".join(sections)

    @property
    def has_results(self) -> bool:
        """Check if any results were found."""
        return bool(self.episodes or self.facts or self.concepts or self.skills)


class TriMemorySystem:
    """Unified interface for the tri-memory architecture.

    Provides:
    - Unified storage across memory types
    - Cross-memory recall
    - Background consolidation
    - Memory statistics and monitoring
    """

    def __init__(
        self,
        backend_type: str = settings.MEMORY_BACKEND_TYPE,
        enable_consolidation: bool = True,
        consolidation_interval: int = 3600,
    ):
        """Initialize the tri-memory system.

        Args:
            backend_type: Backend type for vector stores
            enable_consolidation: Whether to enable background consolidation
            consolidation_interval: Consolidation interval in seconds
        """
        # Initialize memory subsystems
        self.episodic = EpisodicMemory(
            backend_type=backend_type,
            collection_name="episodic_memory",
        )
        self.semantic = SemanticMemory(
            backend_type=backend_type,
            collection_name="semantic_memory",
        )
        self.procedural = ProceduralMemory(
            backend_type=backend_type,
            collection_name="procedural_memory",
        )

        # Initialize consolidator
        self.consolidator = MemoryConsolidator(
            episodic=self.episodic,
            semantic=self.semantic,
            procedural=self.procedural,
            interval_seconds=consolidation_interval,
        )

        self._enable_consolidation = enable_consolidation
        self._initialized = False

        logger.info("Tri-memory system initialized")

    async def start(self) -> None:
        """Start the memory system, including background consolidation."""
        if self._initialized:
            logger.warning("Tri-memory system already started")
            return

        if self._enable_consolidation:
            await self.consolidator.start()

        self._initialized = True
        logger.info("Tri-memory system started")

    async def stop(self) -> None:
        """Stop the memory system and cleanup."""
        if self._enable_consolidation:
            await self.consolidator.stop()

        self._initialized = False
        logger.info("Tri-memory system stopped")

    async def store_experience(
        self,
        event: str,
        action: str,
        outcome: str,
        context: Optional[Dict[str, Any]] = None,
        reward: float = 0.0,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Episode:
        """Store a new experience in episodic memory.

        Args:
            event: Description of what happened
            action: Action that was taken
            outcome: Result of the action
            context: Contextual information
            reward: Reward signal (-1.0 to 1.0)
            importance: Importance score (0.0 to 1.0)
            metadata: Additional metadata

        Returns:
            The stored Episode
        """
        return await self.episodic.store(
            event=event,
            action=action,
            outcome=outcome,
            context=context,
            emotional_valence=reward,
            importance=importance,
            metadata=metadata,
        )

    async def store_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float = 1.0,
        source: str = "",
    ) -> Fact:
        """Store a fact in semantic memory.

        Args:
            subject: Subject of the fact
            predicate: Relationship/verb
            obj: Object of the fact
            confidence: Confidence score
            source: Source of the fact

        Returns:
            The stored Fact
        """
        return await self.semantic.store_fact(
            subject=subject,
            predicate=predicate,
            obj=obj,
            confidence=confidence,
            source=source,
        )

    async def store_concept(
        self,
        name: str,
        concept_type: str,
        description: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Concept:
        """Store a concept in semantic memory.

        Args:
            name: Concept name
            concept_type: Type of concept
            description: Description
            properties: Additional properties

        Returns:
            The stored Concept
        """
        return await self.semantic.store_concept(
            name=name,
            concept_type=concept_type,
            description=description,
            properties=properties,
        )

    async def store_skill(
        self,
        name: str,
        description: str,
        trigger_pattern: str,
        action_sequence: List[Dict[str, Any]],
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None,
    ) -> Skill:
        """Store a skill in procedural memory.

        Args:
            name: Skill name
            description: What the skill does
            trigger_pattern: Pattern that triggers the skill
            action_sequence: Ordered actions
            preconditions: Required conditions
            postconditions: Expected outcomes

        Returns:
            The stored Skill
        """
        return await self.procedural.store_skill(
            name=name,
            description=description,
            trigger_pattern=trigger_pattern,
            action_sequence=action_sequence,
            preconditions=preconditions,
            postconditions=postconditions,
        )

    async def recall(
        self,
        query: str,
        top_k: int = 5,
        include_episodes: bool = True,
        include_facts: bool = True,
        include_concepts: bool = True,
        include_skills: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecall:
        """Recall relevant information from all memory types.

        Args:
            query: Search query
            top_k: Maximum results per memory type
            include_episodes: Include episodic memories
            include_facts: Include semantic facts
            include_concepts: Include semantic concepts
            include_skills: Include procedural skills
            context: Current context for skill matching

        Returns:
            MemoryRecall with results from all memory types
        """
        episodes: List[Episode] = []
        facts: List[Fact] = []
        concepts: List[Concept] = []
        skills: List[Skill] = []

        # Query each memory type
        if include_episodes:
            episodes = await self.episodic.recall(query, top_k=top_k)

        if include_facts or include_concepts:
            semantic_results = await self.semantic.query(query, top_k=top_k)
            for item in semantic_results:
                if isinstance(item, Fact) and include_facts:
                    facts.append(item)
                elif isinstance(item, Concept) and include_concepts:
                    concepts.append(item)

        if include_skills:
            skills = await self.procedural.retrieve_skill(
                task=query,
                context=context,
                top_k=top_k,
            )

        return MemoryRecall(
            query=query,
            timestamp=datetime.now(),
            episodes=episodes,
            facts=facts,
            concepts=concepts,
            skills=skills,
        )

    async def recall_for_action(
        self,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> MemoryRecall:
        """Recall memories relevant to taking a specific action.

        Prioritizes procedural memories (skills) and relevant experiences.

        Args:
            action: The action being considered
            context: Current context

        Returns:
            MemoryRecall optimized for action selection
        """
        return await self.recall(
            query=f"performing action: {action}",
            top_k=3,
            include_episodes=True,
            include_facts=True,
            include_concepts=False,
            include_skills=True,
            context=context,
        )

    async def recall_temporal(
        self,
        time_period: str,
    ) -> List[Episode]:
        """Recall experiences from a specific time period.

        Args:
            time_period: Natural language time period

        Returns:
            List of episodes from that time
        """
        return await self.episodic.recall_temporal(time_period)

    async def get_best_skill(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Skill]:
        """Get the best skill for a task.

        Args:
            task: Task description
            context: Current context

        Returns:
            Best matching Skill or None
        """
        skills = await self.procedural.retrieve_skill(
            task=task,
            context=context,
            top_k=1,
        )
        return skills[0] if skills else None

    async def record_skill_outcome(
        self,
        skill_id: str,
        success: bool,
    ) -> None:
        """Record the outcome of using a skill.

        Args:
            skill_id: ID of the skill used
            success: Whether execution was successful
        """
        await self.procedural.record_outcome(skill_id, success)

    async def consolidate_now(self) -> ConsolidationResult:
        """Trigger immediate memory consolidation.

        Returns:
            ConsolidationResult with statistics
        """
        return await self.consolidator.consolidate_once()

    def get_statistics(self) -> Dict[str, Any]:
        """Get memory system statistics.

        Returns:
            Dictionary with memory statistics
        """
        last_run = self.consolidator.get_last_run()
        return {
            "consolidation_enabled": self._enable_consolidation,
            "consolidation_running": self.consolidator.is_running,
            "last_consolidation": last_run.isoformat() if last_run else None,
            "consolidation_history_count": len(self.consolidator.get_history()),
            "total_skills": len(self.procedural.get_all_skills()),
            "total_concepts": len(self.semantic.get_all_concepts()),
        }

    async def __aenter__(self) -> "TriMemorySystem":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: Any,
        exc_val: Any,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.stop()


# Convenience function
def get_tri_memory_system(
    backend_type: str = settings.MEMORY_BACKEND_TYPE,
    enable_consolidation: bool = True,
) -> TriMemorySystem:
    """Get a tri-memory system instance.

    Args:
        backend_type: Backend type for vector stores
        enable_consolidation: Whether to enable consolidation

    Returns:
        TriMemorySystem instance
    """
    return TriMemorySystem(
        backend_type=backend_type,
        enable_consolidation=enable_consolidation,
    )
