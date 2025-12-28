"""Event processor for the event-driven runtime."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

from loguru import logger

from src.runtime.event import Event, EventType


@dataclass
class ProcessingResult:
    """Result of processing an event."""

    success: bool
    event: Event
    result: Optional[Any] = None
    error: Optional[str] = None
    processing_time: float = 0.0
    handler_name: Optional[str] = None


@dataclass
class ProcessorStatistics:
    """Statistics for the event processor."""

    events_processed: int = 0
    events_succeeded: int = 0
    events_failed: int = 0
    events_skipped: int = 0
    total_processing_time: float = 0.0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_handler: Dict[str, int] = field(default_factory=dict)


EventHandler = Callable[[Event], Coroutine[Any, Any, Any]]


class EventProcessor:
    """Processes events from the event queue.

    Routes events to appropriate handlers based on event type.
    Supports middleware, pre/post hooks, and error handling.
    """

    def __init__(self):
        """Initialize event processor."""
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        self._default_handler: Optional[EventHandler] = None
        self._middleware: List[Callable[[Event], Coroutine[Any, Any, Optional[Event]]]] = []
        self._pre_hooks: List[Callable[[Event], Coroutine[Any, Any, None]]] = []
        self._post_hooks: List[Callable[[ProcessingResult], Coroutine[Any, Any, None]]] = []
        self._error_handlers: List[Callable[[Event, Exception], Coroutine[Any, Any, None]]] = []
        self._statistics = ProcessorStatistics()
        logger.debug("EventProcessor initialized")

    def register_handler(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        """Register a handler for an event type.

        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Registered handler for {event_type.value}")

    def unregister_handler(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> bool:
        """Unregister a handler.

        Args:
            event_type: Event type
            handler: Handler to remove

        Returns:
            True if handler was found and removed
        """
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
            return True
        return False

    def set_default_handler(self, handler: EventHandler) -> None:
        """Set the default handler for unhandled events.

        Args:
            handler: Default handler function
        """
        self._default_handler = handler

    def add_middleware(
        self,
        middleware: Callable[[Event], Coroutine[Any, Any, Optional[Event]]],
    ) -> None:
        """Add middleware that can modify or filter events.

        Middleware can:
        - Modify the event and return it
        - Return None to skip the event
        - Raise an exception to stop processing

        Args:
            middleware: Middleware function
        """
        self._middleware.append(middleware)

    def add_pre_hook(
        self,
        hook: Callable[[Event], Coroutine[Any, Any, None]],
    ) -> None:
        """Add a hook that runs before event processing.

        Args:
            hook: Pre-processing hook
        """
        self._pre_hooks.append(hook)

    def add_post_hook(
        self,
        hook: Callable[[ProcessingResult], Coroutine[Any, Any, None]],
    ) -> None:
        """Add a hook that runs after event processing.

        Args:
            hook: Post-processing hook
        """
        self._post_hooks.append(hook)

    def add_error_handler(
        self,
        handler: Callable[[Event, Exception], Coroutine[Any, Any, None]],
    ) -> None:
        """Add an error handler.

        Args:
            handler: Error handler function
        """
        self._error_handlers.append(handler)

    async def process(self, event: Event) -> ProcessingResult:
        """Process an event.

        Args:
            event: Event to process

        Returns:
            Processing result
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Run middleware
            processed_event = await self._run_middleware(event)
            if processed_event is None:
                self._statistics.events_skipped += 1
                return ProcessingResult(
                    success=True,
                    event=event,
                    handler_name="middleware_skip",
                )
            event = processed_event

            # Run pre-hooks
            await self._run_pre_hooks(event)

            # Find and run handlers
            result = await self._run_handlers(event)

            # Calculate processing time
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()

            # Create result
            processing_result = ProcessingResult(
                success=True,
                event=event,
                result=result,
                processing_time=processing_time,
                handler_name=self._get_handler_name(event.type),
            )

            # Update statistics
            self._update_statistics(event, True, processing_time)

            # Run post-hooks
            await self._run_post_hooks(processing_result)

            return processing_result

        except Exception as e:
            end_time = datetime.now(timezone.utc)
            processing_time = (end_time - start_time).total_seconds()

            # Run error handlers
            await self._run_error_handlers(event, e)

            # Update statistics
            self._update_statistics(event, False, processing_time)

            return ProcessingResult(
                success=False,
                event=event,
                error=str(e),
                processing_time=processing_time,
            )

    async def _run_middleware(self, event: Event) -> Optional[Event]:
        """Run all middleware on the event.

        Args:
            event: Event to process

        Returns:
            Processed event or None to skip
        """
        current_event = event
        for middleware in self._middleware:
            try:
                result = await middleware(current_event)
                if result is None:
                    logger.debug(f"Event skipped by middleware: {event.type.value}")
                    return None
                current_event = result
            except Exception as e:
                logger.error(f"Middleware error: {e}")
                raise
        return current_event

    async def _run_pre_hooks(self, event: Event) -> None:
        """Run all pre-processing hooks.

        Args:
            event: Event being processed
        """
        for hook in self._pre_hooks:
            try:
                await hook(event)
            except Exception as e:
                logger.error(f"Pre-hook error: {e}")

    async def _run_post_hooks(self, result: ProcessingResult) -> None:
        """Run all post-processing hooks.

        Args:
            result: Processing result
        """
        for hook in self._post_hooks:
            try:
                await hook(result)
            except Exception as e:
                logger.error(f"Post-hook error: {e}")

    async def _run_error_handlers(self, event: Event, error: Exception) -> None:
        """Run all error handlers.

        Args:
            event: Event that caused error
            error: The exception
        """
        for handler in self._error_handlers:
            try:
                await handler(event, error)
            except Exception as e:
                logger.error(f"Error handler error: {e}")

    async def _run_handlers(self, event: Event) -> Any:
        """Run handlers for an event.

        Args:
            event: Event to handle

        Returns:
            Result from last handler
        """
        handlers = self._handlers.get(event.type, [])

        if not handlers:
            if self._default_handler:
                logger.debug(f"Using default handler for {event.type.value}")
                return await self._default_handler(event)
            else:
                logger.warning(f"No handler for event type: {event.type.value}")
                return None

        # Run all handlers for this event type
        result = None
        for handler in handlers:
            try:
                result = await handler(event)
            except Exception as e:
                logger.error(f"Handler error for {event.type.value}: {e}")
                raise

        return result

    def _get_handler_name(self, event_type: EventType) -> str:
        """Get handler name for statistics.

        Args:
            event_type: Event type

        Returns:
            Handler name
        """
        handlers = self._handlers.get(event_type, [])
        if handlers:
            return handlers[0].__name__
        elif self._default_handler:
            return "default"
        return "none"

    def _update_statistics(
        self,
        event: Event,
        success: bool,
        processing_time: float,
    ) -> None:
        """Update processing statistics.

        Args:
            event: Processed event
            success: Whether processing succeeded
            processing_time: Time taken to process
        """
        self._statistics.events_processed += 1
        self._statistics.total_processing_time += processing_time

        if success:
            self._statistics.events_succeeded += 1
        else:
            self._statistics.events_failed += 1

        # By type
        type_key = event.type.value
        self._statistics.by_type[type_key] = self._statistics.by_type.get(type_key, 0) + 1

        # By handler
        handler_name = self._get_handler_name(event.type)
        self._statistics.by_handler[handler_name] = (
            self._statistics.by_handler.get(handler_name, 0) + 1
        )

    def get_statistics(self) -> ProcessorStatistics:
        """Get processor statistics.

        Returns:
            Current statistics
        """
        return self._statistics

    def clear_statistics(self) -> None:
        """Clear processing statistics."""
        self._statistics = ProcessorStatistics()

    def has_handler(self, event_type: EventType) -> bool:
        """Check if a handler exists for an event type.

        Args:
            event_type: Event type to check

        Returns:
            True if handler exists
        """
        return event_type in self._handlers and len(self._handlers[event_type]) > 0


class BatchEventProcessor:
    """Process events in batches for efficiency."""

    def __init__(
        self,
        processor: EventProcessor,
        batch_size: int = 10,
        batch_timeout: float = 1.0,
    ):
        """Initialize batch processor.

        Args:
            processor: Underlying event processor
            batch_size: Maximum batch size
            batch_timeout: Maximum time to wait for batch
        """
        self._processor = processor
        self._batch_size = batch_size
        self._batch_timeout = batch_timeout
        self._batch: List[Event] = []
        self._batch_lock = asyncio.Lock()
        self._last_process = datetime.now(timezone.utc)

    async def add(self, event: Event) -> None:
        """Add an event to the batch.

        Args:
            event: Event to add
        """
        async with self._batch_lock:
            self._batch.append(event)

            if len(self._batch) >= self._batch_size:
                await self._process_batch()

    async def flush(self) -> List[ProcessingResult]:
        """Process all pending events.

        Returns:
            List of processing results
        """
        async with self._batch_lock:
            return await self._process_batch()

    async def _process_batch(self) -> List[ProcessingResult]:
        """Process the current batch.

        Returns:
            List of processing results
        """
        if not self._batch:
            return []

        events = self._batch.copy()
        self._batch.clear()
        self._last_process = datetime.now(timezone.utc)

        results = []
        for event in events:
            result = await self._processor.process(event)
            results.append(result)

        return results

    def batch_size(self) -> int:
        """Get current batch size."""
        return len(self._batch)
