"""Procedural Memory - Skills, patterns, and learned behaviors.

Procedural memory stores successful action patterns as reusable "skills".
It supports pattern matching for skill retrieval and skill composition.
Skills are learned from repeated successful episodic experiences.
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
class Skill:
    """Represents a learned skill/procedure."""

    id: str
    name: str
    description: str
    trigger_pattern: str  # Pattern that activates this skill
    action_sequence: List[Dict[str, Any]]  # Ordered list of actions
    preconditions: List[str]  # Conditions that must be true
    postconditions: List[str]  # Expected outcomes
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source_episodes: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def confidence(self) -> float:
        """Calculate confidence based on success/failure ratio."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 0.5  # Neutral confidence for unused skills
        return self.success_count / total

    @property
    def usage_count(self) -> int:
        """Total number of times this skill was used."""
        return self.success_count + self.failure_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert skill to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_pattern": self.trigger_pattern,
            "action_sequence": self.action_sequence,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "created_at": self.created_at.isoformat(),
            "source_episodes": self.source_episodes,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Skill":
        """Create Skill from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description", ""),
            trigger_pattern=data.get("trigger_pattern", ""),
            action_sequence=data.get("action_sequence", []),
            preconditions=data.get("preconditions", []),
            postconditions=data.get("postconditions", []),
            success_count=data.get("success_count", 0),
            failure_count=data.get("failure_count", 0),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.now(timezone.utc)),
            source_episodes=data.get("source_episodes", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ActionPattern:
    """Represents a pattern of actions that may become a skill."""

    id: str
    actions: List[Dict[str, Any]]
    context: Dict[str, Any]
    outcome: str
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary."""
        return {
            "id": self.id,
            "actions": self.actions,
            "context": self.context,
            "outcome": self.outcome,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
        }


