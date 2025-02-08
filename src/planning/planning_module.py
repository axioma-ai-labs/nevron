"""Planning module for the agent's decision making using LLM."""

from typing import List

from loguru import logger

from src.context.context import ActionContext, ContextManager
from src.core.defs import AgentAction, AgentState
from src.llm.llm import LLM


class PlanningModule:
    """LLM-based planning module for high-level autonomous decisions."""

    def __init__(self, context_manager: ContextManager):
        """
        Initialize the planning module.

        Args:
            context_manager: Context manager instance for action history
        """
        self.context_manager = context_manager
        self.llm = LLM()

    def _format_action_for_prompt(self, action: ActionContext) -> str:
        """Format a single action for the prompt."""
        success = "successful" if action.reward and action.reward > 0 else "unsuccessful"
        return f"Action: {action.action.value}, Outcome: {success}"

    def _format_actions_history(self, actions: List[ActionContext]) -> str:
        """Format action history for the prompt."""
        return "\n".join(
            f"{i + 1}. {self._format_action_for_prompt(action)}" for i, action in enumerate(actions)
        )

    def _create_planning_prompt(self, current_state: AgentState) -> str:
        """Create prompt for the LLM."""
        # Get recent actions
        recent_actions = self.context_manager.get_context().get_recent_actions(n=5)
        actions_history = self._format_actions_history(recent_actions)

        # Available actions
        available_actions = ", ".join([action.value for action in AgentAction])

        return (
            f"Based on the following recent action history and current state, choose the next action."
            f"\nCurrent State: {current_state.value}\nRecent Actions History: {actions_history} "
            f"\nAvailable Actions: {available_actions}\nChoose exactly one action from the available "
            f"actions. Respond with just the action name, nothing else. For example: analyze_news"
        )

    async def get_action(self, current_state: AgentState) -> AgentAction:
        """
        Get the next action using LLM.

        Args:
            current_state: Current state of the agent

        Returns:
            AgentAction: The chosen action
        """
        try:
            # Create planning prompt
            prompt = self._create_planning_prompt(current_state)
            logger.debug(f"Planning prompt: {prompt}")

            # Get LLM response
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.generate_response(messages)
            logger.debug(f"LLM response: {response}")

            # Parse response to get action
            action_str = response.strip().lower()

            # Validate action
            try:
                return AgentAction(action_str)
            except ValueError:
                logger.error(f"Invalid action from LLM: {action_str}")
                return AgentAction.IDLE  # Fallback to IDLE if invalid action

        except Exception as e:
            logger.error(f"Error in planning: {e}")
            return AgentAction.IDLE  # Fallback to IDLE on error
