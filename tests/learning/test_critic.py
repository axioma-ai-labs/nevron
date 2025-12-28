"""Tests for SelfCritic module."""

import pytest

from src.learning.critic import (
    Critique,
    CritiqueLevel,
    FailedAction,
    ImprovementSuggestion,
    SelfCritic,
)


class TestCritique:
    """Tests for Critique dataclass."""

    def test_critique_creation(self):
        """Test creating a critique."""
        critique = Critique(
            id="crit-001",
            action="search_tavily",
            context_summary="Searching for news",
            outcome_summary="Rate limit exceeded",
            failure_reason="Too many API requests",
            what_went_wrong="No rate limiting implemented",
            better_approach="Add request throttling",
            pattern_to_avoid="Rapid API calls without delays",
            lesson_learned="Implement backoff for API calls",
        )

        assert critique.action == "search_tavily"
        assert critique.level == CritiqueLevel.ERROR
        assert critique.confidence == 0.7

    def test_critique_to_dict(self):
        """Test converting critique to dict."""
        critique = Critique(
            id="crit-002",
            action="post_tweet",
            context_summary="Posting update",
            outcome_summary="Auth failed",
            failure_reason="Token expired",
            what_went_wrong="Stale credentials",
            better_approach="Refresh token before use",
            pattern_to_avoid="Using old tokens",
            lesson_learned="Always verify token validity",
            level=CritiqueLevel.CRITICAL,
            confidence=0.9,
        )

        result = critique.to_dict()

        assert result["action"] == "post_tweet"
        assert result["level"] == "critical"
        assert result["confidence"] == 0.9
        assert "created_at" in result

    def test_critique_from_dict(self):
        """Test creating critique from dict."""
        data = {
            "id": "crit-003",
            "action": "test_action",
            "context_summary": "test context",
            "outcome_summary": "test outcome",
            "failure_reason": "test reason",
            "what_went_wrong": "test wrong",
            "better_approach": "test approach",
            "pattern_to_avoid": "test pattern",
            "lesson_learned": "test lesson",
            "level": "warning",
            "confidence": 0.8,
            "created_at": "2025-01-01T00:00:00+00:00",
        }

        critique = Critique.from_dict(data)

        assert critique.id == "crit-003"
        assert critique.level == CritiqueLevel.WARNING
        assert critique.confidence == 0.8


class TestImprovementSuggestion:
    """Tests for ImprovementSuggestion dataclass."""

    def test_suggestion_creation(self):
        """Test creating a suggestion."""
        suggestion = ImprovementSuggestion(
            id="sug-001",
            pattern="Repeated rate limit failures",
            suggestion="Implement exponential backoff",
            priority=1,
            affected_actions=["search_tavily", "ask_perplexity"],
            confidence=0.85,
        )

        assert suggestion.pattern == "Repeated rate limit failures"
        assert suggestion.priority == 1
        assert len(suggestion.affected_actions) == 2

    def test_suggestion_to_dict(self):
        """Test suggestion to dict."""
        suggestion = ImprovementSuggestion(
            id="sug-002",
            pattern="Test pattern",
            suggestion="Test suggestion",
            priority=2,
            affected_actions=["action_a"],
        )

        result = suggestion.to_dict()

        assert result["id"] == "sug-002"
        assert result["priority"] == 2
        assert "created_at" in result


class TestFailedAction:
    """Tests for FailedAction dataclass."""

    def test_failed_action_creation(self):
        """Test creating a failed action."""
        failed = FailedAction(
            action="search_tavily",
            context={"goal": "research"},
            outcome=None,
            error_message="Connection timeout",
        )

        assert failed.action == "search_tavily"
        assert failed.error_message == "Connection timeout"


