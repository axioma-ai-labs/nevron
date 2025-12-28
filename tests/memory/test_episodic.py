"""Tests for Episodic Memory."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from src.llm.embeddings import EmbeddingGenerator
from src.memory.backends.chroma import ChromaBackend
from src.memory.episodic import Episode, EpisodicMemory


class TestEpisode:
    """Tests for Episode dataclass."""

    def test_episode_creation(self):
        """Test creating an episode."""
        episode = Episode(
            id="test-001",
            timestamp=datetime.now(timezone.utc),
            event="Test event",
            action="test_action",
            outcome="Test outcome",
            context={"location": "test"},
            emotional_valence=0.5,
            importance=0.8,
        )

        assert episode.id == "test-001"
        assert episode.event == "Test event"
        assert episode.emotional_valence == 0.5
        assert episode.importance == 0.8
        assert episode.access_count == 0

    def test_episode_to_dict(self):
        """Test converting episode to dictionary."""
        now = datetime.now(timezone.utc)
        episode = Episode(
            id="test-002",
            timestamp=now,
            event="Dict test",
            action="to_dict",
            outcome="Success",
            context={},
            emotional_valence=0.0,
            importance=0.5,
        )

        result = episode.to_dict()

        assert result["id"] == "test-002"
        assert result["event"] == "Dict test"
        assert result["timestamp"] == now.isoformat()

    def test_episode_from_dict(self):
        """Test creating episode from dictionary."""
        data = {
            "id": "test-003",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "From dict",
            "action": "create",
            "outcome": "Created",
            "context": {"key": "value"},
            "emotional_valence": 0.7,
            "importance": 0.9,
            "access_count": 5,
        }

        episode = Episode.from_dict(data)

        assert episode.id == "test-003"
        assert episode.event == "From dict"
        assert episode.access_count == 5
        assert episode.context == {"key": "value"}


@pytest.fixture
def mock_embedding_generator():
    """Mock the EmbeddingGenerator."""
    generator = AsyncMock(spec=EmbeddingGenerator)
    # Return a numpy array
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
def episodic_memory(mock_embedding_generator, mock_chroma_backend):
    """Create episodic memory for testing with mocked dependencies."""
    with (
        patch("src.memory.episodic.ChromaBackend", return_value=mock_chroma_backend),
        patch("src.memory.episodic.EmbeddingGenerator", return_value=mock_embedding_generator),
    ):
        memory = EpisodicMemory(
            backend_type="chroma",
            collection_name="test_episodic_memory",
        )
        # Attach mocks to the instance for test access
        memory._mock_backend = mock_chroma_backend  # type: ignore[attr-defined]
        memory._mock_embedding = mock_embedding_generator  # type: ignore[attr-defined]
        return memory


class TestEpisodicMemory:
    """Tests for EpisodicMemory class."""

    def test_initialization(self, episodic_memory):
        """Test episodic memory initialization."""
        assert episodic_memory is not None
        assert episodic_memory.embedding_generator is not None

    def test_retention_calculation(self, episodic_memory):
        """Test memory retention calculation."""
        now = datetime.now(timezone.utc)
        episode = Episode(
            id="retention-test",
            timestamp=now - timedelta(hours=1),
            event="Test",
            action="test",
            outcome="test",
            context={},
            emotional_valence=0.0,
            importance=0.5,
            last_accessed=now - timedelta(hours=1),
        )

        retention = episodic_memory._calculate_retention(episode, now)

        # Retention should be between MIN_RETENTION and 1.0
        assert EpisodicMemory.MIN_RETENTION <= retention <= 1.0

    def test_retention_increases_with_access(self, episodic_memory):
        """Test that retention is higher with more accesses."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(hours=2)

        low_access = Episode(
            id="low-access",
            timestamp=past,
            event="Test",
            action="test",
            outcome="test",
            context={},
            emotional_valence=0.0,
            importance=0.5,
            access_count=0,
            last_accessed=past,
        )

        high_access = Episode(
            id="high-access",
            timestamp=past,
            event="Test",
            action="test",
            outcome="test",
            context={},
            emotional_valence=0.0,
            importance=0.5,
            access_count=10,
            last_accessed=past,
        )

        low_retention = episodic_memory._calculate_retention(low_access, now)
        high_retention = episodic_memory._calculate_retention(high_access, now)

        # Higher access count should lead to higher retention
        assert high_retention > low_retention

    def test_parse_time_period_today(self, episodic_memory):
        """Test parsing 'today' time period."""
        now = datetime.now(timezone.utc)
        result = episodic_memory._parse_time_period("today", now)

        assert result is not None
        start, end = result
        assert start.date() == now.date()
        assert end == now

    def test_parse_time_period_yesterday(self, episodic_memory):
        """Test parsing 'yesterday' time period."""
        now = datetime.now(timezone.utc)
        result = episodic_memory._parse_time_period("yesterday", now)

        assert result is not None
        start, end = result
        assert (now.date() - start.date()).days == 1

    def test_parse_time_period_last_hour(self, episodic_memory):
        """Test parsing 'last hour' time period."""
        now = datetime.now(timezone.utc)
        result = episodic_memory._parse_time_period("last hour", now)

        assert result is not None
        start, end = result
        assert (end - start).total_seconds() == 3600

    def test_parse_time_period_last_n_days(self, episodic_memory):
        """Test parsing 'last N days' time period."""
        now = datetime.now(timezone.utc)
        result = episodic_memory._parse_time_period("last 7 days", now)

        assert result is not None
        start, end = result
        assert (end - start).days == 7

    def test_parse_time_period_invalid(self, episodic_memory):
        """Test parsing invalid time period."""
        now = datetime.now(timezone.utc)
        result = episodic_memory._parse_time_period("some random text", now)

        assert result is None

    @pytest.mark.asyncio
    async def test_store_episode(self, episodic_memory):
        """Test storing an episode."""
        episode = await episodic_memory.store(
            event="Test storage",
            action="store_test",
            outcome="Stored successfully",
            context={"test": True},
            emotional_valence=0.8,
            importance=0.9,
        )

        assert episode is not None
        assert episode.id is not None
        assert episode.event == "Test storage"
        assert episode.emotional_valence == 0.8
        assert episode.importance == 0.9

        # Verify the backend was called
        episodic_memory._mock_backend.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_recall_episodes(self, episodic_memory):
        """Test recalling episodes."""
        # Store an episode
        await episodic_memory.store(
            event="Recall test event",
            action="recall_test",
            outcome="Ready for recall",
        )

        # Recall
        episodes = await episodic_memory.recall(
            query="recall test",
            top_k=5,
        )

        assert isinstance(episodes, list)

    @pytest.mark.asyncio
    async def test_recall_with_results(self, episodic_memory):
        """Test recalling with results from backend."""
        # Mock backend to return results
        now = datetime.now(timezone.utc)
        mock_result = {
            "id": "result-1",
            "timestamp": now.isoformat(),
            "event": "Found event",
            "action": "found",
            "outcome": "Success",
            "context": {},
            "emotional_valence": 0.5,
            "importance": 0.8,
        }
        episodic_memory._mock_backend.search.return_value = [mock_result]

        episodes = await episodic_memory.recall(
            query="find me",
            top_k=5,
        )

        assert len(episodes) == 1
        assert episodes[0].event == "Found event"

    @pytest.mark.asyncio
    async def test_reinforce(self, episodic_memory):
        """Test reinforcing a memory."""
        result = await episodic_memory.reinforce("episode-123")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_recent(self, episodic_memory):
        """Test getting recent episodes."""
        episodes = await episodic_memory.get_recent(limit=5)
        assert isinstance(episodes, list)
