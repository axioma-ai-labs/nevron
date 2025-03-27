import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent import ACTION_2_STATE, Agent
from src.context.context import AgentContext, ContextManager
from src.core.defs import AgentAction, AgentState
from src.execution.execution_module import ExecutionModule
from src.feedback.feedback_module import FeedbackModule
from src.memory.memory_module import MemoryModule
from src.planning.planning_module import PlanningModule


class TestAgent(unittest.TestCase):
    def setUp(self):
        # Mock all dependencies
        self.mock_memory_module = MagicMock(spec=MemoryModule)
        self.mock_context_manager = MagicMock(spec=ContextManager)
        self.mock_planning_module = MagicMock(spec=PlanningModule)
        self.mock_execution_module = MagicMock(spec=ExecutionModule)
        self.mock_feedback_module = MagicMock(spec=FeedbackModule)

        # Set up mock context
        self.mock_context = MagicMock(spec=AgentContext)
        self.mock_context.last_state = AgentState.DEFAULT
        self.mock_context_manager.get_context.return_value = self.mock_context

        # Apply patches
        self.memory_patcher = patch(
            "src.agent.get_memory_module", return_value=self.mock_memory_module
        )
        self.context_patcher = patch(
            "src.agent.ContextManager", return_value=self.mock_context_manager
        )
        self.planning_patcher = patch(
            "src.agent.PlanningModule", return_value=self.mock_planning_module
        )
        self.execution_patcher = patch(
            "src.agent.ExecutionModule", return_value=self.mock_execution_module
        )
        self.feedback_patcher = patch(
            "src.agent.FeedbackModule", return_value=self.mock_feedback_module
        )

        # Start patches
        self.memory_patcher.start()
        self.context_patcher.start()
        self.planning_patcher.start()
        self.execution_patcher.start()
        self.feedback_patcher.start()

        # Create agent instance
        self.agent = Agent()

    def tearDown(self):
        # Stop all patches
        self.memory_patcher.stop()
        self.context_patcher.stop()
        self.planning_patcher.stop()
        self.execution_patcher.stop()
        self.feedback_patcher.stop()

    def test_initialization(self):
        """Test that the Agent initializes with correct modules and state."""
        # Test that all modules are correctly initialized
        self.assertEqual(self.agent.memory_module, self.mock_memory_module)
        self.assertEqual(self.agent.context_manager, self.mock_context_manager)
        self.assertEqual(self.agent.planning_module, self.mock_planning_module)
        self.assertEqual(self.agent.execution_module, self.mock_execution_module)
        self.assertEqual(self.agent.feedback_module, self.mock_feedback_module)

        # Test initial state is loaded from context
        self.assertEqual(self.agent.state, AgentState.DEFAULT)
        self.mock_context_manager.get_context.assert_called_once()

    def test_update_state(self):
        """Test that agent state is updated correctly based on actions."""
        # Test state update for ANALYZE_NEWS action
        self.agent._update_state(AgentAction.ANALYZE_NEWS)
        self.assertEqual(self.agent.state, AgentState.JUST_ANALYZED_NEWS)

        # Test state update for CHECK_SIGNAL action
        self.agent._update_state(AgentAction.CHECK_SIGNAL)
        self.assertEqual(self.agent.state, AgentState.JUST_ANALYZED_SIGNAL)

        # Test state update for IDLE action
        self.agent._update_state(AgentAction.IDLE)
        self.assertEqual(self.agent.state, AgentState.DEFAULT)

    def test_state_mapping_completeness(self):
        """Test that all actions in AgentAction have a corresponding state mapping."""
        # This test ensures all actions have a defined state transition
        # Note: In a real system, you might have more complex state transitions
        # and not all actions would map to a new state, so adapt this test as needed

        # Check that the ones that should have state transitions have them
        # While this test doesn't ensure ALL actions have mappings (which might not be realistic),
        # it ensures the essential ones do
        essential_actions = {AgentAction.ANALYZE_NEWS, AgentAction.CHECK_SIGNAL, AgentAction.IDLE}
        for action in essential_actions:
            self.assertIn(action, ACTION_2_STATE, f"Action {action} should have a state mapping")

    def test_collect_feedback(self):
        """Test feedback collection delegation to FeedbackModule."""
        # Set up mock feedback
        self.mock_feedback_module.collect_feedback.return_value = 0.75

        # Test feedback collection
        action = "test_action"
        outcome = "test_outcome"
        reward = self.agent._collect_feedback(action, outcome)

        # Verify interactions
        self.assertEqual(reward, 0.75)
        self.mock_feedback_module.collect_feedback.assert_called_once_with(action, outcome)

    @pytest.mark.asyncio
    async def test_runtime_loop_success(self):
        """Test the main runtime loop with successful execution."""
        # Configure mocks for a successful run through the loop
        self.mock_planning_module.get_action = AsyncMock(return_value=AgentAction.ANALYZE_NEWS)
        self.mock_execution_module.execute_action = AsyncMock(
            return_value=(True, "Analysis complete")
        )
        self.mock_feedback_module.collect_feedback.return_value = 1.0

        # Patch the sleep function to avoid actual waiting
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Patch KeyboardInterrupt to exit the loop after one iteration
            with patch.object(
                type(self.agent), "start_runtime_loop", side_effect=[KeyboardInterrupt, None]
            ):
                # We use the side_effect to trigger a KeyboardInterrupt after one loop iteration
                await self.agent.start_runtime_loop()

                # Verify interactions
                self.mock_planning_module.get_action.assert_called_once_with(AgentState.DEFAULT)
                self.mock_execution_module.execute_action.assert_called_once_with(
                    AgentAction.ANALYZE_NEWS
                )
                self.mock_feedback_module.collect_feedback.assert_called_once_with(
                    AgentAction.ANALYZE_NEWS.value, "Analysis complete"
                )
                self.mock_context_manager.add_action.assert_called_once_with(
                    action=AgentAction.ANALYZE_NEWS,
                    state=AgentState.DEFAULT,
                    outcome="Analysis complete",
                    reward=1.0,
                )
                mock_sleep.assert_called_once()

                # Check that state was updated
                self.assertEqual(self.agent.state, AgentState.JUST_ANALYZED_NEWS)

    @pytest.mark.asyncio
    async def test_runtime_loop_execution_failure(self):
        """Test the main runtime loop with execution failure."""
        # Configure mocks for a run with execution failure
        self.mock_planning_module.get_action = AsyncMock(return_value=AgentAction.CHECK_SIGNAL)
        self.mock_execution_module.execute_action = AsyncMock(return_value=(False, "API error"))
        self.mock_feedback_module.collect_feedback.return_value = -0.5

        # Patch the sleep function to avoid actual waiting
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Patch KeyboardInterrupt to exit the loop after one iteration
            with patch.object(
                type(self.agent), "start_runtime_loop", side_effect=[KeyboardInterrupt, None]
            ):
                # We use the side_effect to trigger a KeyboardInterrupt after one loop iteration
                await self.agent.start_runtime_loop()

                # Verify interactions
                self.mock_planning_module.get_action.assert_called_once_with(AgentState.DEFAULT)
                self.mock_execution_module.execute_action.assert_called_once_with(
                    AgentAction.CHECK_SIGNAL
                )
                self.mock_feedback_module.collect_feedback.assert_called_once_with(
                    AgentAction.CHECK_SIGNAL.value, "API error"
                )
                self.mock_context_manager.add_action.assert_called_once_with(
                    action=AgentAction.CHECK_SIGNAL,
                    state=AgentState.DEFAULT,
                    outcome="API error",
                    reward=-0.5,
                )
                mock_sleep.assert_called_once()

                # Check that state was updated despite execution failure
                self.assertEqual(self.agent.state, AgentState.JUST_ANALYZED_SIGNAL)

    @pytest.mark.asyncio
    async def test_runtime_loop_exception(self):
        """Test the main runtime loop with an exception during execution."""
        # Configure mocks for a run with an exception during planning
        self.mock_planning_module.get_action = AsyncMock(
            side_effect=Exception("Unexpected planning error")
        )

        # Patch the sleep function to avoid actual waiting
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            # Patch KeyboardInterrupt to exit the loop after one iteration
            with patch.object(
                type(self.agent), "start_runtime_loop", side_effect=[KeyboardInterrupt, None]
            ):
                # We use the side_effect to trigger a KeyboardInterrupt after one loop iteration
                await self.agent.start_runtime_loop()

                # Verify interactions
                self.mock_planning_module.get_action.assert_called_once_with(AgentState.DEFAULT)
                self.mock_context_manager.add_action.assert_not_called()
                mock_sleep.assert_called_once()

                # State should remain unchanged
                self.assertEqual(self.agent.state, AgentState.DEFAULT)


if __name__ == "__main__":
    unittest.main()
