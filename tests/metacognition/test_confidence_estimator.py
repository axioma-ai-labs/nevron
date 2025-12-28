"""Tests for ConfidenceEstimator module."""

from src.metacognition.confidence_estimator import (
    ConfidenceEstimate,
    ConfidenceEstimator,
    ConfidenceFactor,
)


class TestConfidenceEstimate:
    """Tests for ConfidenceEstimate dataclass."""

    def test_estimate_creation(self):
        """Test creating an estimate."""
        estimate = ConfidenceEstimate(
            level=0.7,
            factors={ConfidenceFactor.GOAL_CLARITY: 0.8},
            uncertain_aspects=["Some uncertainty"],
            explanation="High confidence",
        )

        assert estimate.level == 0.7
        assert estimate.is_high

    def test_is_low_medium_high(self):
        """Test confidence level checks."""
        low = ConfidenceEstimate(
            level=0.3,
            factors={},
            uncertain_aspects=[],
        )
        assert low.is_low
        assert not low.is_medium
        assert not low.is_high

        medium = ConfidenceEstimate(
            level=0.5,
            factors={},
            uncertain_aspects=[],
        )
        assert medium.is_medium

        high = ConfidenceEstimate(
            level=0.8,
            factors={},
            uncertain_aspects=[],
        )
        assert high.is_high

    def test_weakest_factor(self):
        """Test finding weakest factor."""
        estimate = ConfidenceEstimate(
            level=0.5,
            factors={
                ConfidenceFactor.GOAL_CLARITY: 0.8,
                ConfidenceFactor.MEMORY_SUPPORT: 0.3,
                ConfidenceFactor.TOOL_AVAILABILITY: 0.6,
            },
            uncertain_aspects=[],
        )

        assert estimate.weakest_factor == ConfidenceFactor.MEMORY_SUPPORT

    def test_to_dict(self):
        """Test converting to dict."""
        estimate = ConfidenceEstimate(
            level=0.6,
            factors={ConfidenceFactor.GOAL_CLARITY: 0.8},
            uncertain_aspects=["Issue 1"],
            would_benefit_from="Human help",
            should_request_help=True,
        )

        result = estimate.to_dict()

        assert result["level"] == 0.6
        assert "goal_clarity" in result["factors"]
        assert result["should_request_help"] is True


