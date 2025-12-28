"""Tests for StrategyAdapter module."""

from src.learning.adapter import ActionBias, AdaptationContext, StrategyAdapter
from src.learning.lessons import Lesson
from src.learning.tracker import ActionTracker


class TestActionBias:
    """Tests for ActionBias dataclass."""

    def test_bias_creation(self):
        """Test creating an action bias."""
        bias = ActionBias(
            action="search_tavily",
            bias=0.3,
            confidence=0.8,
            reason="High success rate",
            source="tracker",
        )

        assert bias.action == "search_tavily"
        assert bias.bias == 0.3
        assert bias.confidence == 0.8

    def test_bias_to_dict(self):
        """Test bias to dict."""
        bias = ActionBias(
            action="test_action",
            bias=-0.2,
            confidence=0.6,
            reason="Low performance",
            source="lesson",
        )

        result = bias.to_dict()

        assert result["action"] == "test_action"
        assert result["bias"] == -0.2
        assert result["source"] == "lesson"


class TestAdaptationContext:
    """Tests for AdaptationContext dataclass."""

    def test_context_creation(self):
        """Test creating adaptation context."""
        ctx = AdaptationContext(
            goal="research news",
            task_type="research",
            environment="production",
        )

        assert ctx.goal == "research news"
        assert ctx.task_type == "research"

    def test_context_key_generation(self):
        """Test context key is deterministic."""
        ctx1 = AdaptationContext(goal="test", task_type="research")
        ctx2 = AdaptationContext(goal="test", task_type="research")

        assert ctx1.to_context_key() == ctx2.to_context_key()

    def test_context_key_different_contexts(self):
        """Test different contexts have different keys."""
        ctx1 = AdaptationContext(goal="research")
        ctx2 = AdaptationContext(goal="social")

        assert ctx1.to_context_key() != ctx2.to_context_key()

    def test_context_key_empty(self):
        """Test empty context gets global key."""
        ctx = AdaptationContext()
        assert ctx.to_context_key() == "global"


