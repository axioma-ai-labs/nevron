"""Tests for EventQueue module."""

import asyncio

import pytest

from src.runtime.event import Event, EventPriority, EventType
from src.runtime.queue import BufferedEventQueue, EventQueue, PriorityBoostQueue


class TestEventQueue:
    """Tests for EventQueue class."""

    def test_queue_creation(self):
        """Test creating an event queue."""
        queue = EventQueue()
        assert queue.empty()
        assert queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_put_and_get(self):
        """Test putting and getting events."""
        queue = EventQueue()

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await queue.put(event)

        assert queue.qsize() == 1

        retrieved = await queue.get()
        assert retrieved == event
        queue.task_done()

    @pytest.mark.asyncio
    async def test_priority_ordering(self):
        """Test events are returned in priority order."""
        queue = EventQueue()

        # Add events in reverse priority order
        low = Event(type=EventType.SCHEDULE_TRIGGERED, priority=EventPriority.LOW)
        normal = Event(type=EventType.MESSAGE_RECEIVED, priority=EventPriority.NORMAL)
        high = Event(type=EventType.GOAL_DEADLINE, priority=EventPriority.HIGH)

        await queue.put(low)
        await queue.put(normal)
        await queue.put(high)

        # Should get them back in priority order
        first = await queue.get()
        assert first.priority == EventPriority.HIGH
        queue.task_done()

        second = await queue.get()
        assert second.priority == EventPriority.NORMAL
        queue.task_done()

        third = await queue.get()
        assert third.priority == EventPriority.LOW
        queue.task_done()

    @pytest.mark.asyncio
    async def test_put_nowait(self):
        """Test putting events without waiting."""
        queue = EventQueue()

        event = Event(type=EventType.MESSAGE_RECEIVED)
        queue.put_nowait(event)

        assert queue.qsize() == 1

    @pytest.mark.asyncio
    async def test_get_nowait(self):
        """Test getting events without waiting."""
        queue = EventQueue()

        # Empty queue should return None
        assert queue.get_nowait() is None

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await queue.put(event)

        retrieved = queue.get_nowait()
        assert retrieved == event

    @pytest.mark.asyncio
    async def test_skip_expired_events(self):
        """Test that expired events are skipped."""
        from datetime import datetime, timedelta, timezone

        queue = EventQueue()

        # Add expired event
        expired = Event(
            type=EventType.GOAL_DEADLINE,
            deadline=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        await queue.put(expired)

        # Add valid event
        valid = Event(type=EventType.MESSAGE_RECEIVED)
        await queue.put(valid)

        # Should skip expired and get valid
        retrieved = await queue.get(skip_expired=True)
        assert retrieved == valid

    @pytest.mark.asyncio
    async def test_pause_resume(self):
        """Test pausing and resuming queue."""
        queue = EventQueue()

        event = Event(type=EventType.MESSAGE_RECEIVED)
        await queue.put(event)

        # Pause queue
        queue.pause()
        assert queue.is_paused()

        # Try to get with timeout - should not return
        try:
            await asyncio.wait_for(queue.get(), timeout=0.1)
            assert False, "Should have timed out"
        except asyncio.TimeoutError:
            pass

        # Resume queue
        queue.resume()
        assert not queue.is_paused()

        # Now should be able to get
        retrieved = await queue.get()
        assert retrieved == event

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing the queue."""
        queue = EventQueue()

        for _ in range(5):
            await queue.put(Event(type=EventType.MESSAGE_RECEIVED))

        assert queue.qsize() == 5

        cleared = queue.clear()
        assert cleared == 5
        assert queue.empty()

    def test_get_statistics(self):
        """Test getting queue statistics."""
        queue = EventQueue()

        stats = queue.get_statistics()

        assert stats.total_enqueued == 0
        assert stats.current_size == 0

    @pytest.mark.asyncio
    async def test_statistics_update(self):
        """Test statistics are updated correctly."""
        queue = EventQueue()

        event = Event(type=EventType.MESSAGE_RECEIVED, priority=EventPriority.HIGH)
        await queue.put(event)

        stats = queue.get_statistics()
        assert stats.total_enqueued == 1
        assert stats.by_priority["HIGH"] == 1
        assert stats.by_type["message"] == 1

        await queue.get()
        queue.task_done()

        stats = queue.get_statistics()
        assert stats.total_dequeued == 1


class TestBufferedEventQueue:
    """Tests for BufferedEventQueue class."""

    @pytest.mark.asyncio
    async def test_buffered_queue(self):
        """Test buffered queue flushes on size."""
        queue = BufferedEventQueue(buffer_size=3)

        # Add 2 events - should stay buffered
        for _ in range(2):
            await queue.put_buffered(Event(type=EventType.MESSAGE_RECEIVED))

        assert queue.buffer_size() == 2
        assert queue.empty()  # Main queue still empty

        # Add 3rd event - should trigger flush
        await queue.put_buffered(Event(type=EventType.MESSAGE_RECEIVED))

        # After flush, buffer should be empty and main queue has events
        assert queue.buffer_size() == 0
        assert queue.qsize() == 3

    @pytest.mark.asyncio
    async def test_manual_flush(self):
        """Test manual buffer flush."""
        queue = BufferedEventQueue(buffer_size=10)

        await queue.put_buffered(Event(type=EventType.MESSAGE_RECEIVED))
        assert queue.buffer_size() == 1

        await queue.flush()
        assert queue.buffer_size() == 0
        assert queue.qsize() == 1


class TestPriorityBoostQueue:
    """Tests for PriorityBoostQueue class."""

    @pytest.mark.asyncio
    async def test_priority_boost(self):
        """Test that aging events get priority boost."""
        from datetime import datetime, timedelta, timezone

        queue = PriorityBoostQueue(boost_interval=10.0, max_boost=2)

        # Create old event with LOW priority
        old_event = Event(type=EventType.SCHEDULE_TRIGGERED, priority=EventPriority.LOW)
        old_event.created_at = datetime.now(timezone.utc) - timedelta(seconds=25)

        await queue.put(old_event)

        # Get event - should have boosted priority
        retrieved = await queue.get()

        # Should have been boosted by 2 levels (25 seconds / 10 second interval = 2 boosts)
        assert retrieved.priority.value < EventPriority.LOW.value
