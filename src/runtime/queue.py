"""Priority event queue for the event-driven runtime."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from loguru import logger

from src.runtime.event import Event, EventPriority


@dataclass
class QueueStatistics:
    """Statistics about the event queue."""

    total_enqueued: int = 0
    total_dequeued: int = 0
    total_expired: int = 0
    current_size: int = 0
    by_priority: Dict[str, int] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)


class EventQueue:
    """Priority queue for events.

    Events are processed in priority order (lower priority value = higher priority).
    Within the same priority, events are processed in FIFO order.
    """

    def __init__(self, maxsize: int = 0):
        """Initialize the event queue.

        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self._queue: asyncio.PriorityQueue[Event] = asyncio.PriorityQueue(maxsize=maxsize)
        self._statistics = QueueStatistics()
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        logger.debug(f"EventQueue initialized (maxsize={maxsize})")

    async def put(self, event: Event) -> None:
        """Add an event to the queue.

        Args:
            event: Event to add
        """
        await self._queue.put(event)
        self._update_enqueue_stats(event)
        logger.debug(f"Event enqueued: {event.type.value} (priority={event.priority.value})")

    def put_nowait(self, event: Event) -> None:
        """Add an event to the queue without waiting.

        Args:
            event: Event to add

        Raises:
            asyncio.QueueFull: If queue is full
        """
        self._queue.put_nowait(event)
        self._update_enqueue_stats(event)
        logger.debug(f"Event enqueued (nowait): {event.type.value}")

    async def get(self, skip_expired: bool = True) -> Event:
        """Get the next event from the queue.

        Blocks until an event is available and queue is not paused.

        Args:
            skip_expired: Whether to skip expired events

        Returns:
            Next event to process
        """
        while True:
            # Wait if paused
            await self._pause_event.wait()

            event = await self._queue.get()
            self._update_dequeue_stats(event)

            # Skip expired events if requested
            if skip_expired and event.is_expired():
                self._statistics.total_expired += 1
                logger.warning(f"Skipping expired event: {event.type.value}")
                self._queue.task_done()
                continue

            return event

    def get_nowait(self, skip_expired: bool = True) -> Optional[Event]:
        """Get the next event without waiting.

        Args:
            skip_expired: Whether to skip expired events

        Returns:
            Next event or None if queue is empty
        """
        try:
            event = self._queue.get_nowait()
            self._update_dequeue_stats(event)

            if skip_expired and event.is_expired():
                self._statistics.total_expired += 1
                logger.warning(f"Skipping expired event: {event.type.value}")
                self._queue.task_done()
                return None

            return event
        except asyncio.QueueEmpty:
            return None

    def task_done(self) -> None:
        """Mark the current task as done."""
        self._queue.task_done()

    async def join(self) -> None:
        """Wait until all tasks are done."""
        await self._queue.join()

    def pause(self) -> None:
        """Pause queue processing."""
        self._paused = True
        self._pause_event.clear()
        logger.info("Event queue paused")

    def resume(self) -> None:
        """Resume queue processing."""
        self._paused = False
        self._pause_event.set()
        logger.info("Event queue resumed")

    def is_paused(self) -> bool:
        """Check if queue is paused."""
        return self._paused

    def empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()

    def qsize(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()

    def clear(self) -> int:
        """Clear all events from the queue.

        Returns:
            Number of events cleared
        """
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break
        logger.info(f"Cleared {count} events from queue")
        return count

    def peek(self) -> Optional[Event]:
        """Peek at the next event without removing it.

        Note: This is not thread-safe and should only be used for debugging.

        Returns:
            Next event or None
        """
        # Access internal queue - this is implementation-specific
        if hasattr(self._queue, "_queue") and self._queue._queue:
            return self._queue._queue[0]
        return None

    def get_statistics(self) -> QueueStatistics:
        """Get queue statistics.

        Returns:
            Current statistics
        """
        self._statistics.current_size = self.qsize()
        return self._statistics

    def _update_enqueue_stats(self, event: Event) -> None:
        """Update statistics on enqueue."""
        self._statistics.total_enqueued += 1
        self._statistics.current_size = self.qsize()

        priority_key = event.priority.name
        self._statistics.by_priority[priority_key] = (
            self._statistics.by_priority.get(priority_key, 0) + 1
        )

        type_key = event.type.value
        self._statistics.by_type[type_key] = self._statistics.by_type.get(type_key, 0) + 1

    def _update_dequeue_stats(self, event: Event) -> None:
        """Update statistics on dequeue."""
        self._statistics.total_dequeued += 1
        self._statistics.current_size = self.qsize()


class BufferedEventQueue(EventQueue):
    """Event queue with buffering for batch processing.

    Collects events up to a buffer size or timeout before processing.
    """

    def __init__(
        self,
        maxsize: int = 0,
        buffer_size: int = 10,
        buffer_timeout: float = 1.0,
    ):
        """Initialize buffered queue.

        Args:
            maxsize: Maximum queue size
            buffer_size: Maximum events to buffer before flushing
            buffer_timeout: Maximum seconds to wait before flushing
        """
        super().__init__(maxsize=maxsize)
        self._buffer: List[Event] = []
        self._buffer_size = buffer_size
        self._buffer_timeout = buffer_timeout
        self._buffer_lock = asyncio.Lock()
        self._last_flush = datetime.now(timezone.utc)

    async def put_buffered(self, event: Event) -> None:
        """Add event to buffer, flush if needed.

        Args:
            event: Event to buffer
        """
        async with self._buffer_lock:
            self._buffer.append(event)

            # Check if we should flush
            should_flush = (
                len(self._buffer) >= self._buffer_size
                or self._seconds_since_flush() >= self._buffer_timeout
            )

            if should_flush:
                await self._flush_buffer()

    async def _flush_buffer(self) -> None:
        """Flush all buffered events to the main queue."""
        for event in self._buffer:
            await self.put(event)
        self._buffer.clear()
        self._last_flush = datetime.now(timezone.utc)
        logger.debug(f"Flushed {len(self._buffer)} events from buffer")

    def _seconds_since_flush(self) -> float:
        """Get seconds since last flush."""
        return (datetime.now(timezone.utc) - self._last_flush).total_seconds()

    async def flush(self) -> None:
        """Manually flush the buffer."""
        async with self._buffer_lock:
            await self._flush_buffer()

    def buffer_size(self) -> int:
        """Get current buffer size."""
        return len(self._buffer)


class PriorityBoostQueue(EventQueue):
    """Event queue that boosts priority of aging events.

    Prevents starvation of low-priority events by gradually
    increasing their priority as they age.
    """

    def __init__(
        self,
        maxsize: int = 0,
        boost_interval: float = 60.0,
        max_boost: int = 2,
    ):
        """Initialize priority boost queue.

        Args:
            maxsize: Maximum queue size
            boost_interval: Seconds before priority boost
            max_boost: Maximum number of priority levels to boost
        """
        super().__init__(maxsize=maxsize)
        self._boost_interval = boost_interval
        self._max_boost = max_boost

    async def get(self, skip_expired: bool = True) -> Event:
        """Get next event with priority boosting.

        Args:
            skip_expired: Whether to skip expired events

        Returns:
            Next event (potentially with boosted priority)
        """
        event = await super().get(skip_expired=skip_expired)

        # Calculate age
        age = (datetime.now(timezone.utc) - event.created_at).total_seconds()
        boost_levels = int(age / self._boost_interval)
        boost_levels = min(boost_levels, self._max_boost)

        # Apply boost if needed
        if boost_levels > 0:
            new_priority_value = max(0, event.priority.value - boost_levels)
            try:
                new_priority = EventPriority(new_priority_value)
                if new_priority != event.priority:
                    logger.debug(
                        f"Priority boost: {event.priority.name} -> {new_priority.name} "
                        f"for {event.type.value}"
                    )
                    event.priority = new_priority
            except ValueError:
                # Invalid priority value, use CRITICAL
                event.priority = EventPriority.CRITICAL

        return event
