from unittest.mock import AsyncMock, MagicMock

import pytest

from src.context.context import ActionContext, ContextManager
from src.core.defs import AgentAction, AgentState
from src.planning.planning_module import PlanningModule


@pytest.fixture
def mock_context_manager():
    """Mock the ContextManager."""
    manager = MagicMock(spec=ContextManager)
    return manager


@pytest.fixture
def mock_llm():
    """Mock the LLM."""
    llm = AsyncMock()
    return llm


@pytest.fixture
def planning_module(mock_context_manager, mock_llm):
    """Create a PlanningModule instance with mocked dependencies."""
    module = PlanningModule(mock_context_manager)
    module.llm = mock_llm
    return module


def test_format_action_for_prompt(planning_module):
    """Test _format_action_for_prompt method."""
    # Test successful action
    action = ActionContext(action=AgentAction.ANALYZE_NEWS, state=AgentState.DEFAULT, reward=1.0)
    result = planning_module._format_action_for_prompt(action)
    assert result == "Action: analyze_news, Outcome: successful"

    # Test unsuccessful action
    action = ActionContext(
        action=AgentAction.SEARCH_GOOGLE_DRIVE, state=AgentState.DEFAULT, reward=0.0
    )
    result = planning_module._format_action_for_prompt(action)
    assert result == "Action: search_google_drive, Outcome: unsuccessful"


def test_format_actions_history(planning_module):
    """Test _format_actions_history method."""
    actions = [
        ActionContext(action=AgentAction.ANALYZE_NEWS, state=AgentState.DEFAULT, reward=1.0),
        ActionContext(action=AgentAction.SEARCH_GOOGLE_DRIVE, state=AgentState.DEFAULT, reward=0.0),
    ]
    result = planning_module._format_actions_history(actions)
    expected = "1. Action: analyze_news, Outcome: successful\n2. Action: search_google_drive, Outcome: unsuccessful"
    assert result == expected


def test_create_planning_prompt(planning_module, mock_context_manager):
    """Test _create_planning_prompt method."""
    # Mock recent actions
    recent_actions = [
        ActionContext(
            action=AgentAction.ANALYZE_NEWS, state=AgentState.WAITING_FOR_NEWS, reward=1.0
        ),
        ActionContext(action=AgentAction.SEARCH_GOOGLE_DRIVE, state=AgentState.DEFAULT, reward=0.0),
    ]
    mock_context_manager.get_context.return_value.get_recent_actions.return_value = recent_actions
    mock_actions_history = planning_module._format_actions_history(recent_actions)
    # Test with different states
    for state in AgentState:
        prompt = planning_module._create_planning_prompt(state)

        # Assert prompt structure
        assert prompt.startswith("Based on the following recent action history and current state")

        # Assert state & action are included
        assert f"\nCurrent State: {state.value}" in prompt
        assert f"\nRecent Actions History: {mock_actions_history}" in prompt
        # Assert actions history is included
        # assert "Recent Actions History: 1. Action: analyze_news, Outcome: successful" in prompt
        # assert "2. Action: search_google_drive, Outcome: unsuccessful" in prompt

        # Assert available actions
        available_actions = ", ".join([action.value for action in AgentAction])
        assert f"\nAvailable Actions: {available_actions}" in prompt

        # Assert response format instructions
        assert "Choose exactly one action from the available actions." in prompt
        assert "Respond with just the action name, nothing else." in prompt
        # Check for example format - either legacy format or new format with MCP tools
        assert "(e.g., analyze_news)" in prompt or "For example: analyze_news" in prompt


@pytest.mark.asyncio
async def test_get_action_valid_response(planning_module, mock_llm):
    """Test get_action with valid LLM response."""
    # Mock LLM response
    mock_llm.generate_response.return_value = "analyze_news"

    # Test with different states
    for state in AgentState:
        action = await planning_module.get_action(state)
        assert action == AgentAction.ANALYZE_NEWS
        mock_llm.generate_response.assert_called()


@pytest.mark.asyncio
async def test_get_action_invalid_response(planning_module, mock_llm):
    """Test get_action with invalid LLM response."""
    # Mock invalid LLM response
    mock_llm.generate_response.return_value = "invalid_action"

    action = await planning_module.get_action(AgentState.DEFAULT)
    assert action == AgentAction.IDLE  # Should fallback to IDLE


@pytest.mark.asyncio
async def test_get_action_llm_error(planning_module, mock_llm):
    """Test get_action when LLM throws an error."""
    # Mock LLM error
    mock_llm.generate_response.side_effect = Exception("LLM error")

    action = await planning_module.get_action(AgentState.DEFAULT)
    assert action == AgentAction.IDLE  # Should fallback to IDLE


@pytest.mark.asyncio
async def test_get_action_empty_response(planning_module, mock_llm):
    """Test get_action with empty LLM response."""
    # Mock empty response
    mock_llm.generate_response.return_value = ""

    action = await planning_module.get_action(AgentState.DEFAULT)
    assert action == AgentAction.IDLE  # Should fallback to IDLE
