import pytest

from src.feedback import FeedbackModule


@pytest.fixture
def feedback_module():
    """Create a FeedbackModule instance for testing."""
    return FeedbackModule()


def test_init(feedback_module):
    """Test FeedbackModule initialization."""
    assert isinstance(feedback_module.feedback_history, list)
    assert len(feedback_module.feedback_history) == 0


def test_collect_feedback_success(feedback_module):
    """Test collecting feedback for successful action."""
    action = "test_action"
    outcome = "success_result"

    score = feedback_module.collect_feedback(action, outcome)

    assert score == 1.0
    assert len(feedback_module.feedback_history) == 1
    entry = feedback_module.feedback_history[0]
    assert entry["action"] == action
    assert entry["outcome"] == outcome
    assert entry["score"] == 1.0
    assert entry["status"] == "success"


def test_collect_feedback_failure(feedback_module):
    """Test collecting feedback for failed action."""
    action = "test_action"
    outcome = None

    score = feedback_module.collect_feedback(action, outcome)

    assert score == -1.0
    assert len(feedback_module.feedback_history) == 1
    entry = feedback_module.feedback_history[0]
    assert entry["action"] == action
    assert entry["outcome"] is None
    assert entry["score"] == -1.0
    assert entry["status"] == "failure"


def test_get_feedback_history_empty(feedback_module):
    """Test getting feedback history when empty."""
    history = feedback_module.get_feedback_history()
    assert isinstance(history, list)
    assert len(history) == 0


def test_get_feedback_history_with_limit(feedback_module):
    """Test getting limited feedback history."""
    # Add multiple feedback entries
    for i in range(5):
        feedback_module.collect_feedback(f"action_{i}", f"outcome_{i}")

    # Test with different limits
    history = feedback_module.get_feedback_history(limit=3)
    assert len(history) == 3
    assert history[-1]["action"] == "action_4"
    assert history[0]["action"] == "action_2"


def test_get_feedback_history_full(feedback_module):
    """Test getting full feedback history."""
    # Add feedback entries
    actions = ["action1", "action2", "action3"]
    outcomes = ["outcome1", "outcome2", None]

    for action, outcome in zip(actions, outcomes):
        feedback_module.collect_feedback(action, outcome)

    history = feedback_module.get_feedback_history()
    assert len(history) == 3
    assert [entry["action"] for entry in history] == actions
    assert [entry["outcome"] for entry in history] == outcomes


def test_reset_feedback_history(feedback_module):
    """Test resetting feedback history."""
    # Add some feedback first
    feedback_module.collect_feedback("test_action", "test_outcome")
    assert len(feedback_module.feedback_history) == 1

    # Reset history
    feedback_module.reset_feedback_history()
    assert len(feedback_module.feedback_history) == 0
    assert isinstance(feedback_module.feedback_history, list)
