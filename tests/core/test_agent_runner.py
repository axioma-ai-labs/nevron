"""Tests for agent runner lifecycle control."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agent_runner import AgentRunner
from src.core.agent_commands import CommandQueue, CommandStatus, CommandType
from src.core.agent_state import SharedStateManager, reset_state_manager


@pytest.fixture
def temp_dirs():
    """Create temporary directories for state and commands."""
    with tempfile.TemporaryDirectory() as state_dir:
        with tempfile.TemporaryDirectory() as cmd_dir:
            yield Path(state_dir), Path(cmd_dir)


@pytest.fixture
def state_manager(temp_dirs):
    """Create a SharedStateManager with a temporary directory."""
    state_dir, _ = temp_dirs
    reset_state_manager()
    manager = SharedStateManager(state_dir=state_dir)
    yield manager
    reset_state_manager()


@pytest.fixture
def command_queue(temp_dirs):
    """Create a CommandQueue with a temporary directory."""
    _, cmd_dir = temp_dirs
    from src.core.agent_commands import reset_command_queue

    reset_command_queue()
    queue = CommandQueue(command_dir=cmd_dir)
    yield queue
    reset_command_queue()


@pytest.fixture
def runner(state_manager, command_queue):
    """Create an AgentRunner with mocked dependencies."""
    runner = AgentRunner(
        state_manager=state_manager,
        command_queue=command_queue,
    )
    return runner


class TestAgentRunnerInitialization:
    """Tests for AgentRunner initialization."""

    def test_initial_state(self, runner):
        """Test that runner starts in correct initial state."""
        assert runner._process_running is False
        assert runner._agent_started is False
        assert runner._paused is False
        assert runner._shutdown_requested is False
        assert runner._agent is None

    def test_has_state_manager(self, runner, state_manager):
        """Test that runner has state manager."""
        assert runner.state_manager is state_manager

    def test_has_command_queue(self, runner, command_queue):
        """Test that runner has command queue."""
        assert runner.command_queue is command_queue


class TestAgentRunnerLifecycle:
    """Tests for agent lifecycle methods."""

    @pytest.mark.asyncio
    async def test_initialize(self, runner, state_manager):
        """Test initialize method."""
        with patch("src.agent_runner.Agent") as MockAgent:
            mock_agent = MagicMock()
            mock_agent.personality = "test personality"
            mock_agent.goal = "test goal"
            mock_agent._initialize_mcp = AsyncMock()
            mock_agent.get_mcp_status.return_value = {
                "enabled": False,
                "connected_servers": [],
                "available_tools": 0,
            }
            MockAgent.return_value = mock_agent

            with patch("src.agent_runner.log_settings"):
                await runner.initialize()

        assert runner._process_running is True
        assert runner._agent_started is False  # Waiting for START command
        assert runner._agent is mock_agent

        # Check state was updated
        state = state_manager.get_state()
        assert state.status == "stopped"  # Initially stopped, waiting for START
        assert state.is_running is False
        assert state.personality == "test personality"
        assert state.goal == "test goal"

    @pytest.mark.asyncio
    async def test_initialize_already_initialized(self, runner):
        """Test that initialize warns if already initialized."""
        runner._process_running = True

        with patch("src.agent_runner.logger") as mock_logger:
            await runner.initialize()
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_agent(self, runner, state_manager):
        """Test start_agent method."""
        # Setup: Initialize first
        runner._process_running = True
        runner._agent = MagicMock()
        runner._agent.personality = "test"
        runner._agent.goal = "test goal"

        await runner.start_agent()

        assert runner._agent_started is True
        assert runner._paused is False

        state = state_manager.get_state()
        assert state.status == "running"
        assert state.is_running is True

    @pytest.mark.asyncio
    async def test_start_agent_already_started(self, runner):
        """Test that start_agent warns if already started."""
        runner._agent_started = True

        with patch("src.agent_runner.logger") as mock_logger:
            await runner.start_agent()
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_agent(self, runner, state_manager):
        """Test stop_agent method."""
        # Setup: Start first
        runner._agent_started = True
        runner._paused = False

        await runner.stop_agent()

        assert runner._agent_started is False
        assert runner._paused is False

        state = state_manager.get_state()
        assert state.status == "stopped"
        assert state.is_running is False

    @pytest.mark.asyncio
    async def test_stop_agent_not_started(self, runner):
        """Test stop_agent when not started does nothing."""
        runner._agent_started = False

        await runner.stop_agent()
        # Should not raise
        assert runner._agent_started is False

    @pytest.mark.asyncio
    async def test_shutdown(self, runner, state_manager):
        """Test shutdown method."""
        # Setup
        runner._process_running = True
        runner._agent_started = True
        runner._agent = MagicMock()
        runner._agent._shutdown_mcp = AsyncMock()

        await runner.shutdown()

        assert runner._process_running is False
        assert runner._agent_started is False

        state = state_manager.get_state()
        assert state.status == "stopped"
        assert state.is_running is False

    @pytest.mark.asyncio
    async def test_shutdown_with_error(self, runner, state_manager):
        """Test shutdown with error message."""
        runner._process_running = True
        runner._agent = MagicMock()
        runner._agent._shutdown_mcp = AsyncMock()

        await runner.shutdown(error="Fatal error occurred")

        state = state_manager.get_state()
        assert state.status == "error"
        assert state.last_error == "Fatal error occurred"

    @pytest.mark.asyncio
    async def test_shutdown_not_running(self, runner):
        """Test shutdown when not running does nothing."""
        runner._process_running = False

        await runner.shutdown()
        # Should not raise


class TestAgentRunnerCommands:
    """Tests for command handling."""

    @pytest.mark.asyncio
    async def test_handle_start_command(self, runner):
        """Test handling START command."""
        runner._agent_started = False
        runner._process_running = True
        runner._agent = MagicMock()
        runner._agent.personality = "test"
        runner._agent.goal = "test"

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.START.value,
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)

        assert result["status"] == "started"
        assert runner._agent_started is True

    @pytest.mark.asyncio
    async def test_handle_start_command_already_running(self, runner):
        """Test START command when already running."""
        runner._agent_started = True

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.START.value,
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)
        assert result["status"] == "already_running"

    @pytest.mark.asyncio
    async def test_handle_stop_command(self, runner, state_manager):
        """Test handling STOP command."""
        runner._agent_started = True

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.STOP.value,
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)

        assert result["status"] == "stopped"
        assert runner._agent_started is False

    @pytest.mark.asyncio
    async def test_handle_stop_command_already_stopped(self, runner):
        """Test STOP command when already stopped."""
        runner._agent_started = False

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.STOP.value,
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)
        assert result["status"] == "already_stopped"

    @pytest.mark.asyncio
    async def test_handle_pause_command(self, runner, state_manager):
        """Test handling PAUSE command."""
        runner._agent_started = True
        runner._paused = False

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.PAUSE.value,
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)

        assert result["status"] == "paused"
        assert runner._paused is True

        state = state_manager.get_state()
        assert state.status == "paused"

    @pytest.mark.asyncio
    async def test_handle_pause_command_not_running(self, runner):
        """Test PAUSE command when agent not running."""
        runner._agent_started = False

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.PAUSE.value,
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)
        assert result["status"] == "error"
        assert "not running" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_resume_command(self, runner, state_manager):
        """Test handling RESUME command."""
        runner._agent_started = True
        runner._paused = True

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.RESUME.value,
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)

        assert result["status"] == "resumed"
        assert runner._paused is False

        state = state_manager.get_state()
        assert state.status == "running"

    @pytest.mark.asyncio
    async def test_handle_resume_command_not_running(self, runner):
        """Test RESUME command when agent not running."""
        runner._agent_started = False

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.RESUME.value,
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)
        assert result["status"] == "error"
        assert "not running" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_shutdown_command(self, runner):
        """Test handling SHUTDOWN command."""
        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.SHUTDOWN.value,
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)

        assert result["status"] == "shutdown_requested"
        assert runner._shutdown_requested is True

    @pytest.mark.asyncio
    async def test_handle_execute_action_command(self, runner):
        """Test handling EXECUTE_ACTION command."""
        runner._agent = MagicMock()
        runner._agent.execution_module.execute_action = AsyncMock(
            return_value=(True, "Action completed")
        )

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.EXECUTE_ACTION.value,
            created_at="2024-01-01T12:00:00Z",
            params={"action": "idle"},
        )

        result = await runner._handle_command(command)

        assert result["success"] is True
        assert result["action"] == "idle"

    @pytest.mark.asyncio
    async def test_handle_execute_action_no_agent(self, runner):
        """Test EXECUTE_ACTION when agent not initialized."""
        runner._agent = None

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.EXECUTE_ACTION.value,
            created_at="2024-01-01T12:00:00Z",
            params={"action": "idle"},
        )

        result = await runner._handle_command(command)
        assert result["success"] is False
        assert "not initialized" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_execute_action_no_action(self, runner):
        """Test EXECUTE_ACTION with no action specified."""
        runner._agent = MagicMock()

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.EXECUTE_ACTION.value,
            created_at="2024-01-01T12:00:00Z",
            params={},
        )

        result = await runner._handle_command(command)
        assert result["success"] is False
        assert "No action specified" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_execute_action_invalid_action(self, runner):
        """Test EXECUTE_ACTION with invalid action."""
        runner._agent = MagicMock()

        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.EXECUTE_ACTION.value,
            created_at="2024-01-01T12:00:00Z",
            params={"action": "invalid_action_name"},
        )

        result = await runner._handle_command(command)
        assert result["success"] is False
        assert "Unknown action" in result["error"]

    @pytest.mark.asyncio
    async def test_handle_reload_config_command(self, runner):
        """Test handling RELOAD_CONFIG command."""
        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.RELOAD_CONFIG.value,
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)
        assert result["status"] == "config_reloaded"

    @pytest.mark.asyncio
    async def test_handle_unknown_command(self, runner):
        """Test handling unknown command type."""
        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type="unknown_command",
            created_at="2024-01-01T12:00:00Z",
        )

        result = await runner._handle_command(command)
        assert "error" in result
        assert "Unknown command type" in result["error"]


class TestAgentRunnerStateTransitions:
    """Tests for state transitions."""

    @pytest.mark.asyncio
    async def test_stopped_to_running(self, runner, state_manager):
        """Test transition from stopped to running."""
        runner._process_running = True
        runner._agent = MagicMock()
        runner._agent.personality = "test"
        runner._agent.goal = "test"

        # Initially stopped
        assert runner._agent_started is False

        await runner.start_agent()

        assert runner._agent_started is True
        state = state_manager.get_state()
        assert state.status == "running"

    @pytest.mark.asyncio
    async def test_running_to_paused(self, runner, state_manager):
        """Test transition from running to paused."""
        runner._agent_started = True
        runner._paused = False

        # Simulate PAUSE command
        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.PAUSE.value,
            created_at="2024-01-01T12:00:00Z",
        )
        await runner._handle_command(command)

        assert runner._paused is True
        state = state_manager.get_state()
        assert state.status == "paused"

    @pytest.mark.asyncio
    async def test_paused_to_running(self, runner, state_manager):
        """Test transition from paused to running."""
        runner._agent_started = True
        runner._paused = True
        state_manager.update_state(status="paused")

        # Simulate RESUME command
        from src.core.agent_commands import AgentCommand

        command = AgentCommand(
            command_id="cmd_001",
            command_type=CommandType.RESUME.value,
            created_at="2024-01-01T12:00:00Z",
        )
        await runner._handle_command(command)

        assert runner._paused is False
        state = state_manager.get_state()
        assert state.status == "running"

    @pytest.mark.asyncio
    async def test_running_to_stopped(self, runner, state_manager):
        """Test transition from running to stopped."""
        runner._agent_started = True
        state_manager.update_state(status="running", is_running=True)

        await runner.stop_agent()

        assert runner._agent_started is False
        state = state_manager.get_state()
        assert state.status == "stopped"
        assert state.is_running is False


class TestAgentRunnerHeartbeat:
    """Tests for heartbeat functionality."""

    @pytest.mark.asyncio
    async def test_send_heartbeat(self, runner, state_manager):
        """Test that heartbeat updates state."""
        runner._last_heartbeat = 0.0
        runner._heartbeat_interval = 0.0  # Always send

        await runner._send_heartbeat()

        state = state_manager.get_state()
        assert state.last_heartbeat is not None

    @pytest.mark.asyncio
    async def test_heartbeat_interval(self, runner):
        """Test that heartbeat respects interval."""
        import time

        runner._last_heartbeat = time.time()  # Just sent
        runner._heartbeat_interval = 10.0  # 10 second interval

        # Mock the state manager to track calls
        runner.state_manager = MagicMock()

        await runner._send_heartbeat()

        # Should not have called heartbeat due to interval
        runner.state_manager.heartbeat.assert_not_called()
