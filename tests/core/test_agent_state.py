"""Tests for agent state management (SharedStateManager and related classes)."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.core.agent_state import (
    AgentRuntimeState,
    CycleInfo,
    RecentCycles,
    SharedStateManager,
    reset_state_manager,
)


@pytest.fixture
def temp_state_dir():
    """Create a temporary directory for state files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def state_manager(temp_state_dir):
    """Create a SharedStateManager with a temporary directory."""
    reset_state_manager()
    manager = SharedStateManager(state_dir=temp_state_dir)
    yield manager
    reset_state_manager()


class TestAgentRuntimeState:
    """Tests for AgentRuntimeState dataclass."""

    def test_default_values(self):
        """Test that AgentRuntimeState has correct default values."""
        state = AgentRuntimeState()
        assert state.pid is None
        assert state.status == "stopped"
        assert state.is_running is False
        assert state.agent_state == "unknown"
        assert state.mcp_enabled is False
        assert state.cycle_count == 0
        assert state.total_rewards == 0.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        state = AgentRuntimeState(
            pid=12345,
            status="running",
            is_running=True,
            agent_state="active",
        )
        data = state.to_dict()
        assert data["pid"] == 12345
        assert data["status"] == "running"
        assert data["is_running"] is True
        assert data["agent_state"] == "active"

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "pid": 12345,
            "status": "running",
            "is_running": True,
            "agent_state": "active",
            "extra_field": "should be ignored",
        }
        state = AgentRuntimeState.from_dict(data)
        assert state.pid == 12345
        assert state.status == "running"
        assert state.is_running is True
        assert state.agent_state == "active"


class TestCycleInfo:
    """Tests for CycleInfo dataclass."""

    def test_creation(self):
        """Test CycleInfo creation."""
        cycle = CycleInfo(
            cycle_id="cycle_001",
            timestamp="2024-01-01T12:00:00Z",
            action="analyze_news",
            state_before="default",
            state_after="just_analyzed_news",
            success=True,
            reward=1.0,
        )
        assert cycle.cycle_id == "cycle_001"
        assert cycle.action == "analyze_news"
        assert cycle.success is True
        assert cycle.reward == 1.0

    def test_to_dict_from_dict(self):
        """Test round-trip conversion."""
        cycle = CycleInfo(
            cycle_id="cycle_001",
            timestamp="2024-01-01T12:00:00Z",
            action="check_signal",
            state_before="default",
            state_after="just_analyzed_signal",
            success=False,
            outcome="API error",
            error="Connection timeout",
        )
        data = cycle.to_dict()
        restored = CycleInfo.from_dict(data)
        assert restored.cycle_id == cycle.cycle_id
        assert restored.action == cycle.action
        assert restored.success == cycle.success
        assert restored.error == cycle.error


class TestRecentCycles:
    """Tests for RecentCycles collection."""

    def test_add_cycle(self):
        """Test adding cycles to the collection."""
        cycles = RecentCycles()
        cycle1 = CycleInfo(
            cycle_id="c1",
            timestamp="2024-01-01T12:00:00Z",
            action="action1",
            state_before="s1",
            state_after="s2",
            success=True,
        )
        cycle2 = CycleInfo(
            cycle_id="c2",
            timestamp="2024-01-01T12:01:00Z",
            action="action2",
            state_before="s2",
            state_after="s3",
            success=True,
        )
        cycles.add_cycle(cycle1)
        cycles.add_cycle(cycle2)

        # Most recent first
        assert len(cycles.cycles) == 2
        assert cycles.cycles[0].cycle_id == "c2"
        assert cycles.cycles[1].cycle_id == "c1"

    def test_max_cycles_limit(self):
        """Test that cycles are limited to max_cycles."""
        cycles = RecentCycles(max_cycles=3)
        for i in range(5):
            cycle = CycleInfo(
                cycle_id=f"c{i}",
                timestamp=f"2024-01-01T12:0{i}:00Z",
                action=f"action{i}",
                state_before="s1",
                state_after="s2",
                success=True,
            )
            cycles.add_cycle(cycle)

        assert len(cycles.cycles) == 3
        # Most recent cycles should be kept
        assert cycles.cycles[0].cycle_id == "c4"
        assert cycles.cycles[1].cycle_id == "c3"
        assert cycles.cycles[2].cycle_id == "c2"


