"""Tests for ActionTracker module."""

from src.learning.tracker import ActionOutcome, ActionStats, ActionTracker


class TestActionOutcome:
    """Tests for ActionOutcome dataclass."""

    def test_outcome_creation(self):
        """Test creating an action outcome."""
        outcome = ActionOutcome(
            id="test-001",
            action="search_tavily",
            context_key="research",
            reward=0.8,
            success=True,
        )

        assert outcome.id == "test-001"
        assert outcome.action == "search_tavily"
        assert outcome.context_key == "research"
        assert outcome.reward == 0.8
        assert outcome.success is True

    def test_outcome_to_dict(self):
        """Test converting outcome to dict."""
        outcome = ActionOutcome(
            id="test-002",
            action="post_tweet",
            context_key="social",
            reward=-0.5,
            success=False,
            metadata={"error": "rate_limit"},
        )

        result = outcome.to_dict()

        assert result["id"] == "test-002"
        assert result["action"] == "post_tweet"
        assert result["reward"] == -0.5
        assert result["metadata"]["error"] == "rate_limit"
        assert "timestamp" in result

    def test_outcome_from_dict(self):
        """Test creating outcome from dict."""
        data = {
            "id": "test-003",
            "action": "search_tavily",
            "context_key": "research",
            "reward": 1.0,
            "success": True,
            "timestamp": "2025-01-01T00:00:00+00:00",
        }

        outcome = ActionOutcome.from_dict(data)

        assert outcome.id == "test-003"
        assert outcome.action == "search_tavily"
        assert outcome.reward == 1.0


class TestActionStats:
    """Tests for ActionStats dataclass."""

    def test_stats_creation(self):
        """Test creating action stats."""
        stats = ActionStats(
            action="search_tavily",
            total_count=10,
            success_count=8,
            failure_count=2,
            total_reward=6.5,
        )

        assert stats.action == "search_tavily"
        assert stats.total_count == 10
        assert stats.success_count == 8

    def test_success_rate(self):
        """Test success rate calculation."""
        stats = ActionStats(
            action="test",
            total_count=10,
            success_count=7,
            failure_count=3,
        )

        assert stats.success_rate == 0.7

    def test_success_rate_empty(self):
        """Test success rate with no data."""
        stats = ActionStats(action="test")
        assert stats.success_rate == 0.5  # Neutral

    def test_average_reward(self):
        """Test average reward calculation."""
        stats = ActionStats(
            action="test",
            total_count=10,
            total_reward=5.0,
        )

        assert stats.average_reward == 0.5

    def test_recent_success_rate(self):
        """Test recent success rate."""
        stats = ActionStats(action="test")
        stats.recent_rewards = [1.0, 1.0, 0.5, -1.0, 1.0]

        # 4 successes (>0) out of 5
        assert stats.recent_success_rate == 0.8

    def test_to_dict(self):
        """Test stats to dict."""
        stats = ActionStats(
            action="test",
            total_count=5,
            success_count=3,
            failure_count=2,
            total_reward=2.5,
        )

        result = stats.to_dict()

        assert result["action"] == "test"
        assert result["success_rate"] == 0.6
        assert result["average_reward"] == 0.5