class ProceduralMemory:
    """Procedural memory system for storing and retrieving skills.

    Features:
    - Skill storage with action sequences
    - Pattern matching for skill retrieval
    - Confidence scoring based on success history
    - Skill composition for complex tasks
    - Learning from episodic experiences
    """

    # Minimum observations to promote pattern to skill
    MIN_OBSERVATIONS_FOR_SKILL = 3
    # Minimum success rate to keep a skill
    MIN_SKILL_CONFIDENCE = 0.3

    def __init__(
        self,
        backend_type: str = settings.MEMORY_BACKEND_TYPE,
        collection_name: str = "procedural_memory",
    ):
        """Initialize procedural memory.

        Args:
            backend_type: Type of vector store backend
            collection_name: Name for the procedural memory collection
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

        # In-memory skill cache for fast access
        self._skills: Dict[str, Skill] = {}
        # Patterns observed but not yet promoted to skills
        self._pending_patterns: Dict[str, List[ActionPattern]] = {}  # pattern_key -> observations

        logger.debug(f"Procedural memory initialized with {backend_type} backend")

    async def store_skill(
        self,
        name: str,
        description: str,
        trigger_pattern: str,
        action_sequence: List[Dict[str, Any]],
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None,
        source_episodes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Skill:
        """Store a new skill in procedural memory.

        Args:
            name: Name of the skill
            description: Description of what the skill does
            trigger_pattern: Pattern that triggers this skill
            action_sequence: Ordered list of actions
            preconditions: Conditions required before execution
            postconditions: Expected outcomes
            source_episodes: Episode IDs that contributed to learning
            metadata: Additional metadata

        Returns:
            The stored Skill
        """
        skill = Skill(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            trigger_pattern=trigger_pattern,
            action_sequence=action_sequence,
            preconditions=preconditions or [],
            postconditions=postconditions or [],
            source_episodes=source_episodes or [],
            metadata=metadata or {},
        )

        # Generate embedding for the skill
        text = f"{name}: {description}. Trigger: {trigger_pattern}"
        embedding = await self.embedding_generator.get_embedding(text)

        # Prepare metadata for storage
        storage_metadata = skill.to_dict()
        storage_metadata["memory_type"] = "procedural_skill"

        # Store in backend
        await self.backend.store(
            event=name,
            action="store_skill",
            outcome=description,
            embedding=embedding[0].tolist(),
            metadata=storage_metadata,
        )

        # Update in-memory cache
        self._skills[skill.id] = skill

        logger.debug(f"Stored procedural skill: {name}")
        return skill

    async def retrieve_skill(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        top_k: int = 3,
        min_confidence: float = 0.3,
    ) -> List[Skill]:
        """Retrieve skills relevant to a task.

        Args:
            task: Description of the task to accomplish
            context: Current context/state
            top_k: Maximum number of skills to return
            min_confidence: Minimum confidence threshold

        Returns:
            List of matching Skills, sorted by relevance and confidence
        """
        # Generate query embedding
        query = task
        if context:
            query += f" Context: {context}"
        query_embedding = await self.embedding_generator.get_embedding(query)

        # Build filters
        filters: Dict[str, Any] = {"memory_type": "procedural_skill"}

        # Search backend
        results = await self.backend.search(
            query_vector=query_embedding[0].tolist(),
            top_k=top_k * 2,  # Get more to filter
            filters=filters,
        )

        # Convert to Skills and filter by confidence
        skills = []
        for result in results:
            skill = Skill.from_dict(result)

            # Check confidence threshold
            if skill.confidence < min_confidence:
                continue

            # Check preconditions if context provided
            if context and skill.preconditions:
                if not self._check_preconditions(skill.preconditions, context):
                    continue

            skills.append(skill)

        # Sort by confidence and relevance
        skills.sort(key=lambda s: s.confidence, reverse=True)

        return skills[:top_k]

    def _check_preconditions(self, preconditions: List[str], context: Dict[str, Any]) -> bool:
        """Check if preconditions are met.

        Args:
            preconditions: List of precondition strings
            context: Current context

        Returns:
            True if all preconditions are met
        """
        # Simple string matching for now
        # Could be enhanced with more sophisticated logic
        for condition in preconditions:
            condition_lower = condition.lower()
            found = False
            for key, value in context.items():
                if condition_lower in str(key).lower() or condition_lower in str(value).lower():
                    found = True
                    break
            if not found:
                return False
        return True

    async def record_outcome(
        self,
        skill_id: str,
        success: bool,
        outcome_details: Optional[str] = None,
    ) -> bool:
        """Record the outcome of using a skill.

        This updates the skill's confidence based on success/failure.

        Args:
            skill_id: ID of the skill that was used
            success: Whether the skill execution was successful
            outcome_details: Optional details about the outcome

        Returns:
            True if the record was updated
        """
        skill = self._skills.get(skill_id)
        if not skill:
            logger.warning(f"Skill not found: {skill_id}")
            return False

        # Update counts
        if success:
            skill.success_count += 1
        else:
            skill.failure_count += 1

        skill.last_used = datetime.now(timezone.utc)

        # Check if skill should be deprecated
        if skill.usage_count >= 5 and skill.confidence < self.MIN_SKILL_CONFIDENCE:
            logger.info(f"Skill {skill.name} confidence too low, marking for review")
            skill.metadata["needs_review"] = True

        logger.debug(
            f"Recorded {'success' if success else 'failure'} for skill {skill.name}, "
            f"new confidence: {skill.confidence:.2f}"
        )
        return True

    async def observe_pattern(
        self,
        actions: List[Dict[str, Any]],
        context: Dict[str, Any],
        outcome: str,
        success: bool,
    ) -> Optional[Skill]:
        """Observe an action pattern that might become a skill.

        If a pattern is observed enough times with success, it becomes a skill.

        Args:
            actions: List of actions in the pattern
            context: Context in which the pattern occurred
            outcome: Result of the actions
            success: Whether the pattern was successful

        Returns:
            Skill if pattern was promoted, None otherwise
        """
        # Create pattern key based on action sequence
        action_key = "_".join([str(a.get("action", "")) for a in actions])
        pattern = ActionPattern(
            id=str(uuid.uuid4()),
            actions=actions,
            context=context,
            outcome=outcome,
            success=success,
        )

        # Add to pending patterns
        if action_key not in self._pending_patterns:
            self._pending_patterns[action_key] = []
        self._pending_patterns[action_key].append(pattern)

        # Check if we have enough observations to create a skill
        observations = self._pending_patterns[action_key]
        if len(observations) >= self.MIN_OBSERVATIONS_FOR_SKILL:
            # Calculate success rate
            successes = sum(1 for p in observations if p.success)
            success_rate = successes / len(observations)

            if success_rate >= self.MIN_SKILL_CONFIDENCE:
                # Promote to skill
                skill = await self._promote_to_skill(action_key, observations)
                # Clear pending patterns
                del self._pending_patterns[action_key]
                return skill
            else:
                logger.debug(
                    f"Pattern {action_key} has low success rate ({success_rate:.2f}), "
                    f"not promoting to skill"
                )

        return None

    async def _promote_to_skill(
        self,
        pattern_key: str,
        observations: List[ActionPattern],
    ) -> Skill:
        """Promote a pattern to a skill.

        Args:
            pattern_key: Key identifying the pattern
            observations: List of observations

        Returns:
            The created Skill
        """
        # Get the most common action sequence
        if not observations:
            raise ValueError("No observations to promote")

        # Use first observation as template
        template = observations[0]

        # Generate name and description
        action_names = [str(a.get("action", "unknown")) for a in template.actions]
        name = f"skill_{pattern_key[:20]}"
        description = f"Learned skill: {' -> '.join(action_names)}"

        # Create skill
        skill = await self.store_skill(
            name=name,
            description=description,
            trigger_pattern=pattern_key,
            action_sequence=template.actions,
            preconditions=[],  # Could extract from context
            postconditions=[template.outcome],
            source_episodes=[p.id for p in observations],
            metadata={"auto_learned": True, "observation_count": len(observations)},
        )

        # Set initial success/failure counts
        skill.success_count = sum(1 for p in observations if p.success)
        skill.failure_count = sum(1 for p in observations if not p.success)

        logger.info(f"Promoted pattern to skill: {name} (confidence: {skill.confidence:.2f})")
        return skill

    async def compose_skills(
        self,
        skill_ids: List[str],
        name: str,
        description: str,
    ) -> Optional[Skill]:
        """Compose multiple skills into a new composite skill.

        Args:
            skill_ids: IDs of skills to compose
            name: Name for the new composite skill
            description: Description of the composite skill

        Returns:
            The composite Skill or None if composition failed
        """
        # Get all skills
        skills = [self._skills.get(sid) for sid in skill_ids]
        skills = [s for s in skills if s is not None]

        # Filter out None values
        valid_skills: List[Skill] = [s for s in skills if s is not None]

        if len(valid_skills) < 2:
            logger.warning("Need at least 2 valid skills to compose")
            return None

        # Combine action sequences
        combined_actions: List[Dict[str, Any]] = []
        for skill in valid_skills:
            combined_actions.extend(skill.action_sequence)

        # Combine pre/postconditions
        preconditions = valid_skills[0].preconditions
        postconditions = valid_skills[-1].postconditions

        # Create composite skill
        trigger = " + ".join([s.trigger_pattern for s in valid_skills])

        composite = await self.store_skill(
            name=name,
            description=description,
            trigger_pattern=trigger,
            action_sequence=combined_actions,
            preconditions=preconditions,
            postconditions=postconditions,
            source_episodes=[],
            metadata={
                "composite": True,
                "component_skills": skill_ids,
            },
        )

        logger.info(f"Created composite skill: {name}")
        return composite

    def get_all_skills(self) -> List[Skill]:
        """Get all stored skills.

        Returns:
            List of all skills
        """
        return list(self._skills.values())

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a specific skill by ID.

        Args:
            skill_id: ID of the skill

        Returns:
            Skill or None if not found
        """
        return self._skills.get(skill_id)

    async def get_best_skill_for_action(self, action: str) -> Optional[Skill]:
        """Get the best skill for a specific action.

        Args:
            action: Action to find skill for

        Returns:
            Best matching Skill or None
        """
        skills = await self.retrieve_skill(
            task=f"Perform action: {action}",
            top_k=1,
        )
        return skills[0] if skills else None