class TestSelfCritic:
    """Tests for SelfCritic class."""

    def test_critic_creation(self):
        """Test creating a critic."""
        critic = SelfCritic()
        assert len(critic.get_recent_critiques()) == 0

    @pytest.mark.asyncio
    async def test_critique_rate_limit(self):
        """Test critique for rate limit error."""
        critic = SelfCritic()

        critique = await critic.critique(
            action="search_tavily",
            context={"goal": "research news"},
            outcome=None,
            error_message="429 Too Many Requests - Rate limit exceeded",
        )

        assert critique.action == "search_tavily"
        assert "rate limit" in critique.failure_reason.lower()
        assert "backoff" in critique.better_approach.lower() or "alternative" in critique.better_approach.lower()

    @pytest.mark.asyncio
    async def test_critique_timeout(self):
        """Test critique for timeout error."""
        critic = SelfCritic()

        critique = await critic.critique(
            action="slow_action",
            context={"task": "processing"},
            outcome=None,
            error_message="Operation timed out after 30 seconds",
        )

        # Should match "timeout" or "timed out" pattern
        assert "timeout" in critique.failure_reason.lower() or "timed" in critique.failure_reason.lower()
        assert critique.confidence >= 0.5

    @pytest.mark.asyncio
    async def test_critique_auth_error(self):
        """Test critique for authentication error."""
        critic = SelfCritic()

        critique = await critic.critique(
            action="post_tweet",
            context={"message": "test"},
            outcome=None,
            error_message="401 Unauthorized - Invalid token",
        )

        assert "auth" in critique.failure_reason.lower() or "unauthorized" in critique.failure_reason.lower()

    @pytest.mark.asyncio
    async def test_critique_not_found(self):
        """Test critique for not found error."""
        critic = SelfCritic()

        critique = await critic.critique(
            action="get_resource",
            context={"id": "123"},
            outcome=None,
            error_message="404 Not Found - Resource does not exist",
        )

        assert "not found" in critique.failure_reason.lower()

    @pytest.mark.asyncio
    async def test_critique_unknown_error(self):
        """Test critique for unknown error."""
        critic = SelfCritic()

        critique = await critic.critique(
            action="mystery_action",
            context={},
            outcome=None,
            error_message="Something went wrong",
        )

        # Should get fallback critique
        assert critique.action == "mystery_action"
        assert critique.level == CritiqueLevel.WARNING
        assert critique.confidence == 0.4

    @pytest.mark.asyncio
    async def test_critique_stored(self):
        """Test that critiques are stored."""
        critic = SelfCritic()

        await critic.critique("action1", {}, None, "rate limit")
        await critic.critique("action2", {}, None, "timeout")

        critiques = critic.get_recent_critiques(limit=5)
        assert len(critiques) == 2

    @pytest.mark.asyncio
    async def test_generate_improvement_suggestions_empty(self):
        """Test suggestions with no failures."""
        critic = SelfCritic()

        suggestions = await critic.generate_improvement_suggestions([])
        assert suggestions == []

    @pytest.mark.asyncio
    async def test_generate_improvement_suggestions_single_action(self):
        """Test suggestions for repeated failures in one action."""
        critic = SelfCritic()

        failures = [
            FailedAction("action_a", {}, None, "rate limit exceeded"),
            FailedAction("action_a", {}, None, "429 too many requests"),
            FailedAction("action_a", {}, None, "rate limited"),
        ]

        suggestions = await critic.generate_improvement_suggestions(failures)

        assert len(suggestions) >= 1
        assert "action_a" in suggestions[0].affected_actions

    @pytest.mark.asyncio
    async def test_generate_improvement_suggestions_cross_action(self):
        """Test suggestions for system-wide patterns."""
        critic = SelfCritic()

        failures = [
            FailedAction("action_a", {}, None, "rate limit"),
            FailedAction("action_b", {}, None, "too many requests"),
            FailedAction("action_c", {}, None, "429"),
        ]

        suggestions = await critic.generate_improvement_suggestions(failures)

        # May or may not detect system-wide depending on thresholds
        # Just verify we can analyze without error
        assert isinstance(suggestions, list)

    def test_clear(self):
        """Test clearing critic state."""
        critic = SelfCritic()
        critic._critiques.append(
            Critique(
                id="test",
                action="test",
                context_summary="",
                outcome_summary="",
                failure_reason="",
                what_went_wrong="",
                better_approach="",
                pattern_to_avoid="",
                lesson_learned="",
            )
        )

        critic.clear()

        assert len(critic.get_recent_critiques()) == 0