class TestActionTracker:
    """Tests for ActionTracker class."""

    def test_tracker_creation(self):
        """Test creating a tracker."""
        tracker = ActionTracker()
        assert len(tracker.get_all_stats()) == 0

    def test_record_outcome(self):
        """Test recording an outcome."""
        tracker = ActionTracker()

        outcome = tracker.record(
            action="search_tavily",
            context_key="research",
            reward=1.0,
            success=True,
        )

        assert outcome.action == "search_tavily"
        assert outcome.success is True

        stats = tracker.get_action_stats("search_tavily")
        assert stats is not None
        assert stats.total_count == 1
        assert stats.success_count == 1

    def test_record_multiple_outcomes(self):
        """Test recording multiple outcomes."""
        tracker = ActionTracker()

        tracker.record("action_a", "ctx1", 1.0, True)
        tracker.record("action_a", "ctx1", 1.0, True)
        tracker.record("action_a", "ctx1", -1.0, False)
        tracker.record("action_b", "ctx2", 0.5, True)

        stats_a = tracker.get_action_stats("action_a")
        assert stats_a is not None
        assert stats_a.total_count == 3
        assert stats_a.success_count == 2
        assert stats_a.failure_count == 1

        stats_b = tracker.get_action_stats("action_b")
        assert stats_b is not None
        assert stats_b.total_count == 1

    def test_get_success_rate(self):
        """Test getting success rate."""
        tracker = ActionTracker()

        tracker.record("action", "ctx", 1.0, True)
        tracker.record("action", "ctx", 1.0, True)
        tracker.record("action", "ctx", -1.0, False)

        rate = tracker.get_success_rate("action")
        assert abs(rate - 0.6667) < 0.01

    def test_get_success_rate_unknown(self):
        """Test success rate for unknown action."""
        tracker = ActionTracker()
        assert tracker.get_success_rate("unknown") == 0.5

    def test_get_context_success_rate(self):
        """Test context-specific success rate."""
        tracker = ActionTracker()

        # Context A: 100% success
        tracker.record("action", "ctx_a", 1.0, True)
        tracker.record("action", "ctx_a", 1.0, True)

        # Context B: 50% success
        tracker.record("action", "ctx_b", 1.0, True)
        tracker.record("action", "ctx_b", -1.0, False)

        assert tracker.get_context_success_rate("ctx_a", "action") == 1.0
        assert tracker.get_context_success_rate("ctx_b", "action") == 0.5

    def test_get_best_action_for_context(self):
        """Test getting best action for context."""
        tracker = ActionTracker()

        # In context "research": action_a is better
        tracker.record("action_a", "research", 1.0, True)
        tracker.record("action_a", "research", 1.0, True)
        tracker.record("action_b", "research", 1.0, True)
        tracker.record("action_b", "research", -1.0, False)

        best = tracker.get_best_action_for_context("research")
        assert best == "action_a"

    def test_get_action_ranking(self):
        """Test action ranking."""
        tracker = ActionTracker()

        tracker.record("action_a", "ctx", 1.0, True)
        tracker.record("action_a", "ctx", 1.0, True)
        tracker.record("action_b", "ctx", 1.0, True)
        tracker.record("action_b", "ctx", -1.0, False)
        tracker.record("action_c", "ctx", -1.0, False)

        ranking = tracker.get_action_ranking()

        assert ranking[0][0] == "action_a"  # 100%
        assert ranking[1][0] == "action_b"  # 50%
        assert ranking[2][0] == "action_c"  # 0%

    def test_get_recent_outcomes(self):
        """Test getting recent outcomes."""
        tracker = ActionTracker()

        for i in range(10):
            tracker.record(f"action_{i % 3}", "ctx", 1.0, True)

        outcomes = tracker.get_recent_outcomes(limit=5)
        assert len(outcomes) == 5

        outcomes_filtered = tracker.get_recent_outcomes(action="action_0")
        assert all(o.action == "action_0" for o in outcomes_filtered)

    def test_get_failing_actions(self):
        """Test getting failing actions."""
        tracker = ActionTracker()

        # Good action: 80% success
        for _ in range(8):
            tracker.record("good_action", "ctx", 1.0, True)
        for _ in range(2):
            tracker.record("good_action", "ctx", -1.0, False)

        # Bad action: 20% success
        for _ in range(2):
            tracker.record("bad_action", "ctx", 1.0, True)
        for _ in range(8):
            tracker.record("bad_action", "ctx", -1.0, False)

        failing = tracker.get_failing_actions(threshold=0.3)

        assert len(failing) == 1
        assert failing[0][0] == "bad_action"

    def test_clear(self):
        """Test clearing tracker."""
        tracker = ActionTracker()

        tracker.record("action", "ctx", 1.0, True)
        tracker.clear()

        assert len(tracker.get_all_stats()) == 0

    def test_to_and_from_dict(self):
        """Test serialization round-trip."""
        tracker = ActionTracker()

        tracker.record("action_a", "ctx1", 1.0, True)
        tracker.record("action_b", "ctx2", -1.0, False)

        data = tracker.to_dict()

        new_tracker = ActionTracker()
        new_tracker.from_dict(data)

        assert "action_a" in new_tracker.get_all_stats()
        assert "action_b" in new_tracker.get_all_stats()
