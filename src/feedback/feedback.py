from typing import Any, Dict, List, Optional

from loguru import logger


class FeedbackModule:
    """
    Module to collect and process feedback for agent actions.
    """

    def __init__(self):
        # Internal store for feedback history
        self.feedback_history: List[Dict[str, Any]] = []

    def collect_feedback(self, action: str, outcome: Optional[Any]) -> float:
        """
        Collects feedback for a given action and its outcome.

        Args:
            action (str): The name of the action performed.
            outcome (Any): The outcome of the action. Can be None for failure or some result for success.

        Returns:
            float: Feedback score (e.g., -1.0 for failure, 1.0 for success, 0.0 for neutral).
        """
        logger.debug(f"Collecting feedback for action '{action}'")

        # Define feedback logic
        if outcome is None:
            feedback_score = -1.0  # Failure
            feedback_status = "failure"
        else:
            feedback_score = 1.0  # Success (you can add more nuanced scoring)
            feedback_status = "success"

        # Log feedback to history
        feedback_entry = {
            "action": action,
            "outcome": outcome,
            "score": feedback_score,
            "status": feedback_status,
        }
        self.feedback_history.append(feedback_entry)

        logger.debug(f"Feedback recorded: {feedback_entry}")
        return feedback_score

    def get_feedback_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve the most recent feedback history.

        Args:
            limit (int): The number of feedback entries to retrieve.

        Returns:
            List[Dict[str, Any]]: Recent feedback entries.
        """
        return self.feedback_history[-limit:]

    def reset_feedback_history(self) -> None:
        """
        Clear the feedback history.
        """
        self.feedback_history = []
        logger.debug("Feedback history has been reset.")
