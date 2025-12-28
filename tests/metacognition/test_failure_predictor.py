"""Tests for FailurePredictor module."""

from src.learning.tracker import ActionTracker
from src.metacognition.failure_predictor import FailurePrediction, FailurePredictor, FailureReason


class TestFailurePrediction:
    """Tests for FailurePrediction dataclass."""

    def test_prediction_creation(self):
        """Test creating a prediction."""
        prediction = FailurePrediction(
            action="search_tavily",
            probability=0.8,
            reasons=[FailureReason.RATE_LIMIT],
            reason_details=["Rate limit approaching"],
            confidence=0.7,
        )

        assert prediction.action == "search_tavily"
        assert prediction.probability == 0.8
        assert prediction.is_high_risk

    def test_is_high_risk(self):
        """Test high risk detection."""
        high_risk = FailurePrediction(
            action="test",
            probability=0.8,
            reasons=[FailureReason.RATE_LIMIT],
            reason_details=[],
            confidence=0.6,
        )
        assert high_risk.is_high_risk

        low_risk = FailurePrediction(
            action="test",
            probability=0.3,
            reasons=[],
            reason_details=[],
            confidence=0.6,
        )
        assert not low_risk.is_high_risk

    def test_is_medium_risk(self):
        """Test medium risk detection."""
        medium_risk = FailurePrediction(
            action="test",
            probability=0.5,
            reasons=[FailureReason.SIMILAR_FAILURE],
            reason_details=[],
            confidence=0.5,
        )
        assert medium_risk.is_medium_risk

    def test_to_dict(self):
        """Test converting prediction to dict."""
        prediction = FailurePrediction(
            action="test",
            probability=0.5,
            reasons=[FailureReason.RATE_LIMIT, FailureReason.TIMEOUT],
            reason_details=["Reason 1", "Reason 2"],
            suggested_alternatives=["alt1", "alt2"],
            confidence=0.7,
        )

        result = prediction.to_dict()

        assert result["action"] == "test"
        assert result["probability"] == 0.5
        assert len(result["reasons"]) == 2
        assert "rate_limit" in result["reasons"]


class TestFailurePredictor:
    """Tests for FailurePredictor class."""

    def test_predictor_creation(self):
        """Test creating a predictor."""
        predictor = FailurePredictor()
        assert predictor is not None

    def test_predictor_with_tracker(self):
        """Test predictor with action tracker."""
        tracker = ActionTracker()
        predictor = FailurePredictor(action_tracker=tracker)

        assert predictor._tracker is tracker

    def test_predict_no_history(self):
        """Test prediction with no historical data."""
        predictor = FailurePredictor()

        prediction = predictor.predict("unknown_action", {})

        assert prediction.action == "unknown_action"
        assert prediction.probability >= 0.0
        assert prediction.confidence <= 0.5  # Low confidence without data

    def test_predict_with_low_success_rate(self):
        """Test prediction for action with low success rate."""
        tracker = ActionTracker()

        # Record many failures
        for _ in range(8):
            tracker.record("failing_action", "ctx", -1.0, False)
        for _ in range(2):
            tracker.record("failing_action", "ctx", 1.0, True)

        predictor = FailurePredictor(action_tracker=tracker)
        prediction = predictor.predict("failing_action", {})

        assert prediction.probability > 0.5
        assert FailureReason.LOW_SUCCESS_RATE in prediction.reasons

    def test_predict_rate_limit(self):
        """Test prediction with rate limit warning."""
        predictor = FailurePredictor()

        # Set up rate limit cache
        predictor.record_rate_limit("search_tavily", 90, 100)

        prediction = predictor.predict("search_tavily", {})

        assert prediction.probability > 0.3
        assert FailureReason.RATE_LIMIT in prediction.reasons

    def test_predict_context_warnings(self):
        """Test prediction with context warnings."""
        predictor = FailurePredictor()

        context = {
            "error_state": True,
            "retry_count": 2,
        }

        prediction = predictor.predict("some_action", context)

        assert prediction.probability > 0.0
        # Context mismatch should be detected
        assert len(prediction.reasons) > 0 or prediction.probability > 0

    def test_record_rate_limit(self):
        """Test recording rate limit info."""
        predictor = FailurePredictor()

        predictor.record_rate_limit("action", 50, 100)

        assert "action" in predictor._rate_limit_cache
        assert predictor._rate_limit_cache["action"]["used"] == 50
        assert predictor._rate_limit_cache["action"]["max"] == 100

    def test_get_rate_limit_alternatives(self):
        """Test getting alternatives for rate-limited actions."""
        predictor = FailurePredictor()

        alternatives = predictor._get_rate_limit_alternatives("search_tavily")
        assert "ask_perplexity" in alternatives

        alternatives = predictor._get_rate_limit_alternatives("unknown")
        assert alternatives == []

    def test_calculate_confidence(self):
        """Test confidence calculation."""
        tracker = ActionTracker()

        # Add many observations
        for _ in range(25):
            tracker.record("well_known_action", "ctx", 1.0, True)

        predictor = FailurePredictor(action_tracker=tracker)
        confidence = predictor._calculate_confidence("well_known_action")

        assert confidence >= 0.7  # Should be high with many observations

        # Unknown action should have low confidence
        unknown_confidence = predictor._calculate_confidence("unknown")
        assert unknown_confidence < 0.5

    def test_clear(self):
        """Test clearing predictor."""
        predictor = FailurePredictor()

        predictor.record_rate_limit("action", 50, 100)
        predictor.clear()

        assert len(predictor._rate_limit_cache) == 0

    def test_get_statistics(self):
        """Test getting statistics."""
        predictor = FailurePredictor()
        predictor.record_rate_limit("action", 50, 100)

        stats = predictor.get_statistics()

        assert stats["rate_limits_tracked"] == 1
        assert "action" in stats["actions_with_limits"]


class TestFailurePredictorIntegration:
    """Integration tests for FailurePredictor."""

    def test_full_prediction_flow(self):
        """Test full prediction flow with tracker."""
        tracker = ActionTracker()

        # Build up history
        for _ in range(5):
            tracker.record("reliable_action", "ctx", 1.0, True)

        for _ in range(3):
            tracker.record("flaky_action", "ctx", 1.0, True)
        for _ in range(7):
            tracker.record("flaky_action", "ctx", -1.0, False)

        predictor = FailurePredictor(action_tracker=tracker)

        # Reliable action should have low failure probability
        reliable_pred = predictor.predict("reliable_action", {})
        assert reliable_pred.probability < 0.5

        # Flaky action should have higher failure probability
        flaky_pred = predictor.predict("flaky_action", {})
        assert flaky_pred.probability > reliable_pred.probability

    def test_should_proceed_recommendation(self):
        """Test should_proceed recommendation."""
        predictor = FailurePredictor()

        # High rate limit usage
        predictor.record_rate_limit("limited_action", 95, 100)

        prediction = predictor.predict("limited_action", {})

        # Should recommend not proceeding
        assert not prediction.should_proceed or prediction.wait_seconds > 0
