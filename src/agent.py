import asyncio
from typing import Any, Optional

from loguru import logger

from src.core.config import settings
from src.core.defs import AgentAction, AgentState
from src.execution import ExecutionModule
from src.feedback import FeedbackModule
from src.memory import get_memory_module
from src.planning import PlanningModule
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
        self.planning_module = PlanningModule()

        #: Initialize Execution Module
        self.execution_module = ExecutionModule()

        #: Initialize Feedback Module
        self.feedback_module = FeedbackModule()

        #: Start in a default state
        self.state = AgentState.DEFAULT  # "default"

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
                #    You might treat the entire system as one "state", or define states.
                logger.info(f"Current state: {self.state.value}")
                next_action = await self.planning_module.get_next_action(self.state)
                logger.info(f"Action chosen: {next_action.value}")

                # 2. Perform that action
                result = await self.execution_module.execute_action(next_action)
                logger.info(f"Outcome: {result}")

                # 3. Collect feedback
                reward = self.feedback_module.collect_feedback(
                    next_action.value, result.get("outcome")
                )
                logger.info(f"Reward: {reward}")

                # 4. Update state and memory
                self.state = AgentState.from_action(next_action)
                # self.memory_module.store(
                #     {
                #         "state": self.state.value,
                #         "action": next_action.value,
                #         "outcome": result.get("outcome", "Unknown"),
                #     }
                # )

                # 5. Sleep or yield
                logger.info("Let's rest a bit...")
                await asyncio.sleep(settings.AGENT_REST_TIME)

            except KeyboardInterrupt:
                logger.info("Agent runtime loop interrupted by user.")
                break
            except Exception as e:
                logger.error(f"Error in runtime loop: {e}")
                break
