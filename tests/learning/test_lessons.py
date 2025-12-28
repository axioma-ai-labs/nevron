"""Tests for Lesson module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.learning.lessons import Lesson, LessonRepository


class TestLesson:
    """Tests for Lesson dataclass."""

    def test_lesson_creation(self):
        """Test creating a lesson."""
        lesson = Lesson(
            id="lesson-001",
            summary="Use backoff for rate limits",
            situation="Making rapid API calls",
            action="search_tavily",
            what_went_wrong="Rate limit exceeded",
            better_approach="Implement exponential backoff",
        )

        assert lesson.id == "lesson-001"
        assert lesson.action == "search_tavily"
        assert lesson.reinforcement_count == 0
        assert lesson.confidence == 0.7

    def test_lesson_create_factory(self):
        """Test Lesson.create factory method."""
        lesson = Lesson.create(
            summary="Test lesson",
            situation="Test situation",
            action="test_action",
            what_went_wrong="Test failure",
            better_approach="Test solution",
            tags=["test", "demo"],
        )

        assert lesson.id is not None
        assert len(lesson.id) == 36  # UUID format
        assert lesson.tags == ["test", "demo"]

    def test_lesson_age_days(self):
        """Test age_days property."""
        # Create lesson from 2 days ago
        old_time = datetime.now(timezone.utc) - timedelta(days=2)
        lesson = Lesson.create(
            summary="Old lesson",
            situation="",
            action="",
            what_went_wrong="",
            better_approach="",
        )
        lesson.learned_at = old_time

        assert lesson.age_days >= 2.0
        assert lesson.age_days < 3.0

    def test_lesson_reliability(self):
        """Test reliability calculation."""
        lesson = Lesson.create(
            summary="Test",
            situation="",
            action="",
            what_went_wrong="",
            better_approach="",
            confidence=0.8,
        )

        # Initial reliability
        initial = lesson.reliability
        assert 0 < initial <= 1

        # After reinforcement, reliability should increase
        lesson.reinforce()
        assert lesson.reliability >= initial

    def test_lesson_reinforce(self):
        """Test reinforcing a lesson."""
        lesson = Lesson.create(
            summary="Test",
            situation="",
            action="",
            what_went_wrong="",
            better_approach="",
            confidence=0.6,
        )

        initial_conf = lesson.confidence
        lesson.reinforce()

        assert lesson.reinforcement_count == 1
        assert lesson.confidence > initial_conf

    def test_lesson_to_dict(self):
        """Test converting lesson to dict."""
        lesson = Lesson.create(
            summary="API backoff lesson",
            situation="Rate limiting",
            action="search_tavily",
            what_went_wrong="Too many requests",
            better_approach="Add delays",
            tags=["api", "rate-limit"],
        )

        result = lesson.to_dict()

        assert result["summary"] == "API backoff lesson"
        assert result["action"] == "search_tavily"
        assert "reliability" in result
        assert "learned_at" in result
        assert result["tags"] == ["api", "rate-limit"]

    def test_lesson_from_dict(self):
        """Test creating lesson from dict."""
        data = {
            "id": "lesson-002",
            "summary": "Test lesson",
            "situation": "Test situation",
            "action": "test_action",
            "what_went_wrong": "Test failure",
            "better_approach": "Test solution",
            "learned_at": "2025-01-01T00:00:00+00:00",
            "reinforcement_count": 3,
            "confidence": 0.9,
        }

        lesson = Lesson.from_dict(data)

        assert lesson.id == "lesson-002"
        assert lesson.reinforcement_count == 3
        assert lesson.confidence == 0.9

    def test_lesson_str(self):
        """Test string representation."""
        lesson = Lesson.create(
            summary="A very long lesson summary that should be truncated",
            situation="",
            action="test_action",
            what_went_wrong="",
            better_approach="",
        )

        result = str(lesson)
        assert "Lesson(" in result
        assert "test_action" in result


class TestLessonRepository:
    """Tests for LessonRepository class."""

    @pytest.fixture
    def mock_backend(self):
        """Create mock backend."""
        backend = MagicMock()
        backend.store = AsyncMock()
        backend.search = AsyncMock(return_value=[])
        return backend

    @pytest.fixture
    def mock_embedding_generator(self):
        """Create mock embedding generator."""
        generator = MagicMock()
        generator.get_embedding = AsyncMock(return_value=[MagicMock(tolist=lambda: [0.1] * 384)])
        return generator

    @pytest.mark.asyncio
    async def test_store_lesson(self, mock_backend, mock_embedding_generator):
        """Test storing a lesson."""
        with (
            patch(
                "src.learning.lessons.EmbeddingGenerator",
                return_value=mock_embedding_generator,
            ),
            patch("src.learning.lessons.ChromaBackend", return_value=mock_backend),
        ):
            repo = LessonRepository(backend_type="chroma")
            repo._backend = mock_backend
            repo._embedding_generator = mock_embedding_generator

            lesson = Lesson.create(
                summary="Test lesson",
                situation="Test",
                action="test_action",
                what_went_wrong="Test",
                better_approach="Test",
            )

            lesson_id = await repo.store(lesson)

            assert lesson_id == lesson.id
            mock_backend.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_similar_lesson_reinforces(self, mock_backend, mock_embedding_generator):
        """Test that similar lessons are reinforced instead of duplicated."""
        with (
            patch(
                "src.learning.lessons.EmbeddingGenerator",
                return_value=mock_embedding_generator,
            ),
            patch("src.learning.lessons.ChromaBackend", return_value=mock_backend),
        ):
            repo = LessonRepository(backend_type="chroma")
            repo._backend = mock_backend
            repo._embedding_generator = mock_embedding_generator

            # Store first lesson
            lesson1 = Lesson.create(
                summary="Rate limit handling",
                situation="API calls",
                action="search_tavily",
                what_went_wrong="Rate limited",
                better_approach="Use backoff",
            )
            await repo.store(lesson1)

            # Store similar lesson
            lesson2 = Lesson.create(
                summary="Rate limit handling v2",
                situation="API calls",
                action="search_tavily",
                what_went_wrong="Rate limited again",
                better_approach="Use backoff",
            )
            lesson_id = await repo.store(lesson2)

            # Should have reinforced first lesson
            assert lesson_id == lesson1.id
            assert lesson1.reinforcement_count == 1

    @pytest.mark.asyncio
    async def test_find_relevant(self, mock_backend, mock_embedding_generator):
        """Test finding relevant lessons."""
        # Mock search results - use recent date for good reliability
        from datetime import datetime, timezone

        mock_results = [
            {
                "id": "lesson-1",
                "summary": "Rate limit lesson",
                "situation": "API",
                "action": "search_tavily",
                "what_went_wrong": "Limited",
                "better_approach": "Backoff",
                "learned_at": datetime.now(timezone.utc).isoformat(),  # Recent lesson
                "reinforcement_count": 5,  # High reinforcement for good reliability
                "confidence": 0.9,  # High confidence
            }
        ]
        mock_backend.search = AsyncMock(return_value=mock_results)

        with (
            patch(
                "src.learning.lessons.EmbeddingGenerator",
                return_value=mock_embedding_generator,
            ),
            patch("src.learning.lessons.ChromaBackend", return_value=mock_backend),
        ):
            repo = LessonRepository(backend_type="chroma")
            repo._backend = mock_backend
            repo._embedding_generator = mock_embedding_generator

            lessons = await repo.find_relevant(
                context={"goal": "search for news", "action": "search_tavily"},
                top_k=5,
            )

            assert len(lessons) == 1
            assert lessons[0].summary == "Rate limit lesson"

    @pytest.mark.asyncio
    async def test_find_by_action(self, mock_backend, mock_embedding_generator):
        """Test finding lessons by action."""
        with (
            patch(
                "src.learning.lessons.EmbeddingGenerator",
                return_value=mock_embedding_generator,
            ),
            patch("src.learning.lessons.ChromaBackend", return_value=mock_backend),
        ):
            repo = LessonRepository(backend_type="chroma")
            repo._backend = mock_backend
            repo._embedding_generator = mock_embedding_generator

            # Add lesson to cache
            lesson = Lesson.create(
                summary="Test",
                situation="Test",
                action="search_tavily",
                what_went_wrong="Test",
                better_approach="Test",
            )
            repo._cache[lesson.id] = lesson
            repo._by_action["search_tavily"] = [lesson.id]

            lessons = await repo.find_by_action("search_tavily")

            assert len(lessons) == 1
            assert lessons[0].action == "search_tavily"

    @pytest.mark.asyncio
    async def test_reinforce_lesson(self, mock_backend, mock_embedding_generator):
        """Test reinforcing a lesson."""
        with (
            patch(
                "src.learning.lessons.EmbeddingGenerator",
                return_value=mock_embedding_generator,
            ),
            patch("src.learning.lessons.ChromaBackend", return_value=mock_backend),
        ):
            repo = LessonRepository(backend_type="chroma")
            repo._backend = mock_backend
            repo._embedding_generator = mock_embedding_generator

            # Add lesson to cache
            lesson = Lesson.create(
                summary="Test",
                situation="Test",
                action="test_action",
                what_went_wrong="Test",
                better_approach="Test",
            )
            repo._cache[lesson.id] = lesson

            initial_count = lesson.reinforcement_count
            result = await repo.reinforce_lesson(lesson.id)

            assert result is True
            assert lesson.reinforcement_count == initial_count + 1

    def test_get_lesson(self, mock_backend, mock_embedding_generator):
        """Test getting a lesson by ID."""
        with (
            patch(
                "src.learning.lessons.EmbeddingGenerator",
                return_value=mock_embedding_generator,
            ),
            patch("src.learning.lessons.ChromaBackend", return_value=mock_backend),
        ):
            repo = LessonRepository(backend_type="chroma")

            # Add lesson to cache
            lesson = Lesson.create(
                summary="Test",
                situation="Test",
                action="test_action",
                what_went_wrong="Test",
                better_approach="Test",
            )
            repo._cache[lesson.id] = lesson

            result = repo.get_lesson(lesson.id)

            assert result == lesson

    def test_get_all_lessons(self, mock_backend, mock_embedding_generator):
        """Test getting all lessons."""
        with (
            patch(
                "src.learning.lessons.EmbeddingGenerator",
                return_value=mock_embedding_generator,
            ),
            patch("src.learning.lessons.ChromaBackend", return_value=mock_backend),
        ):
            repo = LessonRepository(backend_type="chroma")

            # Add lessons to cache
            for i in range(3):
                lesson = Lesson.create(
                    summary=f"Test {i}",
                    situation="Test",
                    action="test_action",
                    what_went_wrong="Test",
                    better_approach="Test",
                )
                repo._cache[lesson.id] = lesson

            lessons = repo.get_all_lessons()

            assert len(lessons) == 3

    def test_get_lessons_by_tag(self, mock_backend, mock_embedding_generator):
        """Test getting lessons by tag."""
        with (
            patch(
                "src.learning.lessons.EmbeddingGenerator",
                return_value=mock_embedding_generator,
            ),
            patch("src.learning.lessons.ChromaBackend", return_value=mock_backend),
        ):
            repo = LessonRepository(backend_type="chroma")

            # Add lessons with different tags
            lesson1 = Lesson.create(
                summary="Rate limit",
                situation="",
                action="",
                what_went_wrong="",
                better_approach="",
                tags=["api", "rate-limit"],
            )
            lesson2 = Lesson.create(
                summary="Auth",
                situation="",
                action="",
                what_went_wrong="",
                better_approach="",
                tags=["auth"],
            )
            repo._cache[lesson1.id] = lesson1
            repo._cache[lesson2.id] = lesson2

            api_lessons = repo.get_lessons_by_tag("api")

            assert len(api_lessons) == 1
            assert api_lessons[0].summary == "Rate limit"

    def test_get_statistics(self, mock_backend, mock_embedding_generator):
        """Test getting statistics."""
        with (
            patch(
                "src.learning.lessons.EmbeddingGenerator",
                return_value=mock_embedding_generator,
            ),
            patch("src.learning.lessons.ChromaBackend", return_value=mock_backend),
        ):
            repo = LessonRepository(backend_type="chroma")

            # Add lessons
            for i in range(3):
                lesson = Lesson.create(
                    summary=f"Test {i}",
                    situation="Test",
                    action=f"action_{i % 2}",
                    what_went_wrong="Test",
                    better_approach="Test",
                )
                lesson.reinforcement_count = i
                repo._cache[lesson.id] = lesson
                repo._by_action.setdefault(lesson.action, []).append(lesson.id)

            stats = repo.get_statistics()

            assert stats["total_lessons"] == 3
            assert stats["actions_covered"] == 2
            assert stats["avg_reinforcement"] == 1.0  # (0+1+2)/3

    def test_clear_cache(self, mock_backend, mock_embedding_generator):
        """Test clearing cache."""
        with (
            patch(
                "src.learning.lessons.EmbeddingGenerator",
                return_value=mock_embedding_generator,
            ),
            patch("src.learning.lessons.ChromaBackend", return_value=mock_backend),
        ):
            repo = LessonRepository(backend_type="chroma")

            lesson = Lesson.create(
                summary="Test",
                situation="",
                action="test",
                what_went_wrong="",
                better_approach="",
            )
            repo._cache[lesson.id] = lesson

            repo.clear_cache()

            assert len(repo._cache) == 0
