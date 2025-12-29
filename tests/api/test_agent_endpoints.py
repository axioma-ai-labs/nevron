"""Tests for agent API endpoints."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.core.agent_commands import CommandQueue
from src.core.agent_state import CycleInfo, SharedStateManager, reset_state_manager


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
def app(state_manager, command_queue):
    """Create test application with mocked dependencies."""
    app = create_app()

    # Override dependencies
    from src.api.dependencies import get_commands, get_shared_state

    app.dependency_overrides[get_shared_state] = lambda: state_manager
    app.dependency_overrides[get_commands] = lambda: command_queue

    return app


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    """Create test client."""
    with TestClient(app) as client:
        yield client


class TestAgentStatusEndpoint:
    """Tests for GET /api/v1/agent/status endpoint."""

    def test_get_status_stopped(self, client, state_manager):
        """Test getting status when agent is stopped."""
        response = client.get("/api/v1/agent/status")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "stopped"
        assert data["data"]["is_running"] is False

    def test_get_status_running(self, client, state_manager):
        """Test getting status when agent is running."""
        # Set up running state with heartbeat
        state_manager.set_running(
            pid=12345,
            personality="test personality",
            goal="test goal",
        )
        state_manager.heartbeat()

        response = client.get("/api/v1/agent/status")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "running"
        assert data["data"]["is_running"] is True
        assert data["data"]["personality"] == "test personality"
        assert data["data"]["goal"] == "test goal"

    def test_get_status_paused(self, client, state_manager):
        """Test getting status when agent is paused."""
        state_manager.set_running(pid=12345)
        state_manager.update_state(status="paused")
        state_manager.heartbeat()

        response = client.get("/api/v1/agent/status")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["status"] == "paused"

    def test_status_shows_stopped_when_heartbeat_expired(self, client, state_manager):
        """Test that status shows stopped when heartbeat is expired."""
        state_manager.set_running(pid=12345)
        # Set old heartbeat
        old_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        state_manager.update_state(last_heartbeat=old_time.isoformat())

        response = client.get("/api/v1/agent/status")
        assert response.status_code == 200

        data = response.json()
        # Should show stopped because heartbeat expired
        assert data["data"]["status"] == "stopped"
        assert data["data"]["is_running"] is False

    def test_status_includes_mcp_info(self, client, state_manager):
        """Test that status includes MCP information."""
        state_manager.update_mcp_status(
            enabled=True,
            connected_servers=2,
            available_tools=10,
        )

        response = client.get("/api/v1/agent/status")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["mcp_enabled"] is True
        assert data["data"]["mcp_connected_servers"] == 2
        assert data["data"]["mcp_available_tools"] == 10


class TestAgentStartEndpoint:
    """Tests for POST /api/v1/agent/start endpoint."""

    def test_start_agent_process_not_running(self, client, state_manager):
        """Test start when agent process is not running."""
        # No heartbeat = process not alive
        response = client.post("/api/v1/agent/start")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert data["data"]["status"] == "not_running"
        assert "make run-agent" in data["message"].lower()

    def test_start_agent_already_running(self, client, state_manager):
        """Test start when agent is already running."""
        state_manager.set_running(pid=12345)
        state_manager.heartbeat()

        response = client.post("/api/v1/agent/start")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "already_running"

    def test_start_agent_sends_command(self, client, state_manager, command_queue):
        """Test that start sends START command when process is alive but stopped."""
        # Process is alive (has heartbeat) but not running cycles
        state_manager.heartbeat()
        state_manager.update_state(is_running=False, status="stopped")

        response = client.post("/api/v1/agent/start")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "starting"
        assert "command_id" in data["data"]

        # Verify command was queued
        commands = command_queue.get_pending_commands()
        assert len(commands) == 1
        assert commands[0].command_type == "start"


class TestAgentStopEndpoint:
    """Tests for POST /api/v1/agent/stop endpoint."""

    def test_stop_agent_already_stopped(self, client, state_manager):
        """Test stop when agent is already stopped."""
        response = client.post("/api/v1/agent/stop")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "already_stopped"

    def test_stop_agent_sends_command(self, client, state_manager, command_queue):
        """Test that stop sends STOP command."""
        state_manager.set_running(pid=12345)
        state_manager.heartbeat()

        response = client.post("/api/v1/agent/stop")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        # Either stopped or stop_requested depending on timing
        assert data["data"]["status"] in ["stopped", "stop_requested"]


class TestAgentPauseEndpoint:
    """Tests for POST /api/v1/agent/pause endpoint."""

    def test_pause_agent_not_running(self, client, state_manager):
        """Test pause when agent process is not running."""
        response = client.post("/api/v1/agent/pause")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert data["data"]["status"] == "not_running"

    def test_pause_agent_not_started(self, client, state_manager):
        """Test pause when agent process is running but cycles not started."""
        state_manager.heartbeat()
        state_manager.update_state(is_running=False, status="stopped")

        response = client.post("/api/v1/agent/pause")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "already_stopped"

    def test_pause_agent_already_paused(self, client, state_manager):
        """Test pause when agent is already paused."""
        state_manager.set_running(pid=12345)
        state_manager.update_state(status="paused")
        state_manager.heartbeat()

        response = client.post("/api/v1/agent/pause")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "already_paused"

    def test_pause_agent_sends_command(self, client, state_manager, command_queue):
        """Test that pause sends PAUSE command."""
        state_manager.set_running(pid=12345)
        state_manager.heartbeat()

        response = client.post("/api/v1/agent/pause")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "pausing"
        assert "command_id" in data["data"]

        # Verify command was queued
        commands = command_queue.get_pending_commands()
        assert len(commands) == 1
        assert commands[0].command_type == "pause"


class TestAgentResumeEndpoint:
    """Tests for POST /api/v1/agent/resume endpoint."""

    def test_resume_agent_not_running(self, client, state_manager):
        """Test resume when agent process is not running."""
        response = client.post("/api/v1/agent/resume")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is False
        assert data["data"]["status"] == "not_running"

    def test_resume_agent_not_paused(self, client, state_manager):
        """Test resume when agent is not paused."""
        state_manager.set_running(pid=12345)
        state_manager.heartbeat()

        response = client.post("/api/v1/agent/resume")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "not_paused"

    def test_resume_agent_sends_command(self, client, state_manager, command_queue):
        """Test that resume sends RESUME command."""
        state_manager.set_running(pid=12345)
        state_manager.update_state(status="paused")
        state_manager.heartbeat()

        response = client.post("/api/v1/agent/resume")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "resuming"
        assert "command_id" in data["data"]

        # Verify command was queued
        commands = command_queue.get_pending_commands()
        assert len(commands) == 1
        assert commands[0].command_type == "resume"


class TestAgentInfoEndpoint:
    """Tests for GET /api/v1/agent/info endpoint."""

    def test_get_info(self, client, state_manager):
        """Test getting agent info."""
        state_manager.update_state(
            personality="test personality",
            goal="test goal",
            agent_state="default",
            cycle_count=10,
            total_rewards=15.5,
        )

        response = client.get("/api/v1/agent/info")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["personality"] == "test personality"
        assert data["data"]["goal"] == "test goal"
        assert data["data"]["total_actions_executed"] == 10
        assert data["data"]["total_rewards"] == 15.5
        assert "available_actions" in data["data"]


class TestAgentContextEndpoint:
    """Tests for GET /api/v1/agent/context endpoint."""

    def test_get_context_empty(self, client, state_manager):
        """Test getting context with no history."""
        response = client.get("/api/v1/agent/context")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["actions_history"] == []

    def test_get_context_with_history(self, client, state_manager):
        """Test getting context with action history."""
        # Add some cycles
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

        response = client.get("/api/v1/agent/context")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["actions_history"]) == 1
        assert data["data"]["actions_history"][0]["action"] == "analyze_news"


class TestAgentActionEndpoint:
    """Tests for POST /api/v1/agent/action endpoint."""

    def test_action_agent_not_running(self, client, state_manager):
        """Test action when agent is not running."""
        response = client.post(
            "/api/v1/agent/action",
            json={"action": "idle"},
        )
        assert response.status_code == 503

    def test_action_invalid_action(self, client, state_manager):
        """Test action with invalid action name."""
        state_manager.set_running(pid=12345)
        state_manager.heartbeat()

        response = client.post(
            "/api/v1/agent/action",
            json={"action": "invalid_action_name"},
        )
        assert response.status_code == 400
        assert "Invalid action" in response.json()["detail"]


class TestAgentCyclesEndpoint:
    """Tests for GET /api/v1/agent/cycles endpoint."""

    def test_get_cycles_empty(self, client, state_manager):
        """Test getting cycles when empty."""
        response = client.get("/api/v1/agent/cycles")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["cycles"] == []
        assert data["data"]["count"] == 0

    def test_get_cycles_with_data(self, client, state_manager):
        """Test getting cycles with data."""
        # Add some cycles
        for i in range(3):
            cycle = CycleInfo(
                cycle_id=f"cycle_{i}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=f"action_{i}",
                state_before="default",
                state_after="default",
                success=True,
                reward=1.0,
            )
            state_manager.add_cycle(cycle)

        response = client.get("/api/v1/agent/cycles")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["count"] == 3

    def test_get_cycles_with_limit(self, client, state_manager):
        """Test getting cycles with limit parameter."""
        # Add 5 cycles
        for i in range(5):
            cycle = CycleInfo(
                cycle_id=f"cycle_{i}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                action=f"action_{i}",
                state_before="default",
                state_after="default",
                success=True,
                reward=1.0,
            )
            state_manager.add_cycle(cycle)

        response = client.get("/api/v1/agent/cycles?limit=2")
        assert response.status_code == 200

        data = response.json()
        assert data["data"]["count"] == 2


class TestAPIAuthentication:
    """Tests for API authentication."""

    def test_endpoints_work_without_api_key_when_not_configured(self, client):
        """Test that endpoints work when no API key is configured."""
        # By default, API_KEY is None so auth is disabled
        response = client.get("/api/v1/agent/status")
        assert response.status_code == 200

    def test_endpoints_require_api_key_when_configured(self, app, state_manager):
        """Test that endpoints require API key when configured."""
        from src.api.config import api_settings

        # Temporarily set API key
        original_key = api_settings.API_KEY
        try:
            api_settings.API_KEY = "test-secret-key"

            with TestClient(app) as client:
                # Without API key
                response = client.get("/api/v1/agent/status")
                assert response.status_code == 401

                # With correct API key
                response = client.get(
                    "/api/v1/agent/status",
                    headers={"X-API-Key": "test-secret-key"},
                )
                assert response.status_code == 200

                # With wrong API key
                response = client.get(
                    "/api/v1/agent/status",
                    headers={"X-API-Key": "wrong-key"},
                )
                assert response.status_code == 401
        finally:
            api_settings.API_KEY = original_key
