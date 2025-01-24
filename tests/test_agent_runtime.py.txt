"""Test the runtime loop of the agent (start_runtime_loop)."""

from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from loguru import logger

from src.agent import Agent
from src.core.defs import AgentAction, AgentState


@pytest.fixture
def mock_runtime_logger(monkeypatch):
    """Mock logger for runtime testing."""
    # arrange:
    mock_info = MagicMock()
    mock_error = MagicMock()
    mock_critical = MagicMock()
    monkeypatch.setattr(logger, "info", mock_info)
    monkeypatch.setattr(logger, "error", mock_error)
    monkeypatch.setattr(logger, "critical", mock_critical)
    return mock_info, mock_error, mock_critical


@pytest.fixture
def runtime_agent():
    """Create an agent instance with mocked dependencies for runtime testing."""
    with (
        patch("src.agent.get_memory_module"),
        patch("src.agent.PlanningModule"),
        patch("src.agent.FeedbackModule"),
    ):
        agent = Agent()
        # Mock memory module methods
        agent.memory_module = MagicMock()
        agent.memory_module.store = AsyncMock()
        agent.memory_module.search = AsyncMock()
        # Mock planning module methods
        agent.planning_module = MagicMock()
        agent.planning_module.get_action = MagicMock(return_value=AgentAction.IDLE)
        agent.planning_module.update_q_table = MagicMock()
        # Mock feedback module methods
        agent.feedback_module = MagicMock()
        agent.feedback_module.collect_feedback = MagicMock(return_value=1.0)
        return agent


@pytest.mark.asyncio
async def test_runtime_loop_one_iteration(runtime_agent, mock_runtime_logger):
    """Test one successful iteration of the runtime loop."""
    # arrange:
    mock_info, mock_error, mock_critical = mock_runtime_logger
    runtime_agent._perform_planned_action = AsyncMock(return_value="idle")

    # Mock asyncio.sleep to raise KeyboardInterrupt after first iteration
    with patch("asyncio.sleep", side_effect=KeyboardInterrupt):
        # act:
        await runtime_agent.start_runtime_loop()

    # assert:
    # Verify logging
    mock_info.assert_any_call("Starting the autonomous agent runtime loop...")
    mock_info.assert_any_call("Current state: default")
    mock_info.assert_any_call("Action chosen: idle")
    mock_info.assert_any_call("Outcome: idle")
    mock_info.assert_any_call("Reward: 1.0")
    mock_info.assert_any_call("Next state: default")
    mock_info.assert_any_call("Let's rest a bit...")
    mock_info.assert_any_call("Agent runtime loop interrupted by user.")

    # Verify method calls
    runtime_agent.planning_module.get_action.assert_called_once_with(AgentState.DEFAULT)
    runtime_agent._perform_planned_action.assert_called_once_with(AgentAction.IDLE)
    runtime_agent.feedback_module.collect_feedback.assert_called_once_with("idle", "idle")
    runtime_agent.planning_module.update_q_table.assert_called_once()

    # Verify no errors
    mock_error.assert_not_called()
    mock_critical.assert_not_called()


@pytest.mark.asyncio
async def test_runtime_loop_with_error(runtime_agent, mock_runtime_logger):
    """Test runtime loop with a runtime error."""
    # arrange:
    mock_info, mock_error, mock_critical = mock_runtime_logger
    runtime_agent.planning_module.get_action = MagicMock(side_effect=RuntimeError("Test error"))
    runtime_agent._perform_planned_action = AsyncMock()

    # act:
    await runtime_agent.start_runtime_loop()

    # assert:
    mock_info.assert_any_call("Starting the autonomous agent runtime loop...")
    mock_error.assert_called_once_with("Error in runtime loop: Test error")
    runtime_agent._perform_planned_action.assert_not_called()
    runtime_agent.feedback_module.collect_feedback.assert_not_called()
    runtime_agent.planning_module.update_q_table.assert_not_called()
    mock_critical.assert_not_called()


@pytest.mark.asyncio
async def test_runtime_loop_keyboard_interrupt(runtime_agent, mock_runtime_logger):
    """Test runtime loop with keyboard interrupt."""
    # arrange:
    mock_info, mock_error, mock_critical = mock_runtime_logger
    runtime_agent.planning_module.get_action = MagicMock(side_effect=KeyboardInterrupt)
    runtime_agent._perform_planned_action = AsyncMock()

    # act:
    await runtime_agent.start_runtime_loop()

    # assert:
    mock_info.assert_any_call("Starting the autonomous agent runtime loop...")
    mock_info.assert_any_call("Agent runtime loop interrupted by user.")
    runtime_agent._perform_planned_action.assert_not_called()
    runtime_agent.feedback_module.collect_feedback.assert_not_called()
    runtime_agent.planning_module.update_q_table.assert_not_called()
    mock_error.assert_not_called()
    mock_critical.assert_not_called()


@pytest.mark.asyncio
async def test_runtime_loop_multiple_actions(runtime_agent, mock_runtime_logger):
    """Test runtime loop with multiple different actions before interruption."""
    # arrange:
    mock_info, mock_error, mock_critical = mock_runtime_logger

    # Setup sequence of actions
    actions = [AgentAction.CHECK_SIGNAL, AgentAction.ANALYZE_NEWS, AgentAction.IDLE]
    outcomes = ["signal detected", "news analyzed", "idle"]
    rewards = [1.0, 0.5, 0.0]

    runtime_agent.planning_module.get_action = MagicMock(side_effect=actions)
    runtime_agent._perform_planned_action = AsyncMock(side_effect=outcomes)
    runtime_agent.feedback_module.collect_feedback = MagicMock(side_effect=rewards)

    # Make sleep raise KeyboardInterrupt after three iterations
    sleep_counter = 0

    async def mock_sleep(seconds):
        nonlocal sleep_counter
        sleep_counter += 1
        if sleep_counter >= 3:
            raise KeyboardInterrupt

    with patch("asyncio.sleep", side_effect=mock_sleep):
        # act:
        await runtime_agent.start_runtime_loop()

    # assert:
    assert runtime_agent.planning_module.get_action.call_count == 3
    assert runtime_agent._perform_planned_action.call_count == 3
    assert runtime_agent.feedback_module.collect_feedback.call_count == 3
    assert runtime_agent.planning_module.update_q_table.call_count == 3

    # Verify action sequence
    runtime_agent._perform_planned_action.assert_has_calls(
        [call(AgentAction.CHECK_SIGNAL), call(AgentAction.ANALYZE_NEWS), call(AgentAction.IDLE)]
    )

    mock_error.assert_not_called()
    mock_critical.assert_not_called()
