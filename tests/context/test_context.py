"""Tests for the context module."""

import json
import os
import tempfile
from pathlib import Path
from typing import Dict

import pytest
from freezegun import freeze_time

from src.context.context import ActionContext, AgentContext, ContextManager
from src.core.defs import AgentAction, AgentState


@pytest.fixture
def temp_context_file():
    """Create a temporary context file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def sample_context_data() -> Dict:
    """Sample context data for testing."""
    return {
        "actions_history": [
            {
                "timestamp": "2024-01-24T10:00:00",
                "action": "analyze_news",
                "state": "default",
                "outcome": "News analyzed successfully",
                "reward": 1.0,
                "metadata": {"source": "test"},
            }
        ],
        "last_state": "default",
        "total_actions": 1,
        "total_rewards": 1.0,
        "metadata": {"test": True},
    }


def test_action_context_creation():
    """Test ActionContext creation and validation."""
    with freeze_time("2024-01-24 10:00:00"):
        action_context = ActionContext(
            action=AgentAction.ANALYZE_NEWS,
            state=AgentState.DEFAULT,
            outcome="Test outcome",
            reward=1.0,
            metadata={"test": True},
        )

        # assert action_context.timestamp == datetime(2024, 1, 24, 10, 0, 0)
        assert action_context.action == AgentAction.ANALYZE_NEWS
        assert action_context.state == AgentState.DEFAULT
        assert action_context.outcome == "Test outcome"
        assert action_context.reward == 1.0
        assert action_context.metadata == {"test": True}


def test_agent_context_creation():
    """Test AgentContext creation and default values."""
    context = AgentContext()
    assert context.actions_history == []
    assert context.last_state == AgentState.DEFAULT
    assert context.total_actions == 0
    assert context.total_rewards == 0.0
    assert context.metadata == {}


def test_agent_context_add_action():
    """Test adding actions to AgentContext."""
    context = AgentContext()

    # Add action without reward
    context.add_action(action=AgentAction.IDLE, state=AgentState.DEFAULT, outcome="Test idle")
    assert len(context.actions_history) == 1
    assert context.total_actions == 1
    assert context.total_rewards == 0.0

    # Add action with reward
    context.add_action(
        action=AgentAction.ANALYZE_NEWS,
        state=AgentState.JUST_ANALYZED_NEWS,
        outcome="Test news",
        reward=0.5,
    )
    assert len(context.actions_history) == 2
    assert context.total_actions == 2
    assert context.total_rewards == 0.5
    assert context.last_state == AgentState.JUST_ANALYZED_NEWS


def test_agent_context_queries():
    """Test AgentContext query methods."""
    context = AgentContext()

    # Add some test actions
    actions = [
        (AgentAction.IDLE, AgentState.DEFAULT),
        (AgentAction.ANALYZE_NEWS, AgentState.JUST_ANALYZED_NEWS),
        (AgentAction.CHECK_SIGNAL, AgentState.JUST_ANALYZED_SIGNAL),
        (AgentAction.ANALYZE_NEWS, AgentState.JUST_ANALYZED_NEWS),
        (AgentAction.IDLE, AgentState.DEFAULT),
    ]

    for action, state in actions:
        context.add_action(action=action, state=state)

    # Test get_recent_actions
    recent = context.get_recent_actions(n=3)
    assert len(recent) == 3
    assert recent[-1].action == AgentAction.IDLE

    # Test get_actions_in_state
    news_actions = context.get_actions_in_state(AgentState.JUST_ANALYZED_NEWS)
    assert len(news_actions) == 2
    assert all(a.state == AgentState.JUST_ANALYZED_NEWS for a in news_actions)

    # Test get_actions_by_type
    idle_actions = context.get_actions_by_type(AgentAction.IDLE)
    assert len(idle_actions) == 2
    assert all(a.action == AgentAction.IDLE for a in idle_actions)


def test_context_manager_save_load(temp_context_file, sample_context_data):
    """Test saving and loading context."""
    # Save context
    with open(temp_context_file, "w") as f:
        json.dump(sample_context_data, f)

    # Load context
    manager = ContextManager(context_path=temp_context_file)
    context = manager.get_context()

    assert len(context.actions_history) == 1
    assert context.total_actions == 1
    assert context.total_rewards == 1.0
    assert context.metadata == {"test": True}


def test_context_manager_add_action(temp_context_file):
    """Test adding actions through ContextManager."""
    manager = ContextManager(context_path=temp_context_file)

    manager.add_action(
        action=AgentAction.ANALYZE_NEWS,
        state=AgentState.DEFAULT,
        outcome="Test outcome",
        reward=1.0,
        metadata={"test": True},
    )

    # Verify action was added
    context = manager.get_context()
    assert len(context.actions_history) == 1
    assert context.total_actions == 1
    assert context.total_rewards == 1.0

    # Verify file was saved
    assert Path(temp_context_file).exists()
    with open(temp_context_file, "r") as f:
        saved_data = json.load(f)
        assert saved_data["total_actions"] == 1
        assert saved_data["total_rewards"] == 1.0


def test_context_manager_invalid_file(temp_context_file):
    """Test handling of invalid context file."""
    # Create invalid JSON file
    with open(temp_context_file, "w") as f:
        f.write("invalid json")

    # Should handle invalid file gracefully
    manager = ContextManager(context_path=temp_context_file)
    context = manager.get_context()
    assert isinstance(context, AgentContext)
    assert context.actions_history == []
