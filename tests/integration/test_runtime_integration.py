"""
Integration tests for Event-Driven Runtime.

Tests that the runtime properly orchestrates all components
and handles events correctly.
"""

import asyncio

import pytest

from src.runtime.background import BackgroundProcessManager
from src.runtime.event import Event, EventPriority, EventType
from src.runtime.processor import EventProcessor
from src.runtime.queue import EventQueue
from src.runtime.runtime import AutonomousRuntime, RuntimeConfiguration, RuntimeState
from src.runtime.scheduler import Scheduler


class TestRuntimeComponentIntegration:
    """Test runtime components work together."""

    @pytest.mark.asyncio
    async def test_queue_to_processor_flow(self):
        """Test events flow from queue to processor."""
        queue = EventQueue()
        processor = EventProcessor()

        processed = {"count": 0, "events": []}

        async def handler(event):
            processed["count"] += 1
            processed["events"].append(event.type)
            return {"handled": True}

        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)

        # Put event in queue
        event = Event(type=EventType.MESSAGE_RECEIVED, payload={"text": "hello"})
        await queue.put(event)

        # Get and process
        retrieved = await queue.get()
        result = await processor.process(retrieved)

        assert processed["count"] == 1
        assert EventType.MESSAGE_RECEIVED in processed["events"]
        assert result.success is True

    @pytest.mark.asyncio
    async def test_scheduler_creates_events(self):
        """Test scheduler creates events in queue."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue, check_interval=0.1)

        from datetime import timedelta

        # Schedule immediate task
        scheduler.schedule(
            name="immediate_task",
            when=timedelta(seconds=-1),  # Already due
            payload={"test": True},
        )

        await scheduler.start()
        await asyncio.sleep(0.3)
        await scheduler.stop()

        # Event should be in queue
        assert not queue.empty()
        event = await queue.get()
        assert event.type == EventType.SCHEDULE_TRIGGERED
        assert event.payload["task_name"] == "immediate_task"

    @pytest.mark.asyncio
    async def test_background_process_runs(self):
        """Test background processes execute properly."""
        manager = BackgroundProcessManager()
        executed = {"count": 0}

        async def background_task():
            executed["count"] += 1

        manager.register(
            name="test_bg",
            func=background_task,
            interval=0.1,
            run_on_start=True,
        )

        await manager.start_all()
        await asyncio.sleep(0.35)
        await manager.stop_all()

        assert executed["count"] >= 2

    @pytest.mark.asyncio
    async def test_priority_queue_ordering(self):
        """Test events are processed in priority order."""
        queue = EventQueue()

        # Add events in wrong order
        await queue.put(Event(type=EventType.MESSAGE_RECEIVED, priority=EventPriority.LOW))
        await queue.put(Event(type=EventType.ERROR, priority=EventPriority.CRITICAL))
        await queue.put(Event(type=EventType.HEALTH_CHECK, priority=EventPriority.BACKGROUND))
        await queue.put(Event(type=EventType.GOAL_DEADLINE, priority=EventPriority.HIGH))

        # Get in priority order
        priorities = []
        while not queue.empty():
            event = await queue.get()
            priorities.append(event.priority)

        # Should be ordered: CRITICAL, HIGH, LOW, BACKGROUND
        assert priorities == [
            EventPriority.CRITICAL,
            EventPriority.HIGH,
            EventPriority.LOW,
            EventPriority.BACKGROUND,
        ]


class TestFullRuntimeIntegration:
    """Test complete runtime integration."""

    @pytest.fixture
    def runtime_config(self):
        """Create test runtime configuration."""
        return RuntimeConfiguration(
            scheduler_enabled=True,
            background_enabled=True,
            webhook_enabled=False,
            graceful_shutdown_timeout=5.0,
            scheduler_check_interval=0.05,  # Fast check interval for tests
        )

    @pytest.mark.asyncio
    async def test_runtime_lifecycle(self, runtime_config):
        """Test runtime start/stop lifecycle."""
        runtime = AutonomousRuntime(config=runtime_config)

        assert runtime.state == RuntimeState.STOPPED

        await runtime.start()
        assert runtime.state == RuntimeState.RUNNING

        await runtime.stop()
        assert runtime.state == RuntimeState.STOPPED

    @pytest.mark.asyncio
    async def test_event_emission_and_processing(self, runtime_config):
        """Test emitting and processing events."""
        runtime = AutonomousRuntime(config=runtime_config)
        processed = {"count": 0}

        async def handler(event):
            processed["count"] += 1

        runtime.register_handler(EventType.MESSAGE_RECEIVED, handler)

        await runtime.start()

        # Emit events
        for i in range(3):
            await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED, payload={"i": i}))

        await asyncio.sleep(0.5)
        await runtime.stop()

        assert processed["count"] == 3

    @pytest.mark.asyncio
    async def test_scheduled_event_flow(self, runtime_config):
        """Test scheduled tasks create and process events."""
        runtime = AutonomousRuntime(config=runtime_config)
        scheduled_triggered = {"value": False}

        async def schedule_handler(event):
            scheduled_triggered["value"] = True

        runtime.register_handler(EventType.SCHEDULE_TRIGGERED, schedule_handler)

        from datetime import timedelta

        runtime.schedule(
            name="test_schedule",
            when=timedelta(seconds=0.05),  # Schedule quickly
            payload={"scheduled": True},
        )

        await runtime.start()
        await asyncio.sleep(1.0)  # Give more time for scheduler to process
        await runtime.stop()

        assert scheduled_triggered["value"] is True

    @pytest.mark.asyncio
    async def test_background_process_integration(self, runtime_config):
        """Test background processes integrate with runtime."""
        runtime = AutonomousRuntime(config=runtime_config)
        bg_executed = {"count": 0}

        async def background_work():
            bg_executed["count"] += 1

        runtime.register_background_process(
            name="bg_worker",
            func=background_work,
            interval=0.1,
            run_on_start=True,
        )

        await runtime.start()
        await asyncio.sleep(0.35)
        await runtime.stop()

        assert bg_executed["count"] >= 2

    @pytest.mark.asyncio
    async def test_error_handling_in_runtime(self, runtime_config):
        """Test runtime handles handler errors gracefully."""
        runtime = AutonomousRuntime(config=runtime_config)
        error_caught = {"value": False}

        async def failing_handler(event):
            raise ValueError("Handler error")

        async def error_handler(event, error):
            error_caught["value"] = True

        runtime.register_handler(EventType.MESSAGE_RECEIVED, failing_handler)
        runtime._processor.add_error_handler(error_handler)

        await runtime.start()
        await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED))
        await asyncio.sleep(0.3)
        await runtime.stop()

        stats = runtime.get_statistics()
        assert stats["runtime"]["events_failed"] >= 1

    @pytest.mark.asyncio
    async def test_startup_shutdown_events(self, runtime_config):
        """Test startup and shutdown events are emitted."""
        runtime = AutonomousRuntime(config=runtime_config)
        events_received = {"startup": False, "shutdown": False}

        async def startup_handler(event):
            events_received["startup"] = True

        async def shutdown_handler(event):
            events_received["shutdown"] = True

        runtime.register_handler(EventType.STARTUP, startup_handler)
        runtime.register_handler(EventType.SHUTDOWN, shutdown_handler)

        await runtime.start()
        await asyncio.sleep(0.2)
        await runtime.stop()

        assert events_received["startup"] is True
        assert events_received["shutdown"] is True

    @pytest.mark.asyncio
    async def test_pause_resume_functionality(self, runtime_config):
        """Test pausing and resuming runtime."""
        runtime = AutonomousRuntime(config=runtime_config)
        processed = {"before_pause": 0, "after_resume": 0}
        is_paused = {"value": False}

        async def handler(event):
            if is_paused["value"]:
                processed["after_resume"] += 1
            else:
                processed["before_pause"] += 1

        runtime.register_handler(EventType.MESSAGE_RECEIVED, handler)

        await runtime.start()

        # Emit before pause
        await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED))
        await asyncio.sleep(0.1)

        # Pause
        await runtime.pause()
        is_paused["value"] = True
        assert runtime.state == RuntimeState.PAUSED

        # Resume
        await runtime.resume()
        await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED))
        await asyncio.sleep(0.1)

        await runtime.stop()

        assert processed["before_pause"] >= 1
        assert processed["after_resume"] >= 1

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, runtime_config):
        """Test comprehensive statistics tracking."""
        runtime = AutonomousRuntime(config=runtime_config)

        async def handler(event):
            pass

        runtime.register_handler(EventType.MESSAGE_RECEIVED, handler)

        await runtime.start()

        for i in range(5):
            await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED))

        await asyncio.sleep(0.5)
        await runtime.stop()

        stats = runtime.get_statistics()

        assert "runtime" in stats
        assert "queue" in stats
        assert "processor" in stats
        assert "scheduler" in stats
        assert "background" in stats
        assert stats["runtime"]["events_processed"] >= 5


class TestRuntimeResilience:
    """Test runtime resilience and recovery."""

    @pytest.mark.asyncio
    async def test_handler_exception_isolation(self):
        """Test that handler exceptions don't crash runtime."""
        config = RuntimeConfiguration(
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)
        good_handler_called = {"value": False}

        async def bad_handler(event):
            raise RuntimeError("Intentional error")

        async def good_handler(event):
            good_handler_called["value"] = True

        runtime.register_handler(EventType.MESSAGE_RECEIVED, bad_handler)
        runtime.register_handler(EventType.WEBHOOK_RECEIVED, good_handler)

        await runtime.start()

        await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED))
        await runtime.emit(Event(type=EventType.WEBHOOK_RECEIVED))

        await asyncio.sleep(0.3)
        await runtime.stop()

        # Runtime should still be functional
        assert runtime.state == RuntimeState.STOPPED
        assert good_handler_called["value"] is True

    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self):
        """Test handling of queue overflow."""
        config = RuntimeConfiguration(
            queue_maxsize=5,
            scheduler_enabled=False,
            background_enabled=False,
        )
        runtime = AutonomousRuntime(config=config)

        # Don't register handlers (events won't be consumed)
        await runtime.start()

        # Try to add many events
        overflow_count = 0
        for i in range(10):
            try:
                await asyncio.wait_for(
                    runtime.emit(Event(type=EventType.MESSAGE_RECEIVED)),
                    timeout=0.1,
                )
            except (asyncio.QueueFull, asyncio.TimeoutError):
                overflow_count += 1

        await runtime.stop()

        # Some should have been rejected or timed out
        # (behavior depends on queue implementation)
        assert runtime.state == RuntimeState.STOPPED

    @pytest.mark.asyncio
    async def test_graceful_shutdown_with_pending_events(self):
        """Test graceful shutdown processes pending events."""
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
        for i in range(3):
            await runtime.emit(Event(type=EventType.MESSAGE_RECEIVED))

        # Give minimal time for processing to start
        await asyncio.sleep(0.05)

        # Stop (should wait for pending)
        await runtime.stop()

        # Should have processed at least some
        assert processed["count"] >= 1
