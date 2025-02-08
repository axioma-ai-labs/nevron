from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from loguru import logger

from src.agent import Agent
from src.core.defs import AgentAction, AgentState


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger for testing."""
    # arrange:
    mock_info = MagicMock()
    mock_debug = MagicMock()
    monkeypatch.setattr(logger, "info", mock_info)
    monkeypatch.setattr(logger, "debug", mock_debug)
    return mock_info, mock_debug


@pytest.fixture
def agent():
    """Create an agent instance with mocked dependencies."""
    with (
        patch("src.agent.get_memory_module"),
        patch("src.agent.PlanningModule"),
        patch("src.agent.FeedbackModule"),
    ):
        agent = Agent()
        # Make store method a coroutine
        agent.memory_module = MagicMock()
        agent.memory_module.store = AsyncMock()
        # Make search method a coroutine
        agent.memory_module.search = AsyncMock()
        return agent


@pytest.mark.parametrize(
    "action,expected_state",
    [
        (AgentAction.CHECK_SIGNAL, AgentState.JUST_ANALYZED_SIGNAL),
        (AgentAction.ANALYZE_NEWS, AgentState.JUST_ANALYZED_NEWS),
        (AgentAction.IDLE, AgentState.DEFAULT),
    ],
)
def test_update_state(agent, mock_logger, action, expected_state):
    """Test state updates based on different actions."""
    # act:
    agent._update_state(action)

    # assert:
    mock_info, _ = mock_logger
    assert agent.state == expected_state
    mock_info.assert_called_once_with(f"Agent state updated to: {expected_state.name}")


@pytest.mark.parametrize(
    "state,action,reward,next_state",
    [
        (AgentState.DEFAULT, AgentAction.CHECK_SIGNAL, 1.0, AgentState.JUST_ANALYZED_SIGNAL),
        (
            AgentState.JUST_ANALYZED_SIGNAL,
            AgentAction.ANALYZE_NEWS,
            0.5,
            AgentState.JUST_ANALYZED_NEWS,
        ),
        (AgentState.JUST_ANALYZED_NEWS, AgentAction.IDLE, -0.1, AgentState.DEFAULT),
    ],
)
def test_update_planning_policy(agent, state, action, reward, next_state):
    """Test updating the planning policy with different state-action pairs."""
    # arrange:
    agent.planning_module.update_q_table = MagicMock()

    # act:
    agent._update_planning_policy(state, action, reward, next_state)

    # assert:
    agent.planning_module.update_q_table.assert_called_once_with(state, action, reward, next_state)


@pytest.mark.parametrize(
    "action,outcome,expected_reward",
    [
        ("check_signal", "Signal detected", 1.0),
        ("analyze_news", None, 0.0),
        ("idle", "idle", 0.5),
    ],
)
def test_collect_feedback(agent, action, outcome, expected_reward):
    """Test collecting feedback for different actions and outcomes."""
    # arrange:
    agent.feedback_module.collect_feedback = MagicMock(return_value=expected_reward)

    # act:
    reward = agent._collect_feedback(action, outcome)

    # assert:
    assert reward == expected_reward
    agent.feedback_module.collect_feedback.assert_called_once_with(action, outcome)


@pytest.mark.asyncio
async def test_perform_planned_action_idle(agent, mock_logger):
    """Test performing IDLE action."""
    # arrange:
    mock_info, mock_debug = mock_logger

    # act:
    outcome = await agent._perform_planned_action(AgentAction.IDLE)

    # assert:
    assert outcome == "idle"
    mock_info.assert_any_call("Agent is idling.")
    mock_debug.assert_called_with("Stored performed action to memory.")
    agent.memory_module.store.assert_called_once()


@pytest.mark.asyncio
async def test_perform_planned_action_check_signal(agent, mock_logger):
    """Test performing CHECK_SIGNAL action."""
    # arrange:
    mock_info, mock_debug = mock_logger
    mock_analyze = AsyncMock(return_value="Signal detected")

    with patch("src.agent.analyze_signal", mock_analyze):
        # act:
        outcome = await agent._perform_planned_action(AgentAction.CHECK_SIGNAL)

        # assert:
        assert outcome == "Signal detected"
        mock_info.assert_any_call("Actionable signal perceived.")
        mock_debug.assert_called_with("Stored performed action to memory.")
        agent.memory_module.store.assert_called_once()
        mock_analyze.assert_called_once()


@pytest.mark.asyncio
async def test_perform_planned_action_check_signal_no_signal(agent, mock_logger):
    """Test performing CHECK_SIGNAL action with no signal detected."""
    # arrange:
    mock_info, mock_debug = mock_logger
    mock_analyze = AsyncMock(return_value=None)

    with patch("src.agent.analyze_signal", mock_analyze):
        # act:
        outcome = await agent._perform_planned_action(AgentAction.CHECK_SIGNAL)

        # assert:
        assert outcome is None
        mock_info.assert_any_call("No actionable signal detected.")
        mock_debug.assert_called_with("Stored performed action to memory.")
        agent.memory_module.store.assert_called_once()
        mock_analyze.assert_called_once()


@pytest.mark.asyncio
async def test_perform_planned_action_analyze_news(agent, mock_logger):
    """Test performing ANALYZE_NEWS action."""
    # arrange:
    mock_info, mock_debug = mock_logger
    agent.memory_module.search.return_value = [{"event": "Test news"}]
    mock_analyze = AsyncMock(return_value="News analyzed")

    with patch("src.agent.analyze_news_workflow", mock_analyze):
        # act:
        outcome = await agent._perform_planned_action(AgentAction.ANALYZE_NEWS)

        # assert:
        assert outcome == "News analyzed"
        mock_debug.assert_any_call("Retrieved memories: [{'event': 'Test news'}]")
        mock_debug.assert_any_call("Stored performed action to memory.")
        agent.memory_module.search.assert_called_once_with("news", top_k=1)
        agent.memory_module.store.assert_called_once()
        mock_analyze.assert_called_once_with("Test news")


@pytest.mark.asyncio
async def test_perform_planned_action_analyze_news_no_news(agent, mock_logger):
    """Test performing ANALYZE_NEWS action with no news found."""
    # arrange:
    mock_info, mock_debug = mock_logger
    agent.memory_module.search.return_value = []
    mock_analyze = AsyncMock(return_value="No news analyzed")

    with patch("src.agent.analyze_news_workflow", mock_analyze):
        # act:
        outcome = await agent._perform_planned_action(AgentAction.ANALYZE_NEWS)

        # assert:
        assert outcome == "No news analyzed"
        mock_debug.assert_any_call("Retrieved memories: []")
        mock_debug.assert_any_call("Stored performed action to memory.")
        agent.memory_module.search.assert_called_once_with("news", top_k=1)
        agent.memory_module.store.assert_called_once()
        mock_analyze.assert_called_once_with("No recent news found")
