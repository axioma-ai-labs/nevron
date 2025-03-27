from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class FeedbackType(Enum):
    BINARY = "binary"  # Default -1.0, 0.0, 1.0 scoring
    CUSTOM = "custom"  # Custom scoring logic
    WEIGHTED = "weighted"  # Weighted scoring based on action importance


@dataclass
class FeedbackConfig:
    action: str
    feedback_type: FeedbackType = FeedbackType.BINARY
    weight: float = 1.0  # Default weight for weighted feedback
    custom_feedback_scorer: Optional[Callable[[Any], float]] = None


class FeedbackModule:
    """
    Enhanced Feedback Module with advanced feedback logic.
    """

    def __init__(self):
        self.feedback_history: List[Dict[str, Any]] = []
        self.feedback_configs: Dict[str, FeedbackConfig] = {}
        self.action_weights: Dict[str, float] = {}  # Stores action-specific weights

    def register_feedback_config(self, config: FeedbackConfig) -> None:
        """
        Register custom feedback configuration for specific actions.

        Args:
            config: FeedbackConfig instance with custom settings
        """
        self.feedback_configs[config.action] = config
        logger.debug(f"Registered feedback config for action: {config.action}")

    def _get_feedback_config(self, action: str) -> FeedbackConfig:
        """
        Get feedback config for an action, falling back to default if not found.
        """
        return self.feedback_configs.get(action, FeedbackConfig(action=action))

    def _calculate_score(self, action: str, outcome: Any) -> float:
        """
        Calculate feedback score based on configured logic.
        """
        config = self._get_feedback_config(action)

        if config.feedback_type == FeedbackType.CUSTOM and config.custom_feedback_scorer:
            return config.custom_feedback_scorer(outcome)

        elif config.feedback_type == FeedbackType.WEIGHTED:
            base_score = 1.0 if outcome is not None else -1.0
            return base_score * config.weight

        # elif ...add more feedback score logic here
        # Default binary scoring
        if outcome is None:
            return -1.0
        return 1.0

    def collect_feedback(self, action: str, outcome: Optional[Any]) -> float:
        """
        Collect feedback for a given action and its outcome.

        Args:
            action: The name of the action performed
            outcome: The outcome of the action

        Returns:
            float: Calculated feedback score
        """
        logger.debug(f"Collecting feedback for action '{action}'")

        feedback_score = self._calculate_score(action, outcome)
        if feedback_score > 0:
            if (
                feedback_score < 1.0
                and self._get_feedback_config(action).feedback_type == FeedbackType.WEIGHTED
            ):
                feedback_status = "partial_success"
            else:
                feedback_status = "success"
        else:
            feedback_status = "failure"

        feedback_entry = {
            "action": action,
            "outcome": outcome,
            "score": feedback_score,
            "status": feedback_status,
            "timestamp": datetime.now(timezone.utc),
        }

        self.feedback_history.append(feedback_entry)
        logger.debug(f"Feedback recorded: {feedback_entry}")
        return feedback_score

    def analyze_feedback_trends(self, action: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze feedback trends for a specific action or overall.

        Args:
            action: Optional action to filter analysis (None means all actions)

        Returns:
            Dict with analysis results including success, partial success, and failure rates
        """
        # Filter feedbacks based on action (or include all if action is None)
        feedbacks = [f for f in self.feedback_history if not action or f["action"] == action]

        if not feedbacks:
            return {
                "action": action or "overall",
                "count": 0,
                "average_score": 0.0,
                "success_rate": 0.0,
                "partial_success_rate": 0.0,
                "failure_rate": 0.0,
                "most_common_outcome": None,
            }

        scores = [f["score"] for f in feedbacks]
        outcomes = [f["outcome"] for f in feedbacks]
        statuses = [f["status"] for f in feedbacks]

        return {
            "action": action or "overall",
            "count": len(feedbacks),
            "average_score": sum(scores) / len(scores),
            "success_rate": sum(1 for s in statuses if s == "success") / len(statuses) * 100,
            "partial_success_rate": sum(1 for s in statuses if s == "partial_success")
            / len(statuses)
            * 100,
            "failure_rate": sum(1 for s in statuses if s == "failure") / len(statuses) * 100,
            "most_common_outcome": max(set(outcomes), key=outcomes.count),
        }

    def get_feedback_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent feedback history.
        """
        return self.feedback_history[-limit:]

    def reset_feedback_history(self) -> None:
        """
        Clear the feedback history.
        """
        self.feedback_history = []
        logger.debug("Feedback history has been reset.")
