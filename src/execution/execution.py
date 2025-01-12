from loguru import logger

from src.core.defs import AgentAction
from src.workflows.analyze_signal import analyze_signal
from src.workflows.research_news import analyze_news_workflow


class ExecutionModule:
    """Module to execute agent actions."""

    async def execute_action(self, action: AgentAction) -> dict:
        """
        Execute the given action and return the result.

        Args:
            action (AgentAction): The action to execute.
            context (dict): Context to pass to the action.

        Returns:
            dict: Outcome and status of the action.
        """
        try:
            if action == AgentAction.CHECK_SIGNAL:
                result = await analyze_signal()
                return {"status": "success", "outcome": result or "No signal"}

            elif action == AgentAction.ANALYZE_NEWS:
                recent_news = "Placeholder"
                result = await analyze_news_workflow(recent_news)
                return {"status": "success", "outcome": result or "No outcome"}

            elif action == AgentAction.IDLE:
                logger.info("Agent is idling.")
                return {"status": "success", "outcome": "Idling"}

        except Exception as e:
            logger.error(f"Error executing action {action}: {e}")
            return {"status": "error", "outcome": str(e)}
