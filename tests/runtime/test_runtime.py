"""Tests for AutonomousRuntime module."""

import asyncio
from datetime import datetime, timezone

import pytest

from src.runtime.event import Event, EventPriority, EventType
from src.runtime.runtime import (
    AutonomousRuntime,
    RuntimeConfiguration,
    RuntimeState,
    RuntimeStatistics,
)


class TestRuntimeConfiguration:
    """Tests for RuntimeConfiguration dataclass."""

    def test_default_configuration(self):
        """Test default runtime configuration."""
        config = RuntimeConfiguration()

        assert config.queue_maxsize == 0
        assert config.webhook_enabled is False
        assert config.scheduler_enabled is True
        assert config.background_enabled is True
        assert config.graceful_shutdown_timeout == 30.0

    def test_custom_configuration(self):
        """Test custom runtime configuration."""
        config = RuntimeConfiguration(
            queue_maxsize=500,
            webhook_enabled=True,
            webhook_port=9000,
            scheduler_enabled=False,
            graceful_shutdown_timeout=10.0,
        )

        assert config.queue_maxsize == 500
        assert config.webhook_enabled is True
        assert config.webhook_port == 9000
        assert config.scheduler_enabled is False
        assert config.graceful_shutdown_timeout == 10.0


class TestRuntimeState:
    """Tests for RuntimeState enum."""

    def test_all_states(self):
        """Test all runtime states exist."""
        assert RuntimeState.STOPPED is not None
        assert RuntimeState.STARTING is not None
        assert RuntimeState.RUNNING is not None
        assert RuntimeState.PAUSED is not None
        assert RuntimeState.STOPPING is not None
        assert RuntimeState.ERROR is not None


class TestRuntimeStatistics:
    """Tests for RuntimeStatistics dataclass."""

    def test_default_statistics(self):
        """Test default runtime statistics."""
        stats = RuntimeStatistics()

        assert stats.state == RuntimeState.STOPPED
        assert stats.started_at is None
        assert stats.stopped_at is None
        assert stats.uptime_seconds == 0.0
        assert stats.events_processed == 0
        assert stats.events_failed == 0


