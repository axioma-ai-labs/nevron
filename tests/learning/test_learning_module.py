"""Tests for AdaptiveLearningModule."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.learning.learning_module import (
    AdaptiveLearningModule,
    LearningConfig,
    LearningOutcome,
    get_learning_module,
)


class TestLearningConfig:
    """Tests for LearningConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = LearningConfig()

        assert config.critique_on_failure is True
        assert config.critique_threshold == 0.3
        assert config.auto_create_lessons is True
        assert config.enable_bias_adaptation is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = LearningConfig(
            critique_on_failure=False,
            critique_threshold=0.5,
            persist_lessons=False,
        )

        assert config.critique_on_failure is False
        assert config.critique_threshold == 0.5
        assert config.persist_lessons is False


class TestLearningOutcome:
    """Tests for LearningOutcome."""

    def test_outcome_creation(self):
        """Test creating a learning outcome."""
        outcome = LearningOutcome(
            action="search_tavily",
            reward=0.8,
            success=True,
            new_success_rate=0.75,
        )

        assert outcome.action == "search_tavily"
        assert outcome.success is True
        assert outcome.critique is None
        assert outcome.lesson_created is None

    def test_outcome_to_dict(self):
        """Test outcome to dict."""
        outcome = LearningOutcome(
            action="test_action",
            reward=-0.5,
            success=False,
            new_success_rate=0.4,
            bias_change=-0.1,
        )

        result = outcome.to_dict()

        assert result["action"] == "test_action"
        assert result["reward"] == -0.5
        assert result["success"] is False
        assert "timestamp" in result


