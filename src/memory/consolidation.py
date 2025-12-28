"""Memory Consolidation - Background process for memory optimization.

Memory consolidation runs periodically to:
- Extract patterns from episodic memory into procedural memory
- Extract facts from episodic memory into semantic memory
- Reinforce important memories
- Let trivial memories fade (forgetting curve)
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.llm.llm import LLM
from src.memory.episodic import Episode, EpisodicMemory
from src.memory.procedural import ProceduralMemory
from src.memory.semantic import SemanticMemory


@dataclass
class ConsolidationResult:
    """Results of a consolidation run."""

    timestamp: datetime
    episodes_processed: int
    facts_extracted: int
    patterns_identified: int
    skills_created: int
    memories_reinforced: int
    memories_pruned: int
    duration_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "episodes_processed": self.episodes_processed,
            "facts_extracted": self.facts_extracted,
            "patterns_identified": self.patterns_identified,
            "skills_created": self.skills_created,
            "memories_reinforced": self.memories_reinforced,
            "memories_pruned": self.memories_pruned,
            "duration_seconds": self.duration_seconds,
        }


class MemoryConsolidator:
    """Background process for memory consolidation.

    Runs periodically to optimize the memory system by:
    1. Processing recent episodic memories
    2. Extracting facts for semantic memory
    3. Identifying patterns for procedural memory
    4. Reinforcing important memories
    5. Pruning low-importance memories
    """

    # Default consolidation interval (1 hour)
    DEFAULT_INTERVAL_SECONDS = 3600

    # Thresholds
    FACT_EXTRACTION_CONFIDENCE = 0.7
    PATTERN_SIMILARITY_THRESHOLD = 0.8
    REINFORCEMENT_IMPORTANCE_THRESHOLD = 0.7
    PRUNING_RETENTION_THRESHOLD = 0.2

    def __init__(
        self,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
        procedural: ProceduralMemory,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    ):
        """Initialize memory consolidator.

        Args:
            episodic: Episodic memory instance
            semantic: Semantic memory instance
            procedural: Procedural memory instance
            interval_seconds: Consolidation interval in seconds
        """
        self.episodic = episodic
        self.semantic = semantic
        self.procedural = procedural
        self.interval = interval_seconds

        self.llm = LLM()
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None
        self._last_run: Optional[datetime] = None
        self._consolidation_history: List[ConsolidationResult] = []

        logger.debug(f"Memory consolidator initialized with {interval_seconds}s interval")

    async def start(self) -> None:
        """Start the background consolidation process."""
        if self._running:
            logger.warning("Memory consolidator already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Memory consolidator started")

    async def stop(self) -> None:
        """Stop the background consolidation process."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Memory consolidator stopped")

    async def _run_loop(self) -> None:
        """Main consolidation loop."""
        while self._running:
            try:
                await self.consolidate()
            except Exception as e:
                logger.error(f"Error during memory consolidation: {e}")

            # Wait for next interval
            await asyncio.sleep(self.interval)

    async def consolidate(self) -> ConsolidationResult:
        """Perform a consolidation run.

        Returns:
            ConsolidationResult with statistics
        """
        start_time = datetime.now(timezone.utc)
        logger.info("Starting memory consolidation...")

        # Get recent episodes to process
        lookback = timedelta(hours=24)
        cutoff = start_time - lookback

        episodes = await self.episodic.recall(
            query="",
            top_k=100,
            time_range=(cutoff, start_time),
            include_retention=False,
        )

        stats = {
            "episodes_processed": len(episodes),
            "facts_extracted": 0,
            "patterns_identified": 0,
            "skills_created": 0,
            "memories_reinforced": 0,
            "memories_pruned": 0,
        }

        # Process each episode
        for episode in episodes:
            # Extract facts
            facts = await self._extract_facts(episode)
            stats["facts_extracted"] += len(facts)

            # Check for patterns
            pattern_found = await self._identify_patterns(episode)
            if pattern_found:
                stats["patterns_identified"] += 1

            # Reinforce important memories
            if episode.importance >= self.REINFORCEMENT_IMPORTANCE_THRESHOLD:
                await self.episodic.reinforce(episode.id)
                stats["memories_reinforced"] += 1

            # Check for pruning (low retention)
            retention = episode.metadata.get("retention_score", 1.0)
            if retention < self.PRUNING_RETENTION_THRESHOLD:
                # Mark for pruning (actual deletion would need backend support)
                logger.debug(
                    f"Episode {episode.id} marked for pruning (retention: {retention:.2f})"
                )
                stats["memories_pruned"] += 1

        # Calculate duration
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        result = ConsolidationResult(
            timestamp=start_time,
            episodes_processed=stats["episodes_processed"],
            facts_extracted=stats["facts_extracted"],
            patterns_identified=stats["patterns_identified"],
            skills_created=stats["skills_created"],
            memories_reinforced=stats["memories_reinforced"],
            memories_pruned=stats["memories_pruned"],
            duration_seconds=duration,
        )

        self._last_run = start_time
        self._consolidation_history.append(result)

        logger.info(
            f"Memory consolidation complete: "
            f"{stats['episodes_processed']} episodes, "
            f"{stats['facts_extracted']} facts, "
            f"{stats['patterns_identified']} patterns, "
            f"duration: {duration:.2f}s"
        )

        return result

    async def _extract_facts(self, episode: Episode) -> List[Dict[str, Any]]:
        """Extract facts from an episode using LLM.

        Args:
            episode: Episode to extract facts from

        Returns:
            List of extracted facts
        """
        prompt = f"""Analyze this experience and extract any factual information that should be remembered.

Experience:
- Event: {episode.event}
- Action: {episode.action}
- Outcome: {episode.outcome}
- Context: {episode.context}

Extract facts as subject-predicate-object triples. Only extract facts that are:
1. Objective and verifiable
2. Worth remembering for future reference
3. Not just temporary state information

Respond with a JSON array of facts, each with 'subject', 'predicate', and 'object' fields.
If no significant facts can be extracted, respond with an empty array [].
"""

        try:
            response = await self.llm.generate_response([{"role": "user", "content": prompt}])

            # Parse JSON response
            import json

            try:
                facts_data = json.loads(response.strip())
                if not isinstance(facts_data, list):
                    return []

                # Store extracted facts
                for fact_data in facts_data:
                    if all(k in fact_data for k in ["subject", "predicate", "object"]):
                        await self.semantic.store_fact(
                            subject=fact_data["subject"],
                            predicate=fact_data["predicate"],
                            obj=fact_data["object"],
                            confidence=self.FACT_EXTRACTION_CONFIDENCE,
                            source=f"episode:{episode.id}",
                        )

                return facts_data

            except json.JSONDecodeError:
                logger.debug(f"Could not parse facts from episode {episode.id}")
                return []

        except Exception as e:
            logger.error(f"Error extracting facts: {e}")
            return []

    async def _identify_patterns(self, episode: Episode) -> bool:
        """Identify action patterns from an episode.

        Args:
            episode: Episode to analyze

        Returns:
            True if a pattern was identified
        """
        # Build action representation
        action_data = {
            "action": episode.action,
            "context": episode.context,
        }

        # Determine success based on emotional valence
        success = episode.emotional_valence > 0

        # Record pattern observation
        skill = await self.procedural.observe_pattern(
            actions=[action_data],
            context=episode.context,
            outcome=episode.outcome,
            success=success,
        )

        return skill is not None

    async def consolidate_once(self) -> ConsolidationResult:
        """Run consolidation once (for testing or manual triggers).

        Returns:
            ConsolidationResult with statistics
        """
        return await self.consolidate()

    def get_history(self) -> List[ConsolidationResult]:
        """Get consolidation history.

        Returns:
            List of past consolidation results
        """
        return self._consolidation_history.copy()

    def get_last_run(self) -> Optional[datetime]:
        """Get timestamp of last consolidation run.

        Returns:
            Datetime of last run or None
        """
        return self._last_run

    @property
    def is_running(self) -> bool:
        """Check if consolidator is running."""
        return self._running
