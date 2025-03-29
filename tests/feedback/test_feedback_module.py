from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from src.feedback.feedback_module import FeedbackConfig, FeedbackModule, FeedbackType


class TestFeedbackModule:
    def test_init(self):
        """Test the initialization of FeedbackModule."""
        module = FeedbackModule()
        assert module.feedback_history == []
        assert module.feedback_configs == {}
        assert module.action_weights == {}

    def test_register_feedback_config(self):
        """Test registering a feedback configuration."""
        module = FeedbackModule()
        config = FeedbackConfig(action="test_action", feedback_type=FeedbackType.BINARY)

        module.register_feedback_config(config)

        assert "test_action" in module.feedback_configs
        assert module.feedback_configs["test_action"] == config

    def test_collect_feedback_binary(self):
        """Test collecting binary feedback."""
        module = FeedbackModule()

        # Success case
        score = module.collect_feedback("test_action", "success")
        assert score == 1.0
        assert module.feedback_history[-1]["status"] == "success"

        # Failure case
        score = module.collect_feedback("test_action", None)
        assert score == -1.0
        assert module.feedback_history[-1]["status"] == "failure"

    def test_collect_feedback_weighted(self):
        """Test collecting weighted feedback."""
        module = FeedbackModule()
        config = FeedbackConfig(
            action="weighted_action", feedback_type=FeedbackType.WEIGHTED, weight=0.5
        )
        module.register_feedback_config(config)

        # Success with weight
        score = module.collect_feedback("weighted_action", "success")
        assert score == 0.5
        assert module.feedback_history[-1]["status"] == "partial_success"

        # Failure with weight
        score = module.collect_feedback("weighted_action", None)
        assert score == -0.5
        assert module.feedback_history[-1]["status"] == "failure"

    def test_collect_feedback_custom(self):
        """Test collecting custom feedback."""
        module = FeedbackModule()

        def custom_scorer(outcome):
            if isinstance(outcome, str):
                return len(outcome) / 10.0
            return -1.0

        config = FeedbackConfig(
            action="custom_action",
            feedback_type=FeedbackType.CUSTOM,
            custom_feedback_scorer=custom_scorer,
        )
        module.register_feedback_config(config)

        # Test with string outcome
        score = module.collect_feedback("custom_action", "hello")
        assert score == 0.5  # len("hello") / 10.0

        # Test with None outcome
        score = module.collect_feedback("custom_action", None)
        assert score == -1.0

    @patch("src.feedback.feedback_module.datetime")
    def test_feedback_timestamp(self, mock_datetime):
        """Test that timestamps are recorded correctly."""
        mock_now = datetime(2023, 1, 1, tzinfo=timezone.utc)
        mock_datetime.now.return_value = mock_now

        module = FeedbackModule()
        module.collect_feedback("test_action", "success")

        assert module.feedback_history[-1]["timestamp"] == mock_now

    def test_analyze_feedback_trends(self):
        """Test analyzing feedback trends."""
        module = FeedbackModule()

        # Add some feedback data
        module.collect_feedback("action1", "success")
        module.collect_feedback("action1", None)
        module.collect_feedback("action1", "success")
        module.collect_feedback("action2", "success")

        # Test analysis for specific action
        results = module.analyze_feedback_trends("action1")
        assert results["count"] == 3
        assert results["success_rate"] == pytest.approx(66.67, 0.01)
        assert results["failure_rate"] == pytest.approx(33.33, 0.01)
        assert results["most_common_outcome"] == "success"

        # Test overall analysis
        results = module.analyze_feedback_trends()
        assert results["count"] == 4
        assert results["success_rate"] == 75.0
        assert results["failure_rate"] == 25.0

    def test_get_feedback_history(self):
        """Test retrieving feedback history."""
        module = FeedbackModule()

        # Add feedback entries
        for i in range(20):
            module.collect_feedback(f"action{i}", f"outcome{i}")

        # Default limit is 10
        history = module.get_feedback_history()
        assert len(history) == 10
        assert history[0]["action"] == "action10"
        assert history[-1]["action"] == "action19"

        # Custom limit
        history = module.get_feedback_history(limit=5)
        assert len(history) == 5
        assert history[0]["action"] == "action15"

        # Get all history
        history = module.get_feedback_history(limit=100)
        assert len(history) == 20

    def test_reset_feedback_history(self):
        """Test resetting feedback history."""
        module = FeedbackModule()

        # Add some feedback data
        module.collect_feedback("action1", "success")
        module.collect_feedback("action2", "failure")

        assert len(module.feedback_history) == 2

        # Reset history
        module.reset_feedback_history()
        assert module.feedback_history == []

    def test_empty_feedback_analysis(self):
        """Test analyzing empty feedback data."""
        module = FeedbackModule()
        results = module.analyze_feedback_trends("nonexistent_action")

        assert results["count"] == 0
        assert results["average_score"] == 0.0
        assert results["success_rate"] == 0.0