class TestAdaptiveLearningModule:
    """Tests for AdaptiveLearningModule."""

    @pytest.fixture
    def mock_lesson_repo(self):
        """Create mock lesson repository."""
        repo = MagicMock()
        repo.store = AsyncMock(return_value="lesson-id")
        repo.find_relevant = AsyncMock(return_value=[])
        repo.find_by_action = AsyncMock(return_value=[])
        repo.reinforce_lesson = AsyncMock(return_value=True)
        repo.get_statistics = MagicMock(return_value={"total_lessons": 0})
        repo.clear_cache = MagicMock()
        return repo

    def test_module_creation(self):
        """Test creating a learning module."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        assert module is not None
        assert module._tracker is not None
        assert module._critic is not None
        assert module._adapter is not None

    @pytest.mark.asyncio
    async def test_learn_from_outcome_success(self):
        """Test learning from successful outcome."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        outcome = await module.learn_from_outcome(
            action="search_tavily",
            context={"goal": "research"},
            outcome={"results": ["news1", "news2"]},
            reward=1.0,
        )

        assert outcome.success is True
        assert outcome.action == "search_tavily"
        assert outcome.critique is None  # No critique for success
        assert module.get_success_rate("search_tavily") > 0.5

    @pytest.mark.asyncio
    async def test_learn_from_outcome_failure(self):
        """Test learning from failed outcome."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        outcome = await module.learn_from_outcome(
            action="search_tavily",
            context={"goal": "research"},
            outcome=None,
            reward=-1.0,
            error_message="Rate limit exceeded",
        )

        assert outcome.success is False
        assert outcome.critique is not None
        assert "rate limit" in outcome.critique.failure_reason.lower()

    @pytest.mark.asyncio
    async def test_learn_from_outcome_creates_lesson(self, mock_lesson_repo):
        """Test that failures can create lessons."""
        config = LearningConfig(persist_lessons=True)

        with patch(
            "src.learning.learning_module.LessonRepository",
            return_value=mock_lesson_repo,
        ):
            module = AdaptiveLearningModule(config=config)
            module._lessons = mock_lesson_repo

            outcome = await module.learn_from_outcome(
                action="search_tavily",
                context={"goal": "research"},
                outcome=None,
                reward=-1.0,
                error_message="Rate limit exceeded",
            )

            assert outcome.lesson_created is not None
            mock_lesson_repo.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_learn_from_agent_action(self):
        """Test learning from AgentAction enum."""
        from src.core.defs import AgentAction

        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        outcome = await module.learn_from_agent_action(
            action=AgentAction.SEARCH_TAVILY,
            context={"goal": "research"},
            outcome={"results": []},
            reward=0.5,
        )

        assert outcome.action == "search_tavily"

    def test_get_action_biases(self):
        """Test getting action biases."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        # Record some outcomes
        module._tracker.record("action_a", "ctx", 1.0, True)
        module._tracker.record("action_a", "ctx", 1.0, True)
        module._tracker.record("action_b", "ctx", -1.0, False)

        biases = module.get_action_biases(
            context={"goal": "test"},
            available_actions=["action_a", "action_b"],
        )

        assert "action_a" in biases
        assert "action_b" in biases
        assert biases["action_a"].bias > biases["action_b"].bias

    @pytest.mark.asyncio
    async def test_get_relevant_lessons(self, mock_lesson_repo):
        """Test getting relevant lessons."""
        from src.learning.lessons import Lesson

        mock_lessons = [
            Lesson.create(
                summary="Rate limit handling",
                situation="API calls",
                action="search_tavily",
                what_went_wrong="Limited",
                better_approach="Backoff",
            )
        ]
        mock_lesson_repo.find_relevant = AsyncMock(return_value=mock_lessons)

        config = LearningConfig(persist_lessons=True)

        with patch(
            "src.learning.learning_module.LessonRepository",
            return_value=mock_lesson_repo,
        ):
            module = AdaptiveLearningModule(config=config)
            module._lessons = mock_lesson_repo

            lessons = await module.get_relevant_lessons(
                context={"goal": "research", "action": "search_tavily"}
            )

            assert len(lessons) == 1
            assert lessons[0].action == "search_tavily"

    @pytest.mark.asyncio
    async def test_analyze_recent_failures(self):
        """Test analyzing recent failures."""
        config = LearningConfig(persist_lessons=False, analyze_patterns_threshold=2)
        module = AdaptiveLearningModule(config=config)

        # Record some failures
        await module.learn_from_outcome("action_a", {}, None, -1.0, "rate limit")
        await module.learn_from_outcome("action_a", {}, None, -1.0, "rate limit again")

        suggestions = await module.analyze_recent_failures()

        # Should get at least one suggestion
        assert len(suggestions) >= 1

    def test_get_action_stats(self):
        """Test getting action statistics."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        module._tracker.record("test_action", "ctx", 1.0, True)
        module._tracker.record("test_action", "ctx", 0.5, True)

        stats = module.get_action_stats("test_action")

        assert stats is not None
        assert stats.total_count == 2
        assert stats.success_count == 2

    def test_get_success_rate(self):
        """Test getting success rate."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        module._tracker.record("test_action", "ctx", 1.0, True)
        module._tracker.record("test_action", "ctx", -1.0, False)

        rate = module.get_success_rate("test_action")

        assert rate == 0.5

    def test_get_best_action_for_context(self):
        """Test getting best action for context."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        module._tracker.record("action_a", "research", 1.0, True)
        module._tracker.record("action_a", "research", 1.0, True)
        module._tracker.record("action_b", "research", -1.0, False)

        best = module.get_best_action_for_context(
            context={"goal": "research"},
            available_actions=["action_a", "action_b"],
        )

        assert best == "action_a"

    def test_get_actions_to_avoid(self):
        """Test getting actions to avoid."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        for _ in range(5):
            module._tracker.record("bad_action", "ctx", -1.0, False)
        for _ in range(5):
            module._tracker.record("good_action", "ctx", 1.0, True)

        avoid = module.get_actions_to_avoid(context={})

        assert "bad_action" in avoid
        assert "good_action" not in avoid

    @pytest.mark.asyncio
    async def test_get_learning_history(self):
        """Test getting learning history."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        await module.learn_from_outcome("action1", {}, None, 1.0)
        await module.learn_from_outcome("action2", {}, None, 0.5)
        await module.learn_from_outcome("action1", {}, None, -0.5)

        history = module.get_learning_history(limit=10)
        assert len(history) == 3

        action1_history = module.get_learning_history(action="action1")
        assert len(action1_history) == 2

    def test_get_failing_actions(self):
        """Test getting failing actions."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        # Good action
        for _ in range(8):
            module._tracker.record("good_action", "ctx", 1.0, True)
        for _ in range(2):
            module._tracker.record("good_action", "ctx", -1.0, False)

        # Bad action
        for _ in range(2):
            module._tracker.record("bad_action", "ctx", 1.0, True)
        for _ in range(8):
            module._tracker.record("bad_action", "ctx", -1.0, False)

        failing = module.get_failing_actions(threshold=0.3)

        assert len(failing) == 1
        assert failing[0][0] == "bad_action"

    def test_get_tracker_statistics(self):
        """Test getting tracker statistics."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        module._tracker.record("action_a", "ctx", 1.0, True)
        module._tracker.record("action_b", "ctx", -1.0, False)

        stats = module.get_tracker_statistics()

        assert stats["total_actions_tracked"] == 2
        assert stats["total_outcomes"] == 2
        assert stats["overall_success_rate"] == 0.5

    def test_reset(self):
        """Test resetting module."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        module._tracker.record("action", "ctx", 1.0, True)

        module.reset()

        assert len(module._tracker.get_all_stats()) == 0
        assert len(module.get_learning_history()) == 0

    def test_to_and_from_dict(self):
        """Test serialization round-trip."""
        config = LearningConfig(persist_lessons=False)
        module = AdaptiveLearningModule(config=config)

        module._tracker.record("action_a", "ctx", 1.0, True)
        module._adapter.set_override("action_b", -0.5, "Test")

        data = module.to_dict()

        new_module = AdaptiveLearningModule(config=config)
        new_module.from_dict(data)

        assert "action_a" in new_module._tracker.get_all_stats()


class TestGetLearningModule:
    """Tests for get_learning_module singleton."""

    def test_get_learning_module_creates_singleton(self):
        """Test that get_learning_module creates a singleton."""
        # Reset singleton
        import src.learning.learning_module as lm

        lm._learning_module = None

        module1 = get_learning_module(config=LearningConfig(persist_lessons=False))
        module2 = get_learning_module()

        assert module1 is module2

        # Reset singleton for other tests
        lm._learning_module = None