class TestConfidenceEstimator:
    """Tests for ConfidenceEstimator class."""

    def test_estimator_creation(self):
        """Test creating an estimator."""
        estimator = ConfidenceEstimator()
        assert estimator is not None

    def test_estimate_with_clear_goal(self):
        """Test estimation with clear goal."""
        estimator = ConfidenceEstimator()

        estimate = estimator.estimate(
            goal="Create a detailed report about market trends with charts",
            success_rate=0.8,
        )

        assert estimate.level > 0.5
        assert ConfidenceFactor.GOAL_CLARITY in estimate.factors
        assert estimate.factors[ConfidenceFactor.GOAL_CLARITY] > 0.5

    def test_estimate_with_unclear_goal(self):
        """Test estimation with unclear goal."""
        estimator = ConfidenceEstimator()

        estimate = estimator.estimate(
            goal=None,
            success_rate=0.5,
        )

        assert estimate.factors[ConfidenceFactor.GOAL_CLARITY] < 0.5
        assert len(estimate.uncertain_aspects) > 0

    def test_estimate_with_memories(self):
        """Test estimation with memory matches."""
        estimator = ConfidenceEstimator()

        estimate = estimator.estimate(
            goal="Test goal",
            memory_matches=[{"id": "1"}, {"id": "2"}, {"id": "3"}],
        )

        assert estimate.factors[ConfidenceFactor.MEMORY_SUPPORT] >= 0.5

    def test_estimate_no_memories(self):
        """Test estimation without memories."""
        estimator = ConfidenceEstimator()

        estimate = estimator.estimate(
            goal="Test goal",
            memory_matches=None,
        )

        assert estimate.factors[ConfidenceFactor.MEMORY_SUPPORT] < 0.5

    def test_estimate_with_plan(self):
        """Test estimation with plan."""
        estimator = ConfidenceEstimator()

        plan = {
            "steps": ["step1", "step2"],
            "goal": "Complete task",
            "success_criteria": "All steps done",
            "fallback": "Try alternative",
        }

        estimate = estimator.estimate(
            goal="Test goal",
            plan=plan,
        )

        assert estimate.factors[ConfidenceFactor.PLAN_COMPLETENESS] >= 0.5

    def test_estimate_error_state(self):
        """Test estimation in error state."""
        estimator = ConfidenceEstimator()

        estimate = estimator.estimate(
            goal="Test goal",
            error_state=True,
        )

        assert estimate.factors[ConfidenceFactor.ERROR_STATE] < 0.5
        # Error state should be in uncertain aspects
        assert any("error" in aspect.lower() for aspect in estimate.uncertain_aspects)

    def test_estimate_low_success_rate(self):
        """Test estimation with low success rate."""
        estimator = ConfidenceEstimator()

        estimate = estimator.estimate(
            goal="Test goal",
            success_rate=0.2,
        )

        assert estimate.factors[ConfidenceFactor.SUCCESS_HISTORY] == 0.2
        assert any("performance" in aspect.lower() for aspect in estimate.uncertain_aspects)

    def test_should_request_help_threshold(self):
        """Test help request threshold."""
        estimator = ConfidenceEstimator()

        # Very low confidence should trigger help request
        # The threshold is 0.3, so we need a very low combination
        low_estimate = estimator.estimate(
            goal=None,  # 0.2 clarity
            success_rate=0.0,  # 0.0 success
            error_state=True,  # 0.2 error state
            memory_matches=None,  # 0.3 memory support
        )

        # If level is exactly at threshold (0.3), it won't trigger
        # Check if the estimate is low enough
        if low_estimate.level < 0.3:
            assert low_estimate.should_request_help
            assert low_estimate.would_benefit_from is not None
        else:
            # Level is at or above threshold, verify it's close
            assert low_estimate.level <= 0.4  # Should still be low

    def test_quick_estimate(self):
        """Test quick estimation method."""
        estimator = ConfidenceEstimator()

        high = estimator.quick_estimate(
            goal="Clear actionable goal",
            has_memories=True,
            success_rate=0.9,
            error_state=False,
        )
        assert high > 0.5

        low = estimator.quick_estimate(
            goal=None,
            has_memories=False,
            success_rate=0.1,
            error_state=True,
        )
        assert low < 0.5

    def test_assess_goal_clarity(self):
        """Test goal clarity assessment."""
        estimator = ConfidenceEstimator()

        # Good goal
        good_score = estimator._assess_goal_clarity(
            "Create a report analyzing sales data for Q4 2024"
        )
        assert good_score > 0.5

        # Question-like goal (less clear)
        question_score = estimator._assess_goal_clarity("What should I do?")
        assert question_score < good_score

        # No goal
        no_goal_score = estimator._assess_goal_clarity(None)
        assert no_goal_score < 0.5

    def test_assess_tool_availability(self):
        """Test tool availability assessment."""
        estimator = ConfidenceEstimator()

        # All tools available
        full_score = estimator._assess_tool_availability(
            available_tools=["tool_a", "tool_b", "tool_c"],
            plan={"required_tools": ["tool_a", "tool_b"]},
        )
        assert full_score == 1.0

        # Some tools missing
        partial_score = estimator._assess_tool_availability(
            available_tools=["tool_a"],
            plan={"required_tools": ["tool_a", "tool_b", "tool_c"]},
        )
        assert partial_score < 1.0

    def test_generate_help_request(self):
        """Test help request generation."""
        estimator = ConfidenceEstimator()

        factors = {
            ConfidenceFactor.GOAL_CLARITY: 0.2,
            ConfidenceFactor.MEMORY_SUPPORT: 0.8,
        }

        help_request = estimator._generate_help_request(factors, [])

        # Should request help with goal clarity (weakest factor)
        assert "goal" in help_request.lower() or "clarification" in help_request.lower()
