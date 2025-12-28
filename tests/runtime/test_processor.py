"""Tests for EventProcessor module."""


import pytest

from src.runtime.event import Event, EventType
from src.runtime.processor import (
    BatchEventProcessor,
    EventProcessor,
    ProcessingResult,
    ProcessorStatistics,
)


class TestProcessingResult:
    """Tests for ProcessingResult dataclass."""

    def test_result_creation(self):
        """Test creating a processing result."""
        event = Event(type=EventType.MESSAGE_RECEIVED)
        result = ProcessingResult(
            success=True,
            event=event,
            handler_name="test_handler",
        )

        assert result.success is True
        assert result.handler_name == "test_handler"
        assert result.error is None
        assert result.result is None

    def test_result_with_error(self):
        """Test processing result with error."""
        event = Event(type=EventType.MESSAGE_RECEIVED)
        result = ProcessingResult(
            success=False,
            event=event,
            handler_name="failing_handler",
            error="Something went wrong",
        )

        assert result.success is False
        assert result.error == "Something went wrong"

    def test_result_with_data(self):
        """Test processing result with return data."""
        event = Event(type=EventType.MESSAGE_RECEIVED)
        result = ProcessingResult(
            success=True,
            event=event,
            handler_name="data_handler",
            result={"count": 10},
        )

        assert result.result["count"] == 10


class TestEventProcessor:
    """Tests for EventProcessor class."""

    def test_processor_creation(self):
        """Test creating an event processor."""
        processor = EventProcessor()
        assert processor is not None

    def test_register_handler(self):
        """Test registering event handlers."""
        processor = EventProcessor()

        async def message_handler(event):
            return {"processed": True}

        processor.register_handler(EventType.MESSAGE_RECEIVED, message_handler)

        assert processor.has_handler(EventType.MESSAGE_RECEIVED)

    def test_register_multiple_handlers(self):
        """Test registering multiple handlers for same event type."""
        processor = EventProcessor()

        async def handler1(event):
            pass

        async def handler2(event):
            pass

        processor.register_handler(EventType.MESSAGE_RECEIVED, handler1)
        processor.register_handler(EventType.MESSAGE_RECEIVED, handler2)

        assert processor.has_handler(EventType.MESSAGE_RECEIVED)

    def test_unregister_handler(self):
        """Test unregistering handlers."""
        processor = EventProcessor()

        async def handler(event):
            pass

        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)
        result = processor.unregister_handler(EventType.MESSAGE_RECEIVED, handler)

        assert result is True
        assert not processor.has_handler(EventType.MESSAGE_RECEIVED)

    @pytest.mark.asyncio
    async def test_process_event(self):
        """Test processing an event."""
        processor = EventProcessor()
        processed = {"value": False}

        async def handler(event):
            processed["value"] = True
            return {"status": "ok"}

        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)

        event = Event(type=EventType.MESSAGE_RECEIVED)
        result = await processor.process(event)

        assert processed["value"] is True
        assert result.success is True

    @pytest.mark.asyncio
    async def test_process_with_no_handler(self):
        """Test processing event with no registered handler."""
        processor = EventProcessor()

        event = Event(type=EventType.MESSAGE_RECEIVED)
        result = await processor.process(event)

        # Should succeed but with no result
        assert result.success is True
        assert result.result is None

    @pytest.mark.asyncio
    async def test_process_with_error(self):
        """Test processing event when handler raises error."""
        processor = EventProcessor()

        async def failing_handler(event):
            raise ValueError("Handler error")

        processor.register_handler(EventType.MESSAGE_RECEIVED, failing_handler)

        event = Event(type=EventType.MESSAGE_RECEIVED)
        result = await processor.process(event)

        assert result.success is False
        assert "Handler error" in result.error

    @pytest.mark.asyncio
    async def test_middleware(self):
        """Test middleware execution."""
        processor = EventProcessor()
        middleware_called = {"value": False}

        async def middleware(event):
            middleware_called["value"] = True
            return event

        async def handler(event):
            return {"processed": True}

        processor.add_middleware(middleware)
        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await processor.process(event)

        assert middleware_called["value"] is True

    @pytest.mark.asyncio
    async def test_middleware_can_modify_event(self):
        """Test middleware can modify event before processing."""
        processor = EventProcessor()

        async def enriching_middleware(event):
            event.payload["enriched"] = True
            return event

        async def handler(event):
            return {"was_enriched": event.payload.get("enriched", False)}

        processor.add_middleware(enriching_middleware)
        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)

        event = Event(type=EventType.MESSAGE_RECEIVED, payload={})
        result = await processor.process(event)

        assert result.result["was_enriched"] is True

    @pytest.mark.asyncio
    async def test_middleware_skip_event(self):
        """Test middleware can skip an event."""
        processor = EventProcessor()

        async def skip_middleware(event):
            return None  # Skip the event

        async def handler(event):
            return {"processed": True}

        processor.add_middleware(skip_middleware)
        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)

        event = Event(type=EventType.MESSAGE_RECEIVED)
        result = await processor.process(event)

        # Event was skipped by middleware
        assert result.success is True
        assert result.handler_name == "middleware_skip"

    @pytest.mark.asyncio
    async def test_pre_hook(self):
        """Test pre-processing hook."""
        processor = EventProcessor()
        hook_called = {"value": False}

        async def pre_hook(event):
            hook_called["value"] = True

        async def handler(event):
            pass

        processor.add_pre_hook(pre_hook)
        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await processor.process(event)

        assert hook_called["value"] is True

    @pytest.mark.asyncio
    async def test_post_hook(self):
        """Test post-processing hook."""
        processor = EventProcessor()
        hook_called = {"value": False}

        async def post_hook(result):
            hook_called["value"] = True

        async def handler(event):
            pass

        processor.add_post_hook(post_hook)
        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await processor.process(event)

        assert hook_called["value"] is True

    @pytest.mark.asyncio
    async def test_error_handler(self):
        """Test custom error handler."""
        processor = EventProcessor()
        error_handled = {"value": False}

        async def error_handler(event, error):
            error_handled["value"] = True

        async def failing_handler(event):
            raise ValueError("Test error")

        processor.add_error_handler(error_handler)
        processor.register_handler(EventType.MESSAGE_RECEIVED, failing_handler)

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await processor.process(event)

        assert error_handled["value"] is True

    def test_get_statistics(self):
        """Test getting processor statistics."""
        processor = EventProcessor()

        stats = processor.get_statistics()

        assert stats.events_processed == 0
        assert stats.events_succeeded == 0
        assert stats.events_failed == 0

    @pytest.mark.asyncio
    async def test_statistics_update(self):
        """Test statistics are updated correctly."""
        processor = EventProcessor()

        async def handler(event):
            return {"ok": True}

        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await processor.process(event)

        stats = processor.get_statistics()
        assert stats.events_processed == 1
        assert stats.events_succeeded == 1

    @pytest.mark.asyncio
    async def test_statistics_on_failure(self):
        """Test statistics track failures."""
        processor = EventProcessor()

        async def failing_handler(event):
            raise ValueError("Error")

        processor.register_handler(EventType.MESSAGE_RECEIVED, failing_handler)

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await processor.process(event)

        stats = processor.get_statistics()
        assert stats.events_processed == 1
        assert stats.events_failed == 1

    def test_clear_statistics(self):
        """Test clearing statistics."""
        processor = EventProcessor()

        # Process some events to create stats
        processor._statistics.events_processed = 10

        processor.clear_statistics()

        stats = processor.get_statistics()
        assert stats.events_processed == 0


