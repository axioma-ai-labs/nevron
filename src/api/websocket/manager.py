"""WebSocket connection manager for real-time event streaming."""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from fastapi import WebSocket
from loguru import logger

from src.api.config import api_settings
from src.api.schemas import WSMessage, WSMessageType


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting.

    Features:
    - Multiple client connections
    - Event subscriptions (clients can filter events)
    - Automatic heartbeat
    - Connection tracking and cleanup
    """

    def __init__(self):
        """Initialize the connection manager."""
        # Active connections: client_id -> WebSocket
        self._connections: Dict[str, WebSocket] = {}

        # Subscriptions: client_id -> set of event types
        self._subscriptions: Dict[str, Set[str]] = {}

        # Heartbeat task
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False

        # Statistics
        self._total_messages_sent = 0
        self._total_connections = 0

        logger.debug("WebSocket ConnectionManager initialized")

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
        """
        await websocket.accept()

        # Store connection
        self._connections[client_id] = websocket

        # Initialize with all events subscribed by default
        self._subscriptions[client_id] = {"*"}

        self._total_connections += 1

        logger.info(f"WebSocket client connected: {client_id} (total: {len(self._connections)})")

        # Start heartbeat if not running
        if not self._running and len(self._connections) == 1:
            await self._start_heartbeat()

        # Send welcome message
        await self._send_to_client(
            client_id,
            {
                "type": "connected",
                "client_id": client_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "subscriptions": list(self._subscriptions[client_id]),
            },
        )

    def disconnect(self, client_id: str) -> None:
        """Disconnect a WebSocket client.

        Args:
            client_id: Client to disconnect
        """
        if client_id in self._connections:
            del self._connections[client_id]

        if client_id in self._subscriptions:
            del self._subscriptions[client_id]

        logger.info(f"WebSocket client disconnected: {client_id} (total: {len(self._connections)})")

        # Stop heartbeat if no more connections
        if len(self._connections) == 0 and self._running:
            self._stop_heartbeat()

    def subscribe(self, client_id: str, events: List[str]) -> None:
        """Subscribe a client to specific events.

        Args:
            client_id: Client identifier
            events: List of event types to subscribe to (or ["*"] for all)
        """
        if client_id not in self._subscriptions:
            self._subscriptions[client_id] = set()

        # If subscribing to "*", clear other subscriptions
        if "*" in events:
            self._subscriptions[client_id] = {"*"}
        else:
            self._subscriptions[client_id].update(events)

        logger.debug(f"Client {client_id} subscribed to: {events}")

    def unsubscribe(self, client_id: str, events: List[str]) -> None:
        """Unsubscribe a client from specific events.

        Args:
            client_id: Client identifier
            events: List of event types to unsubscribe from
        """
        if client_id not in self._subscriptions:
            return

        for event in events:
            self._subscriptions[client_id].discard(event)

        logger.debug(f"Client {client_id} unsubscribed from: {events}")

    def _should_send_to_client(self, client_id: str, event_type: str) -> bool:
        """Check if a client should receive an event.

        Args:
            client_id: Client identifier
            event_type: Type of event

        Returns:
            True if client should receive the event
        """
        if client_id not in self._subscriptions:
            return False

        subs = self._subscriptions[client_id]

        # Wildcard subscription
        if "*" in subs:
            return True

        # Exact match
        if event_type in subs:
            return True

        # Category match (e.g., "agent.*" matches "agent.action")
        for sub in subs:
            if sub.endswith(".*"):
                category = sub[:-2]
                if event_type.startswith(category + "."):
                    return True

        return False

    async def _send_to_client(self, client_id: str, message: Dict[str, Any]) -> bool:
        """Send a message to a specific client.

        Args:
            client_id: Client identifier
            message: Message to send

        Returns:
            True if message was sent successfully
        """
        websocket = self._connections.get(client_id)
        if not websocket:
            return False

        try:
            await websocket.send_json(message)
            self._total_messages_sent += 1
            return True
        except Exception as e:
            logger.warning(f"Failed to send to client {client_id}: {e}")
            self.disconnect(client_id)
            return False

    async def broadcast(
        self,
        message_type: WSMessageType,
        data: Dict[str, Any],
    ) -> int:
        """Broadcast a message to all subscribed clients.

        Args:
            message_type: Type of message
            data: Message data

        Returns:
            Number of clients that received the message
        """
        if not self._connections:
            return 0

        message = {
            "type": message_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        sent_count = 0
        failed_clients = []

        for client_id in list(self._connections.keys()):
            if self._should_send_to_client(client_id, message_type.value):
                if await self._send_to_client(client_id, message):
                    sent_count += 1
                else:
                    failed_clients.append(client_id)

        # Clean up failed connections
        for client_id in failed_clients:
            self.disconnect(client_id)

        return sent_count

    async def broadcast_event(self, event: WSMessage) -> int:
        """Broadcast a WSMessage event.

        Args:
            event: WSMessage to broadcast

        Returns:
            Number of clients that received the message
        """
        return await self.broadcast(event.type, event.data)

    async def send_to(
        self,
        client_id: str,
        message_type: WSMessageType,
        data: Dict[str, Any],
    ) -> bool:
        """Send a message to a specific client.

        Args:
            client_id: Target client identifier
            message_type: Type of message
            data: Message data

        Returns:
            True if message was sent
        """
        message = {
            "type": message_type.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }

        return await self._send_to_client(client_id, message)

    async def _start_heartbeat(self) -> None:
        """Start the heartbeat task."""
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.debug("WebSocket heartbeat started")

    def _stop_heartbeat(self) -> None:
        """Stop the heartbeat task."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        logger.debug("WebSocket heartbeat stopped")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to all clients."""
        while self._running:
            try:
                await asyncio.sleep(api_settings.WS_HEARTBEAT_INTERVAL)

                if not self._connections:
                    continue

                await self.broadcast(
                    WSMessageType.HEARTBEAT,
                    {
                        "active_connections": len(self._connections),
                        "total_messages": self._total_messages_sent,
                    },
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get connection manager statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "active_connections": len(self._connections),
            "total_connections": self._total_connections,
            "total_messages_sent": self._total_messages_sent,
            "heartbeat_running": self._running,
            "clients": list(self._connections.keys()),
        }

    @property
    def connection_count(self) -> int:
        """Get number of active connections."""
        return len(self._connections)

    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running


# Singleton instance
_connection_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get or create the connection manager singleton.

    Returns:
        ConnectionManager instance
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
