import json
from unittest.mock import MagicMock

import pytest
from loguru import logger

from src.core.defs import AgentAction, AgentState
from src.planning.planning_module import PlanningModule


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger for testing."""
    mock_debug = MagicMock()
    mock_error = MagicMock()
    monkeypatch.setattr(logger, "debug", mock_debug)
    monkeypatch.setattr(logger, "error", mock_error)
    return mock_debug, mock_error


@pytest.fixture
def mock_q_table():
    """Create a mock Q-table for testing."""
    return {
        "DEFAULT": [0.0, 0.1, 0.2],
        "JUST_ANALYZED_SIGNAL": [0.3, 0.4, 0.5],
        "JUST_ANALYZED_NEWS": [0.6, 0.7, 0.8],
    }


@pytest.fixture
def planning_module(tmp_path):
    """Create a PlanningModule instance with a temporary Q-table path."""
    q_table_path = tmp_path / "test_q_table.json"
    return PlanningModule(
        actions=[AgentAction.IDLE, AgentAction.CHECK_SIGNAL, AgentAction.ANALYZE_NEWS],
        q_table_path=str(q_table_path),
        planning_alpha=0.1,
        planning_gamma=0.95,
        planning_epsilon=0.1,
    )


def test_init_default_values():
    """Test PlanningModule initialization with default values."""
    module = PlanningModule()

    assert module.actions == list(AgentAction)
    assert module.alpha == 0.1  # Default from settings
    assert module.gamma == 0.95  # Default from settings
    assert module.epsilon == 0.1  # Default from settings
    assert isinstance(module.q_table, dict)


def test_init_custom_values(tmp_path):
    """Test PlanningModule initialization with custom values."""
    custom_actions = [AgentAction.IDLE, AgentAction.CHECK_SIGNAL]
    q_table_path = tmp_path / "custom_q_table.json"

    module = PlanningModule(
        actions=custom_actions,
        q_table_path=str(q_table_path),
        planning_alpha=0.2,
        planning_gamma=0.8,
        planning_epsilon=0.15,
    )

    assert module.actions == custom_actions
    assert module.alpha == 0.2
    assert module.gamma == 0.8
    assert module.epsilon == 0.15
    assert isinstance(module.q_table, dict)


def test_load_q_table_existing(mock_logger, mock_q_table, tmp_path):
    """Test loading an existing Q-table from file."""
    q_table_path = tmp_path / "existing_q_table.json"
    with open(q_table_path, "w") as f:
        json.dump(mock_q_table, f)

    module = PlanningModule(q_table_path=str(q_table_path))
    mock_debug, _ = mock_logger

    assert module.q_table == mock_q_table
    mock_debug.assert_called_once_with(f"Loaded Q-table from {q_table_path}")


def test_load_q_table_nonexistent(mock_logger):
    """Test loading Q-table when file doesn't exist."""
    module = PlanningModule(q_table_path="nonexistent_path.json")
    mock_debug, _ = mock_logger

    assert module.q_table == {}
    mock_debug.assert_not_called()


def test_save_q_table_success(mock_logger, planning_module, mock_q_table):
    """Test successful Q-table saving."""
    planning_module.q_table = mock_q_table
    planning_module._save_q_table()
    mock_debug, _ = mock_logger

    # Verify file contents
    with open(planning_module.q_table_path, "r") as f:
        saved_table = json.load(f)

    assert saved_table == mock_q_table
    mock_debug.assert_called_once_with(f"Q-table saved to {planning_module.q_table_path}")


def test_save_q_table_failure(mock_logger):
    """Test Q-table saving when there's an error."""
    module = PlanningModule(q_table_path="/invalid/path/q_table.json")
    _, mock_error = mock_logger

    module._save_q_table()
    mock_error.assert_called_once()
    assert "Failed to save Q-table" in mock_error.call_args[0][0]


@pytest.mark.parametrize(
    "new_state",
    [AgentState.DEFAULT, AgentState.JUST_ANALYZED_SIGNAL, AgentState.JUST_ANALYZED_NEWS],
)
def test_get_action_new_state(planning_module, new_state):
    """Test action selection for previously unseen states."""
    action = planning_module.get_action(new_state)

    # Verify action is valid
    assert isinstance(action, AgentAction)
    assert action in planning_module.actions

    # Verify Q-table was properly initialized for the state
    assert new_state.value in planning_module.q_table
    assert len(planning_module.q_table[new_state.value]) == len(planning_module.actions)

    # Verify Q-values are initialized to zeros
    assert all(q == 0.0 for q in planning_module.q_table[new_state.value])


def test_update_q_table(planning_module):
    """Test Q-table update with new experience."""
    # Initialize states and action
    state = AgentState.DEFAULT
    action = AgentAction.CHECK_SIGNAL
    reward = 1.0
    next_state = AgentState.JUST_ANALYZED_SIGNAL

    # First, get an action to ensure Q-table is initialized for both states
    planning_module.get_action(state)
    planning_module.get_action(next_state)

    # Get initial Q-value
    action_idx = planning_module.actions.index(action)
    initial_q = planning_module.q_table[state.value][action_idx]

    # Update Q-table
    planning_module.update_q_table(state, action, reward, next_state)

    # Get updated Q-value
    updated_q = planning_module.q_table[state.value][action_idx]

    # Verify Q-value was updated
    assert updated_q != initial_q
    # Verify both states exist in Q-table
    assert state.value in planning_module.q_table
    assert next_state.value in planning_module.q_table
    # Verify Q-values array length matches number of actions
    assert len(planning_module.q_table[state.value]) == len(planning_module.actions)
    assert len(planning_module.q_table[next_state.value]) == len(planning_module.actions)
    # Verify the update followed Q-learning formula
    expected_q = initial_q + planning_module.alpha * (
        reward + planning_module.gamma * max(planning_module.q_table[next_state.value]) - initial_q
    )
    assert abs(updated_q - expected_q) < 1e-10  # Using small epsilon for float comparison
