"""Tests for BackgroundProcessManager module."""

import asyncio

import pytest

from src.runtime.background import BackgroundProcess, BackgroundProcessManager, ProcessState


class TestBackgroundProcess:
    """Tests for BackgroundProcess dataclass."""

    def test_process_creation(self):
        """Test creating a background process."""

        async def dummy():
            pass

        process = BackgroundProcess(
            name="test_process",
            func=dummy,
            interval=60.0,
        )

        assert process.name == "test_process"
        assert process.interval == 60.0
        assert process.enabled is True
        assert process.state == ProcessState.STOPPED

    def test_to_dict(self):
        """Test converting process to dict."""

        async def dummy():
            pass

        process = BackgroundProcess(
            name="test",
            func=dummy,
            interval=30.0,
            enabled=False,
        )

        data = process.to_dict()

        assert data["name"] == "test"
        assert data["interval"] == 30.0
        assert data["enabled"] is False
        assert data["state"] == "stopped"


class TestBackgroundProcessManager:
    """Tests for BackgroundProcessManager class."""

    def test_manager_creation(self):
        """Test creating a process manager."""
        manager = BackgroundProcessManager()
        assert manager is not None
        assert not manager.is_running

    def test_register_process(self):
        """Test registering a process."""
        manager = BackgroundProcessManager()

        async def my_process():
            pass

        process = manager.register(
            name="my_process",
            func=my_process,
            interval=60.0,
        )

        assert process.name == "my_process"
        assert manager.get_process("my_process") is not None

    def test_unregister_process(self):
        """Test unregistering a process."""
        manager = BackgroundProcessManager()

        async def process():
            pass

        manager.register("to_remove", process, 60.0)

        assert manager.unregister("to_remove")
        assert manager.get_process("to_remove") is None
        assert not manager.unregister("nonexistent")

    def test_enable_disable(self):
        """Test enabling and disabling processes."""
        manager = BackgroundProcessManager()

        async def process():
            pass

        manager.register("toggleable", process, 60.0)

        p = manager.get_process("toggleable")
        assert p is not None and p.enabled

        manager.disable("toggleable")
        p_disabled = manager.get_process("toggleable")
        assert p_disabled is not None and not p_disabled.enabled

        manager.enable("toggleable")
        p_enabled = manager.get_process("toggleable")
        assert p_enabled is not None and p_enabled.enabled

    def test_list_processes(self):
        """Test listing processes."""
        manager = BackgroundProcessManager()

        async def p1():
            pass

        async def p2():
            pass

        manager.register("process1", p1, 60.0)
        manager.register("process2", p2, 120.0)

        processes = manager.list_processes()
        assert len(processes) == 2

    @pytest.mark.asyncio
    async def test_start_stop_all(self):
        """Test starting and stopping all processes."""
        manager = BackgroundProcessManager()
        counter = {"value": 0}

        async def increment():
            counter["value"] += 1

        manager.register("counter", increment, 0.1, run_on_start=True)

        await manager.start_all()
        assert manager.is_running

        # Wait for a few iterations
        await asyncio.sleep(0.35)

        await manager.stop_all()
        assert not manager.is_running

        # Should have run multiple times
        assert counter["value"] >= 2

    @pytest.mark.asyncio
    async def test_start_stop_single(self):
        """Test starting and stopping a single process."""
        manager = BackgroundProcessManager()
        counter = {"value": 0}

        async def increment():
            counter["value"] += 1

        manager.register("counter", increment, 0.1, run_on_start=True)

        # Use start_all to properly set manager._running flag
        # (start() for single process doesn't set this flag, which is needed for loop)
        await manager.start_all()
        process = manager.get_process("counter")
        assert process is not None and process.state == ProcessState.RUNNING

        await asyncio.sleep(0.25)

        # Stop single process
        await manager.stop("counter")
        process_after = manager.get_process("counter")
        assert process_after is not None and process_after.state == ProcessState.STOPPED

        assert counter["value"] >= 1

    @pytest.mark.asyncio
    async def test_process_error_handling(self):
        """Test that process handles errors gracefully."""
        manager = BackgroundProcessManager()

        async def failing_process():
            raise ValueError("Test error")

        # Use run_on_start=True to trigger immediate execution
        # Need: 1 run on start + 2 more runs after intervals to hit max_errors=3
        # With 0.05s interval, need to wait at least 0.05 * 2 = 0.1s after first run
        manager.register("failing", failing_process, 0.05, max_errors=3, run_on_start=True)

        # Use start_all to properly set manager._running flag
        # (start() for single process doesn't set this flag, which is needed for loop)
        await manager.start_all()
        process = manager.get_process("failing")

        # Wait for errors to accumulate:
        # - 1st error: immediate (run_on_start)
        # - 2nd error: after 0.05s
        # - 3rd error: after 0.10s
        # Add buffer time
        await asyncio.sleep(0.5)

        # Should have stopped due to too many errors
        assert process is not None and process.state == ProcessState.ERROR
        assert process.statistics is not None and process.statistics.errors >= 3

        await manager.stop_all()

    @pytest.mark.asyncio
    async def test_run_on_start(self):
        """Test run_on_start option."""
        manager = BackgroundProcessManager()
        ran = {"value": False}

        async def immediate():
            ran["value"] = True

        manager.register("immediate", immediate, 60.0, run_on_start=True)

        await manager.start_all()
        await asyncio.sleep(0.1)
        await manager.stop_all()

        assert ran["value"]

    def test_get_statistics(self):
        """Test getting statistics."""
        manager = BackgroundProcessManager()

        async def process():
            pass

        manager.register("test", process, 60.0)

        stats = manager.get_statistics()

        assert "test" in stats
        assert stats["test"]["interval"] == 60.0

    @pytest.mark.asyncio
    async def test_process_statistics_update(self):
        """Test that process statistics are updated."""
        manager = BackgroundProcessManager()

        async def process():
            pass

        manager.register("stats_test", process, 0.1, run_on_start=True)

        await manager.start_all()
        await asyncio.sleep(0.35)
        await manager.stop_all()

        p = manager.get_process("stats_test")
        assert p is not None
        assert p.statistics is not None
        assert p.statistics.iterations >= 2
        assert p.statistics.total_run_time > 0
        assert p.statistics.started_at is not None
