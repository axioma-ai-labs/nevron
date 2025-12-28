"""Failure Predictor - Predict impending failures based on context.

Uses historical data and context analysis to predict failure probability
before executing an action.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.defs import AgentAction
from src.learning.tracker import ActionOutcome, ActionTracker


class FailureReason(Enum):
    """Categories of predicted failure reasons."""

    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    RESOURCE_UNAVAILABLE = "resource_unavailable"
    SIMILAR_FAILURE = "similar_failure"
    LOW_SUCCESS_RATE = "low_success_rate"
    PREREQUISITE_MISSING = "prerequisite_missing"
    CONTEXT_MISMATCH = "context_mismatch"
    UNKNOWN = "unknown"


@dataclass
class FailurePrediction:
    """Represents a prediction of potential failure."""

    action: str
    probability: float  # 0.0 to 1.0
    reasons: List[FailureReason]
    reason_details: List[str]
    suggested_alternatives: List[str] = field(default_factory=list)
    confidence: float = 0.5
    should_proceed: bool = True
    wait_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "probability": self.probability,
            "reasons": [r.value for r in self.reasons],
            "reason_details": self.reason_details,
            "suggested_alternatives": self.suggested_alternatives,
            "confidence": self.confidence,
            "should_proceed": self.should_proceed,
            "wait_seconds": self.wait_seconds,
        }

    @property
    def is_high_risk(self) -> bool:
        """Check if this prediction indicates high failure risk."""
        return self.probability >= 0.7 and self.confidence >= 0.5

    @property
    def is_medium_risk(self) -> bool:
        """Check if this prediction indicates medium failure risk."""
        return 0.4 <= self.probability < 0.7 and self.confidence >= 0.4


class FailurePredictor:
    """Predict impending failures based on context and history.

    Factors considered:
    - Historical success rate for this action
    - Similar past contexts and their outcomes
    - Current resource constraints (API limits, time)
    - Action prerequisites
    - Recent failure patterns
    """

    # Thresholds for prediction
    HIGH_FAILURE_THRESHOLD = 0.7
    MEDIUM_FAILURE_THRESHOLD = 0.4
    MIN_OBSERVATIONS_FOR_PREDICTION = 3
    RECENT_WINDOW_HOURS = 24

    # Rate limit tracking (action -> (count, reset_time))
    _rate_limits: Dict[str, tuple[int, datetime]] = {}

    def __init__(
        self,
        action_tracker: Optional[ActionTracker] = None,
    ):
        """Initialize failure predictor.

        Args:
            action_tracker: Optional ActionTracker for historical data
        """
        self._tracker = action_tracker
        self._rate_limit_cache: Dict[str, Dict[str, Any]] = {}
        self._recent_failures: List[ActionOutcome] = []

        logger.debug("FailurePredictor initialized")

    def set_tracker(self, tracker: ActionTracker) -> None:
        """Set the action tracker.

        Args:
            tracker: ActionTracker instance
        """
        self._tracker = tracker

    def predict(
        self,
        action: str,
        context: Dict[str, Any],
    ) -> FailurePrediction:
        """Predict failure probability for an action.

        Args:
            action: Action name to predict for
            context: Current context

        Returns:
            FailurePrediction with probability and reasons
        """
        reasons: List[FailureReason] = []
        reason_details: List[str] = []
        probabilities: List[float] = []
        alternatives: List[str] = []

        # 1. Check historical success rate
        if self._tracker:
            success_rate = self._tracker.get_success_rate(action)
            stats = self._tracker.get_action_stats(action)

            if stats and stats.total_count >= self.MIN_OBSERVATIONS_FOR_PREDICTION:
                if success_rate < 0.3:
                    reasons.append(FailureReason.LOW_SUCCESS_RATE)
                    reason_details.append(
                        f"Low historical success rate: {success_rate:.0%} "
                        f"over {stats.total_count} attempts"
                    )
                    probabilities.append(1.0 - success_rate)

        # 2. Check for recent failures of this action
        recent_failure_prob = self._check_recent_failures(action)
        if recent_failure_prob > 0.5:
            reasons.append(FailureReason.SIMILAR_FAILURE)
            reason_details.append(
                f"Similar action failed recently (pattern probability: {recent_failure_prob:.0%})"
            )
            probabilities.append(recent_failure_prob)

        # 3. Check rate limit status
        rate_limit_prob = self._check_rate_limit(action, context)
        if rate_limit_prob > 0.3:
            reasons.append(FailureReason.RATE_LIMIT)
            limit_info = self._rate_limit_cache.get(action, {})
            used = limit_info.get("used", 0)
            max_limit = limit_info.get("max", 0)
            reason_details.append(
                f"Approaching rate limit ({used}/{max_limit})"
                if max_limit
                else "Rate limiting likely"
            )
            probabilities.append(rate_limit_prob)
            alternatives = self._get_rate_limit_alternatives(action)

        # 4. Check context for warning signs
        context_prob = self._analyze_context(action, context)
        if context_prob > 0.3:
            reasons.append(FailureReason.CONTEXT_MISMATCH)
            reason_details.append("Context suggests potential issues")
            probabilities.append(context_prob)

        # Calculate overall probability
        if probabilities:
            # Use weighted average with max influence
            max_prob = max(probabilities)
            avg_prob = sum(probabilities) / len(probabilities)
            overall_probability = 0.6 * max_prob + 0.4 * avg_prob
        else:
            overall_probability = 0.0

        # Determine confidence based on data availability
        confidence = self._calculate_confidence(action)

        # Determine if should proceed
        should_proceed = overall_probability < self.HIGH_FAILURE_THRESHOLD
        wait_seconds = self._get_wait_time(action, reasons)

        return FailurePrediction(
            action=action,
            probability=min(1.0, overall_probability),
            reasons=reasons,
            reason_details=reason_details,
            suggested_alternatives=alternatives,
            confidence=confidence,
            should_proceed=should_proceed,
            wait_seconds=wait_seconds,
        )

    def predict_for_agent_action(
        self,
        action: AgentAction,
        context: Dict[str, Any],
    ) -> FailurePrediction:
        """Predict failure for an AgentAction enum.

        Args:
            action: AgentAction enum value
            context: Current context

        Returns:
            FailurePrediction
        """
        return self.predict(action.value, context)

    def _check_recent_failures(self, action: str) -> float:
        """Check for recent failures of this action.

        Args:
            action: Action name

        Returns:
            Probability based on recent failures (0.0 to 1.0)
        """
        if not self._tracker:
            return 0.0

        # Get recent outcomes for this action
        recent = self._tracker.get_recent_outcomes(action=action, limit=10)

        if not recent:
            return 0.0

        # Filter to last 24 hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.RECENT_WINDOW_HOURS)
        recent_window = [o for o in recent if o.timestamp >= cutoff]

        if not recent_window:
            return 0.0

        # Calculate failure rate in recent window
        failures = sum(1 for o in recent_window if not o.success)
        return failures / len(recent_window)

    def _check_rate_limit(
        self,
        action: str,
        context: Dict[str, Any],
    ) -> float:
        """Check rate limit status for an action.

        Args:
            action: Action name
            context: Current context with possible rate limit info

        Returns:
            Probability of rate limit failure
        """
        # Check if we have cached rate limit info
        if action in self._rate_limit_cache:
            cache = self._rate_limit_cache[action]
            used = cache.get("used", 0)
            max_limit = cache.get("max", 100)
            reset_time = cache.get("reset_time")

            # Check if reset time has passed
            if reset_time and datetime.now(timezone.utc) > reset_time:
                self._rate_limit_cache[action] = {}
                return 0.0

            # Calculate probability based on usage
            if max_limit > 0:
                usage_ratio = used / max_limit
                if usage_ratio >= 0.9:
                    return 0.9
                elif usage_ratio >= 0.7:
                    return 0.5
                elif usage_ratio >= 0.5:
                    return 0.2

        # Check context for rate limit hints
        if context.get("rate_limit_warning"):
            return 0.7

        return 0.0

    def _analyze_context(
        self,
        action: str,
        context: Dict[str, Any],
    ) -> float:
        """Analyze context for warning signs.

        Args:
            action: Action name
            context: Current context

        Returns:
            Probability of context-related failure
        """
        warnings = 0
        total_checks = 4

        # Check for error state
        if context.get("error_state") or context.get("last_error"):
            warnings += 1

        # Check for retries
        if context.get("retry_count", 0) > 0:
            warnings += 1

        # Check for timeout hints
        if context.get("slow_response") or context.get("timeout_warning"):
            warnings += 1

        # Check for resource warnings
        if context.get("low_resources") or context.get("memory_warning"):
            warnings += 1

        return warnings / total_checks

    def _calculate_confidence(self, action: str) -> float:
        """Calculate prediction confidence based on data availability.

        Args:
            action: Action name

        Returns:
            Confidence value (0.0 to 1.0)
        """
        if not self._tracker:
            return 0.3  # Low confidence without tracker

        stats = self._tracker.get_action_stats(action)
        if not stats:
            return 0.3

        # More observations = higher confidence
        if stats.total_count >= 20:
            return 0.9
        elif stats.total_count >= 10:
            return 0.7
        elif stats.total_count >= 5:
            return 0.5
        else:
            return 0.3

    def _get_rate_limit_alternatives(self, action: str) -> List[str]:
        """Get alternative actions when rate limited.

        Args:
            action: Rate-limited action

        Returns:
            List of alternative action names
        """
        # Map actions to alternatives
        alternatives_map = {
            "search_tavily": ["ask_perplexity"],
            "ask_perplexity": ["search_tavily"],
            "post_tweet": ["send_telegram_message", "send_slack_message"],
            "send_discord_message": ["send_telegram_message", "send_slack_message"],
        }

        return alternatives_map.get(action, [])

    def _get_wait_time(
        self,
        action: str,
        reasons: List[FailureReason],
    ) -> float:
        """Get recommended wait time before retrying.

        Args:
            action: Action name
            reasons: Failure reasons

        Returns:
            Wait time in seconds
        """
        if FailureReason.RATE_LIMIT in reasons:
            # Check cache for reset time
            cache = self._rate_limit_cache.get(action, {})
            reset_time = cache.get("reset_time")
            if reset_time:
                wait = (reset_time - datetime.now(timezone.utc)).total_seconds()
                return max(0, wait)
            return 60.0  # Default 1 minute

        if FailureReason.TIMEOUT in reasons:
            return 30.0

        if FailureReason.SIMILAR_FAILURE in reasons:
            return 10.0

        return 0.0

    def record_rate_limit(
        self,
        action: str,
        used: int,
        max_limit: int,
        reset_time: Optional[datetime] = None,
    ) -> None:
        """Record rate limit information for an action.

        Args:
            action: Action name
            used: Number of requests used
            max_limit: Maximum requests allowed
            reset_time: When the limit resets
        """
        self._rate_limit_cache[action] = {
            "used": used,
            "max": max_limit,
            "reset_time": reset_time,
        }

    def record_failure(self, outcome: ActionOutcome) -> None:
        """Record a failure for pattern analysis.

        Args:
            outcome: The failed action outcome
        """
        if not outcome.success:
            self._recent_failures.append(outcome)
            # Keep only recent failures
            if len(self._recent_failures) > 100:
                self._recent_failures.pop(0)

    def clear(self) -> None:
        """Clear prediction data."""
        self._rate_limit_cache.clear()
        self._recent_failures.clear()
        logger.debug("FailurePredictor cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get predictor statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "rate_limits_tracked": len(self._rate_limit_cache),
            "recent_failures": len(self._recent_failures),
            "has_tracker": self._tracker is not None,
            "actions_with_limits": list(self._rate_limit_cache.keys()),
        }