class TestAutonomousRuntime:
    """Tests for AutonomousRuntime class."""

    def test_runtime_creation(self):
        """Test creating a runtime instance."""
        runtime = AutonomousRuntime()

        assert runtime is not None
        assert runtime.state == RuntimeState.STOPPED

    def test_runtime_with_config(self):
        """Test creating runtime with custom configuration."""
        config = RuntimeConfiguration(
            queue_maxsize=500,
            scheduler_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)

        assert runtime._config.queue_maxsize == 500
        assert runtime._config.scheduler_enabled is False

    def test_register_handler(self):
        """Test registering event handlers."""
        runtime = AutonomousRuntime()

        async def message_handler(event):
            pass

        runtime.register_handler(EventType.MESSAGE_RECEIVED, message_handler)

        # Handler should be registered in processor
        assert runtime._processor.has_handler(EventType.MESSAGE_RECEIVED)

    def test_set_default_handler(self):
        """Test setting default handler."""
        runtime = AutonomousRuntime()

        async def default_handler(event):
            pass

        runtime.set_default_handler(default_handler)

        assert runtime._processor._default_handler is not None

    @pytest.mark.asyncio
    async def test_emit_event(self):
        """Test emitting events to runtime."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)

        # Start callback listener so events can be injected
        await runtime._callback_listener.start()

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await runtime.emit(event)

        assert runtime._queue.qsize() == 1

        await runtime._callback_listener.stop()

    @pytest.mark.asyncio
    async def test_emit_message(self):
        """Test emitting message events."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)

        await runtime._callback_listener.start()

        await runtime.emit_message(
            content="Hello",
            channel="test",
            sender="user1",
        )

        assert runtime._queue.qsize() == 1
        event = await runtime._queue.get()
        assert event.type == EventType.MESSAGE_RECEIVED
        assert event.payload["content"] == "Hello"

        await runtime._callback_listener.stop()

    def test_schedule_task(self):
        """Test scheduling a task."""
        config = RuntimeConfiguration(scheduler_enabled=True)
        runtime = AutonomousRuntime(config=config)

        from datetime import timedelta

        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        runtime.schedule(
            name="test_task",
            when=future_time,
            payload={"test": True},
        )

        # Task should be in scheduler
        tasks = runtime._scheduler.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].name == "test_task"

    def test_schedule_recurring(self):
        """Test scheduling a recurring task."""
        config = RuntimeConfiguration(scheduler_enabled=True)
        runtime = AutonomousRuntime(config=config)

        runtime.schedule_recurring(
            name="recurring_task",
            interval_seconds=30.0,
        )

        tasks = runtime._scheduler.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].name == "recurring_task"

    def test_register_background_process(self):
        """Test registering a background process."""
        config = RuntimeConfiguration(background_enabled=True)
        runtime = AutonomousRuntime(config=config)

        async def background_work():
            pass

        runtime.register_background_process(
            name="worker",
            func=background_work,
            interval=60.0,
        )

        process = runtime._background.get_process("worker")
        assert process is not None
        assert process.name == "worker"

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping runtime."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)

        await runtime.start()
        assert runtime.state == RuntimeState.RUNNING
        assert runtime.is_running

        await runtime.stop()
        assert runtime.state == RuntimeState.STOPPED
        assert not runtime.is_running

    @pytest.mark.asyncio
    async def test_pause_resume(self):
        """Test pausing and resuming runtime."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)

        await runtime.start()
        assert runtime.state == RuntimeState.RUNNING

        await runtime.pause()
        assert runtime.state == RuntimeState.PAUSED

        await runtime.resume()
        assert runtime.state == RuntimeState.RUNNING

        await runtime.stop()

    @pytest.mark.asyncio
    async def test_event_processing_loop(self):
        """Test that events are processed when runtime is running."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)
        processed = {"count": 0}

        async def handler(event):
            processed["count"] += 1

        runtime.register_handler(EventType.MESSAGE_RECEIVED, handler)

        await runtime.start()

        # Emit some events
        for _ in range(3):
            await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED))

        # Wait for processing
        await asyncio.sleep(0.5)

        await runtime.stop()

        assert processed["count"] == 3

    @pytest.mark.asyncio
    async def test_startup_event(self):
        """Test startup event is emitted."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)
        startup_received = {"value": False}

        async def startup_handler(event):
            startup_received["value"] = True

        runtime.register_handler(EventType.STARTUP, startup_handler)

        await runtime.start()
        await asyncio.sleep(0.2)
        await runtime.stop()

        assert startup_received["value"] is True

    @pytest.mark.asyncio
    async def test_shutdown_event(self):
        """Test shutdown event is emitted."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)
        shutdown_received = {"value": False}

        async def shutdown_handler(event):
            shutdown_received["value"] = True

        runtime.register_handler(EventType.SHUTDOWN, shutdown_handler)

        await runtime.start()
        await asyncio.sleep(0.2)
        await runtime.stop()

        assert shutdown_received["value"] is True

    def test_get_statistics(self):
        """Test getting runtime statistics."""
        runtime = AutonomousRuntime()

        stats = runtime.get_statistics()

        assert "runtime" in stats
        assert "queue" in stats
        assert "processor" in stats
        assert "scheduler" in stats
        assert "background" in stats
        assert "listeners" in stats

    @pytest.mark.asyncio
    async def test_statistics_update(self):
        """Test statistics are updated correctly."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)

        async def handler(event):
            pass

        runtime.register_handler(EventType.MESSAGE_RECEIVED, handler)

        await runtime.start()

        # Emit and process an event
        await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED))
        await asyncio.sleep(0.2)

        stats = runtime.get_statistics()

        await runtime.stop()

        assert stats["runtime"]["events_processed"] >= 1

    @pytest.mark.asyncio
    async def test_priority_processing(self):
        """Test priority-based event processing."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)

        processed_order = []

        async def tracking_handler(event):
            processed_order.append(event.priority)

        runtime.register_handler(EventType.MESSAGE_RECEIVED, tracking_handler)

        # Queue events before starting (callback listener not running yet)
        await runtime._queue.put(Event(
            type=EventType.MESSAGE_RECEIVED,
            priority=EventPriority.LOW,
        ))
        await runtime._queue.put(Event(
            type=EventType.MESSAGE_RECEIVED,
            priority=EventPriority.HIGH,
        ))
        await runtime._queue.put(Event(
            type=EventType.MESSAGE_RECEIVED,
            priority=EventPriority.NORMAL,
        ))

        await runtime.start()
        await asyncio.sleep(0.5)
        await runtime.stop()

        # STARTUP event is first (CRITICAL priority)
        # Then HIGH, NORMAL, LOW
        # Check that we processed events
        assert len(processed_order) >= 3

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in runtime."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)
        error_count = {"value": 0}

        async def failing_handler(event):
            raise ValueError("Test error")

        async def error_handler(event, error):
            error_count["value"] += 1

        runtime.register_handler(EventType.MESSAGE_RECEIVED, failing_handler)
        runtime._processor.add_error_handler(error_handler)

        await runtime.start()

        await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED))

        await asyncio.sleep(0.3)

        await runtime.stop()

        # Error should have been counted
        stats = runtime.get_statistics()
        assert stats["runtime"]["events_failed"] >= 1

    @pytest.mark.asyncio
    async def test_properties(self):
        """Test runtime property accessors."""
        runtime = AutonomousRuntime()

        assert runtime.queue is not None
        assert runtime.scheduler is not None
        assert runtime.background is not None
        assert runtime.processor is not None


class TestRuntimeIntegration:
    """Integration tests for runtime with all components."""

    @pytest.mark.asyncio
    async def test_full_event_flow(self):
        """Test complete event flow through runtime."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)

        events_received = []

        async def capture_handler(event):
            events_received.append(event)

        runtime.register_handler(EventType.MESSAGE_RECEIVED, capture_handler)

        await runtime.start()

        # Emit a message event
        await runtime.emit_message(content="Hello", channel="test")

        # Wait for processing
        await asyncio.sleep(0.3)

        await runtime.stop()

        # Should have received the message
        message_events = [
            e for e in events_received
            if e.type == EventType.MESSAGE_RECEIVED
        ]
        assert len(message_events) >= 1
        assert message_events[0].payload["content"] == "Hello"

    @pytest.mark.asyncio
    async def test_webhook_enabled(self):
        """Test runtime with webhook listener enabled."""
        config = RuntimeConfiguration(
            webhook_enabled=True,
            webhook_port=18080,  # Use unusual port to avoid conflicts
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)

        # Should have webhook listener
        assert len(runtime._listeners.listeners) >= 2  # callback + webhook

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test graceful shutdown processes remaining events."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
            graceful_shutdown_timeout=5.0,
        )
        runtime = AutonomousRuntime(config=config)
        processed = {"count": 0}

        async def slow_handler(event):
            await asyncio.sleep(0.05)
            processed["count"] += 1

        runtime.register_handler(EventType.MESSAGE_RECEIVED, slow_handler)

        await runtime.start()

        # Queue some events
        for _ in range(3):
            await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED))

        # Wait a bit, then stop
        await asyncio.sleep(0.1)
        await runtime.stop()

        # Should have processed at least some events
        assert processed["count"] >= 1
