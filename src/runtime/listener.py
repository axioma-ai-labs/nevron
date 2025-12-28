"""External event listeners for the event-driven runtime."""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from aiohttp import web
from loguru import logger

from src.runtime.event import Event
from src.runtime.queue import EventQueue


@dataclass
class ListenerStatistics:
    """Statistics for an event listener."""

    events_received: int = 0
    events_forwarded: int = 0
    errors: int = 0
    last_event_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    is_running: bool = False


class EventListener(ABC):
    """Base class for event listeners."""

    def __init__(self, event_queue: EventQueue, name: str = "listener"):
        """Initialize listener.

        Args:
            event_queue: Queue to push events to
            name: Listener name for logging
        """
        self._queue = event_queue
        self._name = name
        self._statistics = ListenerStatistics()
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None

    @abstractmethod
    async def start(self) -> None:
        """Start listening for events."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening for events."""
        pass

    async def push_event(self, event: Event) -> None:
        """Push an event to the queue.

        Args:
            event: Event to push
        """
        await self._queue.put(event)
        self._statistics.events_forwarded += 1
        self._statistics.last_event_at = datetime.now(timezone.utc)
        logger.debug(f"[{self._name}] Event pushed: {event.type.value}")

    def get_statistics(self) -> ListenerStatistics:
        """Get listener statistics."""
        self._statistics.is_running = self._running
        return self._statistics

    @property
    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._running


class WebhookListener(EventListener):
    """HTTP webhook listener for external events."""

    def __init__(
        self,
        event_queue: EventQueue,
        host: str = "0.0.0.0",
        port: int = 8080,
        path: str = "/webhook",
        auth_token: Optional[str] = None,
    ):
        """Initialize webhook listener.

        Args:
            event_queue: Queue to push events to
            host: Host to bind to
            port: Port to listen on
            path: Webhook endpoint path
            auth_token: Optional authentication token
        """
        super().__init__(event_queue, name="webhook")
        self._host = host
        self._port = port
        self._path = path
        self._auth_token = auth_token
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Event]] = {}

    def register_handler(
        self,
        endpoint: str,
        handler: Callable[[Dict[str, Any]], Event],
    ) -> None:
        """Register a custom handler for a specific endpoint.

        Args:
            endpoint: Endpoint path (e.g., "/github")
            handler: Function that converts request data to Event
        """
        self._handlers[endpoint] = handler
        logger.debug(f"Registered webhook handler for {endpoint}")

    async def start(self) -> None:
        """Start the webhook server."""
        if self._running:
            logger.warning("Webhook listener already running")
            return

        self._app = web.Application()
        self._app.router.add_post(self._path, self._handle_webhook)

        # Add custom endpoint handlers
        for endpoint, _handler in self._handlers.items():
            self._app.router.add_post(endpoint, self._handle_custom_webhook)

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()

        self._site = web.TCPSite(self._runner, self._host, self._port)
        await self._site.start()

        self._running = True
        self._statistics.started_at = datetime.now(timezone.utc)
        logger.info(f"Webhook listener started on {self._host}:{self._port}{self._path}")

    async def stop(self) -> None:
        """Stop the webhook server."""
        if not self._running:
            return

        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()

        self._running = False
        logger.info("Webhook listener stopped")

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """Handle incoming webhook request.

        Args:
            request: The HTTP request

        Returns:
            HTTP response
        """
        try:
            # Check authentication
            if self._auth_token:
                auth_header = request.headers.get("Authorization", "")
                if auth_header != f"Bearer {self._auth_token}":
                    logger.warning("Webhook authentication failed")
                    return web.Response(status=401, text="Unauthorized")

            # Parse request body
            try:
                data = await request.json()
            except Exception:
                data = {"raw": await request.text()}

            self._statistics.events_received += 1

            # Create event
            event = Event.webhook(
                endpoint=str(request.path),
                data=data,
                headers=dict(request.headers),
            )

            await self.push_event(event)

            return web.Response(status=200, text="OK")

        except Exception as e:
            self._statistics.errors += 1
            logger.error(f"Webhook handling error: {e}")
            return web.Response(status=500, text="Internal Server Error")

    async def _handle_custom_webhook(self, request: web.Request) -> web.Response:
        """Handle custom webhook with registered handler.

        Args:
            request: The HTTP request

        Returns:
            HTTP response
        """
        try:
            handler = self._handlers.get(str(request.path))
            if not handler:
                return web.Response(status=404, text="Not Found")

            try:
                data = await request.json()
            except Exception:
                data = {"raw": await request.text()}

            self._statistics.events_received += 1

            # Use custom handler to create event
            event = handler(data)
            await self.push_event(event)

            return web.Response(status=200, text="OK")

        except Exception as e:
            self._statistics.errors += 1
            logger.error(f"Custom webhook handling error: {e}")
            return web.Response(status=500, text="Internal Server Error")