class TestStrategyAdapter:
    """Tests for StrategyAdapter class."""

    def test_adapter_creation(self):
        """Test creating an adapter."""
        tracker = ActionTracker()
        adapter = StrategyAdapter(tracker=tracker)

        assert adapter is not None

    def test_get_action_biases_no_data(self):
        """Test biases with no tracking data."""
        tracker = ActionTracker()
        adapter = StrategyAdapter(tracker=tracker)

        ctx = AdaptationContext(goal="test")
        biases = adapter.get_action_biases(ctx)

        # Should have no biases without data
        assert len(biases) == 0

    def test_get_action_biases_with_data(self):
        """Test biases with tracking data."""
        tracker = ActionTracker()

        # Record some outcomes
        for _ in range(5):
            tracker.record("good_action", "ctx", 1.0, True)
        for _ in range(5):
            tracker.record("bad_action", "ctx", -1.0, False)

        adapter = StrategyAdapter(tracker=tracker)
        ctx = AdaptationContext(goal="test")

        biases = adapter.get_action_biases(ctx)

        assert "good_action" in biases
        assert "bad_action" in biases
        assert biases["good_action"].bias > 0
        assert biases["bad_action"].bias < 0

    def test_get_ranked_actions(self):
        """Test getting ranked actions."""
        tracker = ActionTracker()

        tracker.record("action_a", "ctx", 1.0, True)
        tracker.record("action_a", "ctx", 1.0, True)
        tracker.record("action_b", "ctx", 1.0, True)
        tracker.record("action_b", "ctx", -1.0, False)
        tracker.record("action_c", "ctx", -1.0, False)

        adapter = StrategyAdapter(tracker=tracker)
        ctx = AdaptationContext()

        ranked = adapter.get_ranked_actions(ctx)

        # Should be ordered by bias (highest first)
        assert ranked[0][0] == "action_a"
        assert ranked[-1][0] == "action_c"

    def test_get_preferred_action(self):
        """Test getting preferred action."""
        tracker = ActionTracker()

        tracker.record("action_a", "ctx", 1.0, True)
        tracker.record("action_b", "ctx", -1.0, False)

        adapter = StrategyAdapter(tracker=tracker)
        ctx = AdaptationContext()

        preferred = adapter.get_preferred_action(ctx, ["action_a", "action_b"])
        assert preferred == "action_a"

    def test_get_actions_to_avoid(self):
        """Test getting actions to avoid."""
        tracker = ActionTracker()

        for _ in range(5):
            tracker.record("good_action", "ctx", 1.0, True)
        for _ in range(5):
            tracker.record("bad_action", "ctx", -1.0, False)

        adapter = StrategyAdapter(tracker=tracker)
        ctx = AdaptationContext()

        avoid = adapter.get_actions_to_avoid(ctx)

        assert "bad_action" in avoid
        assert "good_action" not in avoid

    def test_set_override(self):
        """Test setting manual override."""
        tracker = ActionTracker()
        adapter = StrategyAdapter(tracker=tracker)

        adapter.set_override("test_action", -0.5, "Manually disabled")

        ctx = AdaptationContext()
        biases = adapter.get_action_biases(ctx, ["test_action"])

        assert "test_action" in biases
        assert biases["test_action"].bias == -0.5
        assert biases["test_action"].source == "override"

    def test_remove_override(self):
        """Test removing override."""
        tracker = ActionTracker()
        adapter = StrategyAdapter(tracker=tracker)

        adapter.set_override("test_action", -0.5, "Disabled")
        result = adapter.remove_override("test_action")

        assert result is True

        # Override should be gone
        ctx = AdaptationContext()
        biases = adapter.get_action_biases(ctx, ["test_action"])

        # Without override and no data, should have no bias
        assert "test_action" not in biases

    def test_update_from_lesson(self):
        """Test updating from lesson."""
        tracker = ActionTracker()
        adapter = StrategyAdapter(tracker=tracker)

        lesson = Lesson.create(
            summary="Don't use search_tavily when rate limited",
            situation="Research task",
            action="search_tavily",
            what_went_wrong="Rate limited",
            better_approach="Use ask_perplexity instead",
            context_key="research_123",
        )

        adapter.update_from_lesson(lesson)

        # Context modifier should be negative for search_tavily
        modifier = adapter.get_context_modifier("research_123", "search_tavily")
        assert modifier < 0

    def test_extract_context_features(self):
        """Test extracting context features from dict."""
        tracker = ActionTracker()
        adapter = StrategyAdapter(tracker=tracker)

        context = {
            "goal": "research crypto news",
            "task_type": "research",
            "environment": "production",
        }

        key = adapter.extract_context_features(context)

        assert key != "global"
        assert len(key) > 0

    def test_reset_modifiers(self):
        """Test resetting modifiers."""
        tracker = ActionTracker()
        adapter = StrategyAdapter(tracker=tracker)

        lesson = Lesson.create(
            summary="Test",
            situation="Test",
            action="test_action",
            what_went_wrong="Test",
            better_approach="Test",
            context_key="test_ctx",
        )

        adapter.update_from_lesson(lesson)
        adapter.reset_modifiers()

        # Modifier should be reset
        modifier = adapter.get_context_modifier("test_ctx", "test_action")
        assert modifier == 0.0

    def test_to_and_from_dict(self):
        """Test serialization round-trip."""
        tracker = ActionTracker()
        adapter = StrategyAdapter(tracker=tracker)

        adapter.set_override("action_a", 0.5, "Test override")

        data = adapter.to_dict()

        new_adapter = StrategyAdapter(tracker=ActionTracker())
        new_adapter.from_dict(data)

        ctx = AdaptationContext()
        biases = new_adapter.get_action_biases(ctx, ["action_a"])

        assert "action_a" in biases
        assert biases["action_a"].bias == 0.5