class TestBatchEventProcessor:
    """Tests for BatchEventProcessor class."""

    def test_batch_processor_creation(self):
        """Test creating a batch processor."""
        processor = EventProcessor()
        batch = BatchEventProcessor(processor, batch_size=5)
        assert batch is not None
        assert batch._batch_size == 5

    @pytest.mark.asyncio
    async def test_batch_add(self):
        """Test adding events to batch."""
        processor = EventProcessor()
        batch = BatchEventProcessor(processor, batch_size=5)

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await batch.add(event)

        assert batch.batch_size() == 1

    @pytest.mark.asyncio
    async def test_batch_flush(self):
        """Test flushing batch."""
        processor = EventProcessor()
        processed = {"count": 0}

        async def handler(event):
            processed["count"] += 1

        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)

        batch = BatchEventProcessor(processor, batch_size=10)

        for _ in range(3):
            await batch.add(Event(type=EventType.MESSAGE_RECEIVED))

        results = await batch.flush()

        assert processed["count"] == 3
        assert len(results) == 3
        assert batch.batch_size() == 0

    @pytest.mark.asyncio
    async def test_batch_auto_flush_on_size(self):
        """Test batch auto-flushes when size reached."""
        processor = EventProcessor()
        processed = {"count": 0}

        async def handler(event):
            processed["count"] += 1

        processor.register_handler(EventType.MESSAGE_RECEIVED, handler)

        batch = BatchEventProcessor(processor, batch_size=3)

        # Add events up to batch size
        for _ in range(3):
            await batch.add(Event(type=EventType.MESSAGE_RECEIVED))

        # Should have auto-flushed
        assert processed["count"] == 3
        assert batch.batch_size() == 0


class TestProcessorStatistics:
    """Tests for ProcessorStatistics dataclass."""

    def test_default_statistics(self):
        """Test default statistics values."""
        stats = ProcessorStatistics()

        assert stats.events_processed == 0
        assert stats.events_succeeded == 0
        assert stats.events_failed == 0
        assert stats.events_skipped == 0
        assert stats.total_processing_time == 0.0
        assert stats.by_type == {}
        assert stats.by_handler == {}
