"""Autonomous runtime - main event-driven runtime class."""

import asyncio
import signal
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, Optional

from loguru import logger

from src.runtime.background import BackgroundProcessManager
from src.runtime.event import Event, EventPriority, EventType
from src.runtime.listener import CallbackListener, EventListenerManager, WebhookListener
from src.runtime.processor import EventProcessor, ProcessingResult
from src.runtime.queue import EventQueue
from src.runtime.scheduler import PatternLearner, Scheduler


class RuntimeState(Enum):
    """State of the autonomous runtime."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class RuntimeConfiguration:
    """Configuration for the autonomous runtime."""

    # Event queue settings
    queue_maxsize: int = 0

    # Webhook settings
    webhook_enabled: bool = False
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080
    webhook_path: str = "/webhook"
    webhook_auth_token: Optional[str] = None

    # Scheduler settings
    scheduler_enabled: bool = True
    scheduler_check_interval: float = 10.0

    # Background process settings
    background_enabled: bool = True
    health_check_interval: float = 300.0
    memory_consolidation_interval: float = 3600.0
    learning_update_interval: float = 1800.0

    # Processing settings
    process_timeout: float = 300.0  # Max time per event
    max_concurrent_events: int = 1  # Events processed in parallel

    # Shutdown settings
    graceful_shutdown_timeout: float = 30.0


@dataclass
class RuntimeStatistics:
    """Statistics for the autonomous runtime."""

    state: RuntimeState = RuntimeState.STOPPED
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    uptime_seconds: float = 0.0
    events_processed: int = 0
    events_failed: int = 0
    current_queue_size: int = 0
    last_event_at: Optional[datetime] = None


class AutonomousRuntime:
    """Event-driven runtime for the autonomous agent.

    Provides:
    - Priority event queue
    - External event listeners (webhooks, messages)
    - Background processes (memory, health, learning)
    - Self-scheduling with pattern learning
    - Graceful shutdown handling
    """

    def __init__(
        self,
        config: Optional[RuntimeConfiguration] = None,
    ):
        """Initialize autonomous runtime.

        Args:
            config: Runtime configuration
        """
        self._config = config or RuntimeConfiguration()
        self._state = RuntimeState.STOPPED
        self._statistics = RuntimeStatistics()

        # Core components
        self._queue = EventQueue(maxsize=self._config.queue_maxsize)
        self._processor = EventProcessor()
        self._scheduler = Scheduler(
            event_queue=self._queue,
            check_interval=self._config.scheduler_check_interval,
        )
        self._background = BackgroundProcessManager()
        self._listeners = EventListenerManager()

        # Callback listener for programmatic events
        self._callback_listener = CallbackListener(self._queue, name="runtime")
        self._listeners.add_listener(self._callback_listener)

        # Webhook listener (optional)
        if self._config.webhook_enabled:
            webhook = WebhookListener(
                event_queue=self._queue,
                host=self._config.webhook_host,
                port=self._config.webhook_port,
                path=self._config.webhook_path,
                auth_token=self._config.webhook_auth_token,
            )
            self._listeners.add_listener(webhook)

        # Pattern learner for scheduler
        self._pattern_learner = PatternLearner()
        self._scheduler.set_pattern_learner(self._pattern_learner)

        # Main loop task
        self._main_task: Optional[asyncio.Task[None]] = None

        # Shutdown handling
        self._shutdown_event = asyncio.Event()

        logger.debug("AutonomousRuntime initialized")

    # === Event Handling ===

    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[Event], Coroutine[Any, Any, Any]],
    ) -> None:
        """Register an event handler.

        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        self._processor.register_handler(event_type, handler)

    def set_default_handler(
        self,
        handler: Callable[[Event], Coroutine[Any, Any, Any]],
    ) -> None:
        """Set the default handler for unhandled events.

        Args:
            handler: Default handler
        """
        self._processor.set_default_handler(handler)

    # === Event Injection ===

    async def emit(self, event: Event) -> None:
        """Emit an event to the runtime.

        Args:
            event: Event to emit
        """
        await self._callback_listener.inject(event)

    async def emit_message(
        self,
        content: str,
        channel: str = "internal",
        sender: Optional[str] = None,
    ) -> None:
        """Emit a message event.

        Args:
            content: Message content
            channel: Message channel
            sender: Message sender
        """
        event = Event.message(content=content, channel=channel, sender=sender)
        await self.emit(event)

    # === Scheduling ===

    def schedule(
        self,
        name: str,
        when: datetime,
        payload: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Schedule a task for future execution.

        Args:
            name: Task name
            when: When to run
            payload: Task payload
            **kwargs: Additional scheduler arguments
        """
        self._scheduler.schedule(name=name, when=when, payload=payload, **kwargs)

    def schedule_recurring(
        self,
        name: str,
        interval_seconds: float,
        payload: Optional[Dict[str, Any]] = None,
        start_immediately: bool = False,
    ) -> None:
        """Schedule a recurring task.

        Args:
            name: Task name
            interval_seconds: Interval between runs
            payload: Task payload
            start_immediately: Run immediately on start
        """
        from datetime import timedelta

        self._scheduler.schedule_recurring(
            name=name,
            interval=timedelta(seconds=interval_seconds),
            payload=payload,
            start_immediately=start_immediately,
        )

    # === Background Processes ===

    def register_background_process(
        self,
        name: str,
        func: Callable[[], Coroutine[Any, Any, None]],
        interval: float,
        **kwargs: Any,
    ) -> None:
        """Register a background process.

        Args:
            name: Process name
            func: Process function
            interval: Run interval in seconds
            **kwargs: Additional process options
        """
        self._background.register(name=name, func=func, interval=interval, **kwargs)

    # === Lifecycle ===

    async def start(self) -> None:
        """Start the runtime."""
        if self._state == RuntimeState.RUNNING:
            logger.warning("Runtime already running")
            return

        self._state = RuntimeState.STARTING
        self._statistics.started_at = datetime.now(timezone.utc)

        try:
            # Start listeners
            await self._listeners.start_all()
            await self._callback_listener.start()

            # Start scheduler
            if self._config.scheduler_enabled:
                await self._scheduler.start()

            # Start background processes
            if self._config.background_enabled:
                await self._background.start_all()

            # Setup signal handlers
            self._setup_signal_handlers()

            # Emit startup event
            await self._queue.put(Event.system(EventType.STARTUP, priority=EventPriority.CRITICAL))

            # Start main loop
            self._state = RuntimeState.RUNNING
            self._statistics.state = RuntimeState.RUNNING
            self._main_task = asyncio.create_task(self._main_loop())

            logger.info("AutonomousRuntime started")

        except Exception as e:
            self._state = RuntimeState.ERROR
            logger.error(f"Failed to start runtime: {e}")
            raise

    async def stop(self) -> None:
        """Stop the runtime gracefully."""
        if self._state not in (RuntimeState.RUNNING, RuntimeState.PAUSED):
            logger.warning(f"Runtime not running (state: {self._state})")
            return

        self._state = RuntimeState.STOPPING
        logger.info("Stopping AutonomousRuntime...")

        # Signal shutdown
        self._shutdown_event.set()

        # Emit shutdown event
        await self._queue.put(Event.system(EventType.SHUTDOWN, priority=EventPriority.CRITICAL))

        # Wait for main loop to finish
        if self._main_task:
            try:
                await asyncio.wait_for(
                    self._main_task,
                    timeout=self._config.graceful_shutdown_timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("Main loop did not stop gracefully, cancelling")
                self._main_task.cancel()
                try:
                    await self._main_task
                except asyncio.CancelledError:
                    pass

        # Stop components in reverse order
        await self._background.stop_all()

        if self._config.scheduler_enabled:
            await self._scheduler.stop()

        await self._listeners.stop_all()

        self._state = RuntimeState.STOPPED
        self._statistics.state = RuntimeState.STOPPED
        self._statistics.stopped_at = datetime.now(timezone.utc)
        self._update_uptime()

        logger.info("AutonomousRuntime stopped")

    async def pause(self) -> None:
        """Pause event processing."""
        if self._state != RuntimeState.RUNNING:
            return

        self._queue.pause()
        self._state = RuntimeState.PAUSED
        self._statistics.state = RuntimeState.PAUSED
        logger.info("Runtime paused")

    async def resume(self) -> None:
        """Resume event processing."""
        if self._state != RuntimeState.PAUSED:
            return

        self._queue.resume()
        self._state = RuntimeState.RUNNING
        self._statistics.state = RuntimeState.RUNNING
        logger.info("Runtime resumed")

    # === Main Loop ===

    async def _main_loop(self) -> None:
        """Main event processing loop."""
        logger.debug("Main loop started")

        while self._state == RuntimeState.RUNNING:
            try:
                # Check for shutdown
                if self._shutdown_event.is_set():
                    break

                # Get next event (with timeout to check shutdown)
                try:
                    event = await asyncio.wait_for(
                        self._queue.get(),
                        timeout=1.0,
                    )
                except asyncio.TimeoutError:
                    continue

                # Process event
                try:
                    result = await asyncio.wait_for(
                        self._processor.process(event),
                        timeout=self._config.process_timeout,
                    )
                    self._update_event_statistics(result)

                except asyncio.TimeoutError:
                    logger.error(f"Event processing timeout: {event.type.value}")
                    self._statistics.events_failed += 1

                finally:
                    self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")

        logger.debug("Main loop ended")

    # === Signal Handling ===

    def _setup_signal_handlers(self) -> None:
        """Setup OS signal handlers for graceful shutdown."""
        try:
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(
                    sig,
                    lambda: asyncio.create_task(self._handle_signal(sig)),
                )
            logger.debug("Signal handlers installed")
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            logger.debug("Signal handlers not supported on this platform")

    async def _handle_signal(self, sig: signal.Signals) -> None:
        """Handle OS signal.

        Args:
            sig: Signal received
        """
        logger.info(f"Received signal {sig.name}, initiating shutdown")
        await self.stop()

    # === Statistics ===

    def _update_event_statistics(self, result: ProcessingResult) -> None:
        """Update event processing statistics.

        Args:
            result: Processing result
        """
        self._statistics.events_processed += 1
        self._statistics.last_event_at = datetime.now(timezone.utc)

        if not result.success:
            self._statistics.events_failed += 1

        self._statistics.current_queue_size = self._queue.qsize()

    def _update_uptime(self) -> None:
        """Update uptime statistic."""
        if self._statistics.started_at:
            end = self._statistics.stopped_at or datetime.now(timezone.utc)
            self._statistics.uptime_seconds = (end - self._statistics.started_at).total_seconds()

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive runtime statistics.

        Returns:
            Statistics dictionary
        """
        self._update_uptime()
        self._statistics.current_queue_size = self._queue.qsize()

        return {
            "runtime": {
                "state": self._state.value,
                "started_at": (
                    self._statistics.started_at.isoformat() if self._statistics.started_at else None
                ),
                "uptime_seconds": self._statistics.uptime_seconds,
                "events_processed": self._statistics.events_processed,
                "events_failed": self._statistics.events_failed,
                "current_queue_size": self._statistics.current_queue_size,
                "last_event_at": (
                    self._statistics.last_event_at.isoformat()
                    if self._statistics.last_event_at
                    else None
                ),
            },
            "queue": {
                "size": self._queue.qsize(),
                "paused": self._queue.is_paused(),
                "statistics": self._queue.get_statistics().__dict__,
            },
            "processor": self._processor.get_statistics().__dict__,
            "scheduler": self._scheduler.get_statistics().__dict__,
            "background": self._background.get_statistics(),
            "listeners": self._listeners.get_statistics(),
        }

    # === Properties ===

    @property
    def state(self) -> RuntimeState:
        """Get current runtime state."""
        return self._state

    @property
    def is_running(self) -> bool:
        """Check if runtime is running."""
        return self._state == RuntimeState.RUNNING

    @property
    def queue(self) -> EventQueue:
        """Get the event queue."""
        return self._queue

    @property
    def scheduler(self) -> Scheduler:
        """Get the scheduler."""
        return self._scheduler

    @property
    def background(self) -> BackgroundProcessManager:
        """Get the background process manager."""
        return self._background

    @property
    def processor(self) -> EventProcessor:
        """Get the event processor."""
        return self._processor


async def run_runtime(
    runtime: AutonomousRuntime,
    until_stopped: bool = True,
) -> None:
    """Run a runtime until stopped.

    Args:
        runtime: Runtime to run
        until_stopped: Wait until runtime is stopped
    """
    await runtime.start()

    if until_stopped:
        while runtime.is_running:
            await asyncio.sleep(1)
