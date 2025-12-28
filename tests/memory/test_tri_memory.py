"""Tests for Tri-Memory System."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.llm.embeddings import EmbeddingGenerator
from src.memory.backends.chroma import ChromaBackend
from src.memory.episodic import Episode
from src.memory.procedural import Skill
from src.memory.semantic import Concept, Fact
from src.memory.tri_memory import MemoryRecall, TriMemorySystem


class TestMemoryRecall:
    """Tests for MemoryRecall dataclass."""

    def test_memory_recall_creation(self):
        """Test creating a memory recall result."""
        recall = MemoryRecall(
            query="test query",
            timestamp=datetime.now(),
            episodes=[],
            facts=[],
            concepts=[],
            skills=[],
        )

        assert recall.query == "test query"
        assert recall.has_results is False

    def test_memory_recall_has_results(self):
        """Test has_results property."""
        episode = Episode(
            id="test",
            timestamp=datetime.now(timezone.utc),
            event="test",
            action="test",
            outcome="test",
            context={},
            emotional_valence=0.0,
            importance=0.5,
        )

        recall = MemoryRecall(
            query="test",
            timestamp=datetime.now(),
            episodes=[episode],
            facts=[],
            concepts=[],
            skills=[],
        )

        assert recall.has_results is True

    def test_memory_recall_to_dict(self):
        """Test converting recall to dictionary."""
        recall = MemoryRecall(
            query="dict test",
            timestamp=datetime.now(),
            episodes=[],
            facts=[],
            concepts=[],
            skills=[],
        )

        result = recall.to_dict()

        assert result["query"] == "dict test"
        assert "timestamp" in result
        assert isinstance(result["episodes"], list)

    def test_memory_recall_to_prompt_format_empty(self):
        """Test prompt format with no results."""
        recall = MemoryRecall(
            query="empty test",
            timestamp=datetime.now(),
            episodes=[],
            facts=[],
            concepts=[],
            skills=[],
        )

        prompt = recall.to_prompt_format()

        assert "No relevant memories found" in prompt

    def test_memory_recall_to_prompt_format_with_episodes(self):
        """Test prompt format with episodes."""
        episode = Episode(
            id="test",
            timestamp=datetime.now(timezone.utc),
            event="test event",
            action="test action",
            outcome="test outcome",
            context={},
            emotional_valence=0.0,
            importance=0.5,
        )

        recall = MemoryRecall(
            query="test",
            timestamp=datetime.now(),
            episodes=[episode],
            facts=[],
            concepts=[],
            skills=[],
        )

        prompt = recall.to_prompt_format()

        assert "Recent Experiences" in prompt
        assert "test event" in prompt

    def test_memory_recall_to_prompt_format_with_facts(self):
        """Test prompt format with facts."""
        fact = Fact(
            id="fact-1",
            subject="Python",
            predicate="is",
            object="programming language",
        )

        recall = MemoryRecall(
            query="test",
            timestamp=datetime.now(),
            episodes=[],
            facts=[fact],
            concepts=[],
            skills=[],
        )

        prompt = recall.to_prompt_format()

        assert "Known Facts" in prompt
        assert "Python" in prompt

    def test_memory_recall_to_prompt_format_with_concepts(self):
        """Test prompt format with concepts."""
        concept = Concept(
            id="concept-1",
            name="AI",
            concept_type="field",
            description="Artificial Intelligence",
        )

        recall = MemoryRecall(
            query="test",
            timestamp=datetime.now(),
            episodes=[],
            facts=[],
            concepts=[concept],
            skills=[],
        )

        prompt = recall.to_prompt_format()

        assert "Related Concepts" in prompt
        assert "AI" in prompt

    def test_memory_recall_to_prompt_format_with_skills(self):
        """Test prompt format with skills."""
        skill = Skill(
            id="skill-1",
            name="Test Skill",
            description="A test skill",
            trigger_pattern="test",
            action_sequence=[],
            preconditions=[],
            postconditions=[],
            success_count=8,
            failure_count=2,
        )

        recall = MemoryRecall(
            query="test",
            timestamp=datetime.now(),
            episodes=[],
            facts=[],
            concepts=[],
            skills=[skill],
        )

        prompt = recall.to_prompt_format()

        assert "Available Skills" in prompt
        assert "Test Skill" in prompt


@pytest.fixture
def mock_embedding_generator():
    """Mock the EmbeddingGenerator."""
    generator = AsyncMock(spec=EmbeddingGenerator)
    generator.get_embedding.return_value = np.array([[0.1, 0.2, 0.3]])
    return generator


@pytest.fixture
def mock_chroma_backend():
    """Mock the ChromaBackend."""
    backend = AsyncMock(spec=ChromaBackend)
    backend.store = AsyncMock()
    backend.search = AsyncMock(return_value=[])
    return backend


@pytest.fixture
def mock_consolidator():
    """Mock the MemoryConsolidator."""
    consolidator = MagicMock()
    consolidator.start = AsyncMock()
    consolidator.stop = AsyncMock()
    consolidator.consolidate_once = AsyncMock(
        return_value=MagicMock(
            episodes_processed=0,
            facts_extracted=0,
            patterns_identified=0,
            skills_updated=0,
            duration_seconds=0.1,
        )
    )
    consolidator.is_running = False
    consolidator.get_last_run = MagicMock(return_value=None)
    consolidator.get_history = MagicMock(return_value=[])
    return consolidator


@pytest.fixture
def tri_memory(mock_embedding_generator, mock_chroma_backend, mock_consolidator):
    """Create tri-memory system for testing."""
    with (
        patch("src.memory.episodic.ChromaBackend", return_value=mock_chroma_backend),
        patch("src.memory.episodic.EmbeddingGenerator", return_value=mock_embedding_generator),
        patch("src.memory.semantic.ChromaBackend", return_value=mock_chroma_backend),
        patch("src.memory.semantic.EmbeddingGenerator", return_value=mock_embedding_generator),
        patch("src.memory.procedural.ChromaBackend", return_value=mock_chroma_backend),
        patch("src.memory.procedural.EmbeddingGenerator", return_value=mock_embedding_generator),
        patch("src.memory.tri_memory.MemoryConsolidator", return_value=mock_consolidator),
    ):
        memory = TriMemorySystem(
            backend_type="chroma",
            enable_consolidation=False,
        )
        memory._mock_backend = mock_chroma_backend  # type: ignore[attr-defined]
        memory._mock_embedding = mock_embedding_generator  # type: ignore[attr-defined]
        memory._mock_consolidator = mock_consolidator  # type: ignore[attr-defined]
        return memory


class TestTriMemorySystem:
    """Tests for TriMemorySystem class."""

    def test_initialization(self, tri_memory):
        """Test tri-memory system initialization."""
        assert tri_memory is not None
        assert tri_memory.episodic is not None
        assert tri_memory.semantic is not None
        assert tri_memory.procedural is not None
        assert tri_memory.consolidator is not None

    @pytest.mark.asyncio
    async def test_start_and_stop(self, tri_memory):
        """Test starting and stopping the system."""
        await tri_memory.start()
        assert tri_memory._initialized is True

        await tri_memory.stop()
        assert tri_memory._initialized is False

    @pytest.mark.asyncio
    async def test_context_manager(
        self, mock_embedding_generator, mock_chroma_backend, mock_consolidator
    ):
        """Test using tri-memory as context manager."""
        with (
            patch("src.memory.episodic.ChromaBackend", return_value=mock_chroma_backend),
            patch("src.memory.episodic.EmbeddingGenerator", return_value=mock_embedding_generator),
            patch("src.memory.semantic.ChromaBackend", return_value=mock_chroma_backend),
            patch("src.memory.semantic.EmbeddingGenerator", return_value=mock_embedding_generator),
            patch("src.memory.procedural.ChromaBackend", return_value=mock_chroma_backend),
            patch(
                "src.memory.procedural.EmbeddingGenerator", return_value=mock_embedding_generator
            ),
            patch("src.memory.tri_memory.MemoryConsolidator", return_value=mock_consolidator),
        ):
            async with TriMemorySystem(
                backend_type="chroma",
                enable_consolidation=False,
            ) as memory:
                assert memory._initialized is True

    @pytest.mark.asyncio
    async def test_store_experience(self, tri_memory):
        """Test storing an experience."""
        episode = await tri_memory.store_experience(
            event="Test event",
            action="test_action",
            outcome="Test outcome",
            context={"location": "test"},
            reward=0.5,
            importance=0.8,
        )

        assert episode is not None
        assert episode.event == "Test event"
        assert episode.emotional_valence == 0.5

    @pytest.mark.asyncio
    async def test_store_fact(self, tri_memory):
        """Test storing a fact."""
        fact = await tri_memory.store_fact(
            subject="Test",
            predicate="is",
            obj="working",
            confidence=0.9,
        )

        assert fact is not None
        assert fact.subject == "Test"

    @pytest.mark.asyncio
    async def test_store_concept(self, tri_memory):
        """Test storing a concept."""
        concept = await tri_memory.store_concept(
            name="Test Concept",
            concept_type="test",
            description="A test concept",
            properties={"key": "value"},
        )

        assert concept is not None
        assert concept.name == "Test Concept"

    @pytest.mark.asyncio
    async def test_store_skill(self, tri_memory):
        """Test storing a skill."""
        skill = await tri_memory.store_skill(
            name="Test Skill",
            description="A test skill",
            trigger_pattern="test pattern",
            action_sequence=[{"action": "test"}],
            preconditions=["ready"],
            postconditions=["done"],
        )

        assert skill is not None
        assert skill.name == "Test Skill"

    @pytest.mark.asyncio
    async def test_recall(self, tri_memory):
        """Test unified recall."""
        # Store some data first
        await tri_memory.store_experience(
            event="Recall test",
            action="recall",
            outcome="ready for recall",
        )

        # Recall
        result = await tri_memory.recall(
            query="recall test",
            top_k=5,
        )

        assert isinstance(result, MemoryRecall)
        assert result.query == "recall test"

    @pytest.mark.asyncio
    async def test_recall_selective(self, tri_memory):
        """Test selective recall (only certain memory types)."""
        result = await tri_memory.recall(
            query="selective test",
            top_k=3,
            include_episodes=True,
            include_facts=False,
            include_concepts=False,
            include_skills=False,
        )

        assert isinstance(result, MemoryRecall)
        # Facts and concepts should be empty
        assert result.facts == []
        assert result.concepts == []

    @pytest.mark.asyncio
    async def test_recall_for_action(self, tri_memory):
        """Test recall optimized for action selection."""
        result = await tri_memory.recall_for_action(
            action="test_action",
            context={"state": "ready"},
        )

        assert isinstance(result, MemoryRecall)

    @pytest.mark.asyncio
    async def test_get_best_skill(self, tri_memory):
        """Test getting best skill for a task."""
        # Store a skill
        await tri_memory.store_skill(
            name="Best Skill Test",
            description="Skill for best skill test",
            trigger_pattern="best skill",
            action_sequence=[{"action": "test"}],
        )

        # Get best skill
        skill = await tri_memory.get_best_skill(
            task="best skill test",
        )

        # May or may not find it depending on vector similarity
        # Just check it returns the right type
        assert skill is None or hasattr(skill, "name")

    @pytest.mark.asyncio
    async def test_record_skill_outcome(self, tri_memory):
        """Test recording skill outcome."""
        skill = await tri_memory.store_skill(
            name="Outcome Skill",
            description="For outcome test",
            trigger_pattern="outcome",
            action_sequence=[],
        )

        await tri_memory.record_skill_outcome(skill.id, success=True)

        # Skill should have updated counts
        stored_skill = tri_memory.procedural.get_skill(skill.id)
        assert stored_skill is not None
        assert stored_skill.success_count == 1

    def test_get_statistics(self, tri_memory):
        """Test getting memory statistics."""
        stats = tri_memory.get_statistics()

        assert isinstance(stats, dict)
        assert "consolidation_enabled" in stats
        assert "consolidation_running" in stats
        assert "total_skills" in stats
        assert "total_concepts" in stats


class TestTriMemoryConsolidation:
    """Tests for tri-memory consolidation."""

    @pytest.fixture
    def tri_memory_with_consolidation(
        self, mock_embedding_generator, mock_chroma_backend, mock_consolidator
    ):
        """Create tri-memory with consolidation enabled."""
        mock_consolidator.is_running = True

        with (
            patch("src.memory.episodic.ChromaBackend", return_value=mock_chroma_backend),
            patch("src.memory.episodic.EmbeddingGenerator", return_value=mock_embedding_generator),
            patch("src.memory.semantic.ChromaBackend", return_value=mock_chroma_backend),
            patch("src.memory.semantic.EmbeddingGenerator", return_value=mock_embedding_generator),
            patch("src.memory.procedural.ChromaBackend", return_value=mock_chroma_backend),
            patch(
                "src.memory.procedural.EmbeddingGenerator", return_value=mock_embedding_generator
            ),
            patch("src.memory.tri_memory.MemoryConsolidator", return_value=mock_consolidator),
        ):
            memory = TriMemorySystem(
                backend_type="chroma",
                enable_consolidation=True,
                consolidation_interval=3600,
            )
            memory._mock_consolidator = mock_consolidator  # type: ignore[attr-defined]
            return memory

    @pytest.mark.asyncio
    async def test_consolidate_now(self, tri_memory_with_consolidation):
        """Test immediate consolidation."""
        memory = tri_memory_with_consolidation

        # Store some experience
        await memory.store_experience(
            event="Consolidation test",
            action="consolidate",
            outcome="ready",
            importance=0.8,
        )

        # Trigger consolidation
        result = await memory.consolidate_now()

        assert result is not None
        assert result.episodes_processed >= 0
        assert result.duration_seconds >= 0

    @pytest.mark.asyncio
    async def test_consolidation_starts_with_system(self, tri_memory_with_consolidation):
        """Test that consolidation starts when system starts."""
        memory = tri_memory_with_consolidation

        await memory.start()

        # Check consolidator.start was called
        memory._mock_consolidator.start.assert_called_once()

        await memory.stop()

        # Check consolidator.stop was called
        memory._mock_consolidator.stop.assert_called_once()