class TestSharedStateManager:
    """Tests for SharedStateManager."""

    def test_initialization(self, state_manager):
        """Test that state manager initializes correctly."""
        state = state_manager.get_state()
        assert state.status == "stopped"
        assert state.is_running is False

    def test_update_state(self, state_manager):
        """Test updating state fields."""
        state_manager.update_state(
            status="running",
            is_running=True,
            agent_state="active",
        )
        state = state_manager.get_state()
        assert state.status == "running"
        assert state.is_running is True
        assert state.agent_state == "active"

    def test_set_running(self, state_manager):
        """Test marking agent as running."""
        state_manager.set_running(
            pid=12345,
            personality="test personality",
            goal="test goal",
        )
        state = state_manager.get_state()
        assert state.pid == 12345
        assert state.status == "running"
        assert state.is_running is True
        assert state.personality == "test personality"
        assert state.goal == "test goal"
        assert state.last_heartbeat is not None

    def test_set_stopped(self, state_manager):
        """Test marking agent as stopped."""
        # First set as running
        state_manager.set_running(pid=12345)

        # Then stop
        state_manager.set_stopped()
        state = state_manager.get_state()
        assert state.status == "stopped"
        assert state.is_running is False

    def test_set_stopped_with_error(self, state_manager):
        """Test stopping with error."""
        state_manager.set_stopped(error="Test error")
        state = state_manager.get_state()
        assert state.status == "error"
        assert state.last_error == "Test error"
        assert state.error_count == 1

    def test_heartbeat(self, state_manager):
        """Test heartbeat updates timestamp."""
        state_manager.heartbeat()
        state = state_manager.get_state()
        assert state.last_heartbeat is not None

        # Parse the timestamp to verify it's valid
        heartbeat = datetime.fromisoformat(state.last_heartbeat.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        # Should be within 5 seconds
        assert (now - heartbeat).total_seconds() < 5

    def test_is_agent_alive_with_recent_heartbeat(self, state_manager):
        """Test is_agent_alive returns True with recent heartbeat."""
        state_manager.heartbeat()
        assert state_manager.is_agent_alive(timeout_seconds=60.0) is True

    def test_is_agent_alive_with_old_heartbeat(self, state_manager):
        """Test is_agent_alive returns False with old heartbeat."""
        # Set an old heartbeat
        old_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        state_manager.update_state(last_heartbeat=old_time.isoformat())

        # Should not be alive with 60 second timeout
        assert state_manager.is_agent_alive(timeout_seconds=60.0) is False

    def test_is_agent_alive_no_heartbeat(self, state_manager):
        """Test is_agent_alive returns False when no heartbeat."""
        state_manager.update_state(last_heartbeat=None)
        assert state_manager.is_agent_alive() is False

    def test_is_agent_alive_invalid_heartbeat(self, state_manager):
        """Test is_agent_alive handles invalid heartbeat gracefully."""
        state_manager.update_state(last_heartbeat="invalid-timestamp")
        assert state_manager.is_agent_alive() is False

    def test_update_cycle_info(self, state_manager):
        """Test updating cycle info."""
        state_manager.update_cycle_info(
            action="analyze_news",
            agent_state="just_analyzed_news",
            success=True,
            reward=1.5,
        )
        state = state_manager.get_state()
        assert state.cycle_count == 1
        assert state.agent_state == "just_analyzed_news"
        assert state.total_rewards == 1.5
        assert state.successful_actions == 1
        assert state.failed_actions == 0

    def test_update_cycle_info_failed(self, state_manager):
        """Test updating cycle info for failed action."""
        state_manager.update_cycle_info(
            action="check_signal",
            agent_state="default",
            success=False,
            reward=-0.5,
        )
        state = state_manager.get_state()
        assert state.cycle_count == 1
        assert state.failed_actions == 1
        assert state.successful_actions == 0
        assert state.total_rewards == -0.5

    def test_set_current_action(self, state_manager):
        """Test setting current action."""
        state_manager.set_current_action("analyze_news")
        state = state_manager.get_state()
        assert state.current_action == "analyze_news"

    def test_update_mcp_status(self, state_manager):
        """Test updating MCP status."""
        state_manager.update_mcp_status(
            enabled=True,
            connected_servers=3,
            available_tools=15,
        )
        state = state_manager.get_state()
        assert state.mcp_enabled is True
        assert state.mcp_connected_servers == 3
        assert state.mcp_available_tools == 15

    def test_add_cycle(self, state_manager):
        """Test adding a cycle to history."""
        cycle = CycleInfo(
            cycle_id="test_cycle",
            timestamp=datetime.now(timezone.utc).isoformat(),
            action="analyze_news",
            state_before="default",
            state_after="just_analyzed_news",
            success=True,
            reward=1.0,
        )
        state_manager.add_cycle(cycle)

        cycles = state_manager.get_recent_cycles()
        assert len(cycles.cycles) == 1
        assert cycles.cycles[0].cycle_id == "test_cycle"

    def test_clear_state(self, state_manager):
        """Test clearing all state."""
        # Set some state
        state_manager.set_running(pid=12345)
        state_manager.add_cycle(
            CycleInfo(
                cycle_id="c1",
                timestamp="2024-01-01T12:00:00Z",
                action="test",
                state_before="s1",
                state_after="s2",
                success=True,
            )
        )

        # Clear it
        state_manager.clear_state()

        state = state_manager.get_state()
        assert state.pid is None
        assert state.is_running is False

        cycles = state_manager.get_recent_cycles()
        assert len(cycles.cycles) == 0

    def test_get_full_status(self, state_manager):
        """Test getting full status."""
        state_manager.set_running(pid=12345)
        state_manager.heartbeat()

        status = state_manager.get_full_status()
        assert "state" in status
        assert "is_alive" in status
        assert "is_process_running" in status
        assert "recent_cycles_count" in status
        assert status["is_alive"] is True
