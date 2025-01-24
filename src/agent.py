import asyncio
from typing import Any, Optional

from loguru import logger

from src.context.context import ContextManager
from src.core.config import settings
from src.core.defs import AgentAction, AgentState
from src.feedback.feedback_module import FeedbackModule
from src.memory.memory_module import get_memory_module
from src.planning.planning_module import PlanningModule
from src.workflows.analyze_signal import analyze_signal
from src.workflows.research_news import analyze_news_workflow


class Agent:
    """
    Central runtime for an autonomous AI agent. Integrates:
      1. Perception Module
      2. Memory Module
      3. Planning Module (Q-learning or other RL)
      4. Execution Module
      5. Feedback Module
      6. Autonomy Engine
      7. Context Manager (for persistent state)

    ### Adding a New State
      1. Open `core/defs.py`.
      2. Add the new state to the `AgentState` class.
        class AgentState(Enum):
            DEFAULT = "default"
            ...
    """

    def __init__(self):
        #: Initialize Memory Module
        self.memory_module = get_memory_module()

        #: Initialize Planning Module with persistent Q-table
        self.planning_module = PlanningModule(
            actions=list(AgentAction),
            q_table_path=settings.PERSISTENT_Q_TABLE_PATH,  # Persistent Q-table file
        )

        #: Initialize Feedback Module
        self.feedback_module = FeedbackModule()

        #: Initialize Context Manager
        self.context_manager = ContextManager()

        #: Start with the last known state or default
        self.state = self.context_manager.get_context().last_state

        # ===== Agent Personality =====
        #: The agent's personality description
        self.personality = settings.AGENT_PERSONALITY
        #: The agent's goal
        self.goal = settings.AGENT_GOAL

    # --------------------------------------------------------------
    # UTILITY FUNCTIONS FOR STATE & PLANNING & FEEDBACK
    # --------------------------------------------------------------

    def _update_state(self, last_action: AgentAction):
        """Updates the agent's state based on the last action."""
        if last_action == AgentAction.CHECK_SIGNAL:
            self.state = AgentState.JUST_ANALYZED_SIGNAL
        elif last_action == AgentAction.ANALYZE_NEWS:
            self.state = AgentState.JUST_ANALYZED_NEWS
        elif last_action == AgentAction.IDLE:
            self.state = AgentState.DEFAULT

        logger.info(f"Agent state updated to: {self.state.name}")

    def _update_planning_policy(
        self, state: AgentState, action: AgentAction, reward: float, next_state: AgentState
    ):
        """Update the Q-learning table in the PlanningModule."""
        self.planning_module.update_q_table(state, action, reward, next_state)

    def _collect_feedback(self, action: str, outcome: Optional[Any]) -> float:
        """Collect feedback for the action & outcome in the FeedbackModule."""
        return self.feedback_module.collect_feedback(action, outcome)

    # --------------------------------------------------------------
    # RL-based PLANNING & EXECUTION
    # --------------------------------------------------------------

    async def _perform_planned_action(self, action_name: AgentAction) -> Optional[str]:
        """Perform the planned action and return the outcome."""
        outcome = None

        # 1. Perform the action based on the action name (arg)
        if action_name == AgentAction.IDLE:
            logger.info("Agent is idling.")
            outcome = action_name.value

        elif action_name == AgentAction.CHECK_SIGNAL:
            result = await analyze_signal()
            if result:
                logger.info("Actionable signal perceived.")
                outcome = result
            else:
                logger.info("No actionable signal detected.")
                outcome = None

        elif action_name == AgentAction.ANALYZE_NEWS:
            recent_news = "No recent news found"
            retrieved = await self.memory_module.search("news", top_k=1)
            logger.debug(f"Retrieved memories: {retrieved}")
            if retrieved:
                recent_news = retrieved[0]["event"]
            outcome = await analyze_news_workflow(recent_news)

        # 2. Store the outcome in memory
        event = f"Performed action '{action_name.value}'"
        await self.memory_module.store(
            event, action_name.value, str(outcome), metadata={"state": self.state.value}
        )
        logger.debug("Stored performed action to memory.")

        # 3. Update the state
        self._update_state(action_name)
        return outcome

    # --------------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------------

    async def start_runtime_loop(self) -> None:
        """The main runtime loop for the agent."""
        logger.info("Starting the autonomous agent runtime loop...")
        while True:
            try:
                # 1. Choose an action
                logger.info(f"Current state: {self.state.value}")
                action_name = self.planning_module.get_action(self.state)
                logger.info(f"Action chosen: {action_name.value}")

                # 2. Perform that action
                outcome = await self._perform_planned_action(action_name)
                logger.info(f"Outcome: {outcome}")

                # 3. Collect feedback
                reward = self._collect_feedback(action_name.value, outcome)
                logger.info(f"Reward: {reward}")

                # 4. Update context
                self.context_manager.add_action(
                    action=action_name,
                    state=self.state,
                    outcome=str(outcome) if outcome else None,
                    reward=reward,
                )

                # 5. Update the planning policy
                next_state = self.state
                logger.info(f"Next state: {next_state.value}")
                self._update_planning_policy(self.state, action_name, reward, next_state)

                # 6. Sleep or yield
                logger.info("Let's rest a bit...")
                await asyncio.sleep(settings.AGENT_REST_TIME)

            except KeyboardInterrupt:
                logger.info("Agent runtime loop interrupted by user.")
                break
            except Exception as e:
                logger.error(f"Error in runtime loop: {e}")
                break