class MessageChannelListener(EventListener):
    """Listener for message channels (Telegram, Slack, etc.)."""

    def __init__(
        self,
        event_queue: EventQueue,
        channel: str,
        poll_interval: float = 1.0,
    ):
        """Initialize message channel listener.

        Args:
            event_queue: Queue to push events to
            channel: Channel name (e.g., "telegram", "slack")
            poll_interval: Polling interval in seconds
        """
        super().__init__(event_queue, name=f"channel:{channel}")
        self._channel = channel
        self._poll_interval = poll_interval
        self._message_callback: Optional[Callable[[], List[Dict[str, Any]]]] = None

    def set_message_callback(
        self,
        callback: Callable[[], List[Dict[str, Any]]],
    ) -> None:
        """Set callback to retrieve new messages.

        Args:
            callback: Async function that returns list of message dicts
        """
        self._message_callback = callback

    async def start(self) -> None:
        """Start listening for messages."""
        if self._running:
            logger.warning(f"Channel listener {self._channel} already running")
            return

        if not self._message_callback:
            logger.error(f"No message callback set for {self._channel}")
            return

        self._running = True
        self._statistics.started_at = datetime.now(timezone.utc)
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"Message channel listener started: {self._channel}")

    async def stop(self) -> None:
        """Stop listening for messages."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(f"Message channel listener stopped: {self._channel}")

    async def _poll_loop(self) -> None:
        """Poll for new messages."""
        while self._running:
            try:
                if self._message_callback:
                    messages = self._message_callback()
                    if asyncio.iscoroutine(messages):
                        messages = await messages

                    for msg in messages:
                        self._statistics.events_received += 1
                        event = Event.message(
                            content=msg.get("content", ""),
                            channel=self._channel,
                            sender=msg.get("sender"),
                            **{k: v for k, v in msg.items() if k not in ["content", "sender"]},
                        )
                        await self.push_event(event)

            except Exception as e:
                self._statistics.errors += 1
                logger.error(f"Error polling {self._channel}: {e}")

            await asyncio.sleep(self._poll_interval)


class CallbackListener(EventListener):
    """Simple callback-based listener for programmatic event injection."""

    def __init__(self, event_queue: EventQueue, name: str = "callback"):
        """Initialize callback listener.

        Args:
            event_queue: Queue to push events to
            name: Listener name
        """
        super().__init__(event_queue, name=name)
        self._callbacks: List[Callable[[Event], None]] = []

    async def start(self) -> None:
        """Mark listener as started."""
        self._running = True
        self._statistics.started_at = datetime.now(timezone.utc)
        logger.debug(f"Callback listener started: {self._name}")

    async def stop(self) -> None:
        """Mark listener as stopped."""
        self._running = False
        logger.debug(f"Callback listener stopped: {self._name}")

    async def inject(self, event: Event) -> None:
        """Inject an event directly.

        Args:
            event: Event to inject
        """
        if not self._running:
            logger.warning(f"Listener {self._name} not running, event dropped")
            return

        self._statistics.events_received += 1
        await self.push_event(event)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                result = callback(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def add_callback(self, callback: Callable[[Event], None]) -> None:
        """Add a callback to be notified of events.

        Args:
            callback: Callback function
        """
        self._callbacks.append(callback)


@dataclass
class EventListenerManager:
    """Manages multiple event listeners."""

    listeners: List[EventListener] = field(default_factory=list)
    _running: bool = False

    def add_listener(self, listener: EventListener) -> None:
        """Add a listener.

        Args:
            listener: Listener to add
        """
        self.listeners.append(listener)
        logger.debug(f"Added listener: {listener._name}")

    def remove_listener(self, listener: EventListener) -> None:
        """Remove a listener.

        Args:
            listener: Listener to remove
        """
        if listener in self.listeners:
            self.listeners.remove(listener)
            logger.debug(f"Removed listener: {listener._name}")

    async def start_all(self) -> None:
        """Start all listeners."""
        for listener in self.listeners:
            try:
                await listener.start()
            except Exception as e:
                logger.error(f"Failed to start listener {listener._name}: {e}")
        self._running = True
        logger.info(f"Started {len(self.listeners)} event listeners")

    async def stop_all(self) -> None:
        """Stop all listeners."""
        for listener in self.listeners:
            try:
                await listener.stop()
            except Exception as e:
                logger.error(f"Failed to stop listener {listener._name}: {e}")
        self._running = False
        logger.info("All event listeners stopped")

    def get_statistics(self) -> Dict[str, ListenerStatistics]:
        """Get statistics for all listeners.

        Returns:
            Dict mapping listener names to statistics
        """
        return {listener._name: listener.get_statistics() for listener in self.listeners}

    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running
