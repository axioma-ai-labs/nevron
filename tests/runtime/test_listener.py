"""Tests for Event Listener module."""

import asyncio

import pytest

from src.runtime.event import Event, EventType
from src.runtime.listener import (
    CallbackListener,
    EventListenerManager,
    ListenerStatistics,
    MessageChannelListener,
    WebhookListener,
)
from src.runtime.queue import EventQueue


class TestListenerStatistics:
    """Tests for ListenerStatistics dataclass."""

    def test_default_statistics(self):
        """Test default statistics values."""
        stats = ListenerStatistics()

        assert stats.events_received == 0
        assert stats.events_forwarded == 0
        assert stats.errors == 0
        assert stats.last_event_at is None
        assert stats.started_at is None
        assert stats.is_running is False


class TestCallbackListener:
    """Tests for CallbackListener class."""

    def test_callback_listener_creation(self):
        """Test creating a callback listener."""
        queue = EventQueue()
        listener = CallbackListener(event_queue=queue)

        assert listener._name == "callback"
        assert not listener.is_running

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test callback listener start/stop."""
        queue = EventQueue()
        listener = CallbackListener(event_queue=queue)

        await listener.start()
        assert listener.is_running

        await listener.stop()
        assert not listener.is_running

    @pytest.mark.asyncio
    async def test_inject_event(self):
        """Test injecting event through callback."""
        queue = EventQueue()
        listener = CallbackListener(event_queue=queue)

        await listener.start()

        event = Event(type=EventType.MESSAGE_RECEIVED, payload={"test": True})
        await listener.inject(event)

        assert queue.qsize() == 1
        retrieved = await queue.get()
        assert retrieved.payload["test"] is True

        await listener.stop()

    @pytest.mark.asyncio
    async def test_inject_when_stopped(self):
        """Test injection when listener is stopped."""
        queue = EventQueue()
        listener = CallbackListener(event_queue=queue)

        # Don't start listener
        event = Event(type=EventType.MESSAGE_RECEIVED)
        await listener.inject(event)

        # Event should be dropped
        assert queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_callback_notification(self):
        """Test callbacks are notified on inject."""
        queue = EventQueue()
        listener = CallbackListener(event_queue=queue)

        callback_called = {"value": False}

        def my_callback(event):
            callback_called["value"] = True

        listener.add_callback(my_callback)

        await listener.start()
        await listener.inject(Event(type=EventType.MESSAGE_RECEIVED))
        await listener.stop()

        assert callback_called["value"] is True

    @pytest.mark.asyncio
    async def test_statistics_update(self):
        """Test statistics are updated on inject."""
        queue = EventQueue()
        listener = CallbackListener(event_queue=queue)

        await listener.start()

        await listener.inject(Event(type=EventType.MESSAGE_RECEIVED))
        await listener.inject(Event(type=EventType.MESSAGE_RECEIVED))

        stats = listener.get_statistics()

        assert stats.events_received == 2
        assert stats.events_forwarded == 2
        assert stats.last_event_at is not None

        await listener.stop()


class TestMessageChannelListener:
    """Tests for MessageChannelListener class."""

    def test_message_listener_creation(self):
        """Test creating a message channel listener."""
        queue = EventQueue()
        listener = MessageChannelListener(
            event_queue=queue,
            channel="telegram",
            poll_interval=1.0,
        )

        assert listener._name == "channel:telegram"
        assert listener._poll_interval == 1.0

    @pytest.mark.asyncio
    async def test_no_callback_warning(self):
        """Test that starting without callback logs error."""
        queue = EventQueue()
        listener = MessageChannelListener(
            event_queue=queue,
            channel="test",
        )

        # Start without setting callback - should not crash
        await listener.start()
        # Listener shouldn't start without callback
        assert not listener.is_running

    @pytest.mark.asyncio
    async def test_message_processing(self):
        """Test processing fetched messages."""
        queue = EventQueue()
        listener = MessageChannelListener(
            event_queue=queue,
            channel="test",
            poll_interval=0.1,
        )

        messages = [
            {"content": "Hello", "sender": "user1"},
            {"content": "World", "sender": "user2"},
        ]
        call_count = {"value": 0}

        def mock_callback():
            call_count["value"] += 1
            if call_count["value"] == 1:
                return messages
            return []

        listener.set_message_callback(mock_callback)

        await listener.start()
        await asyncio.sleep(0.25)
        await listener.stop()

        # Should have processed the messages
        assert queue.qsize() >= 2

    @pytest.mark.asyncio
    async def test_async_callback(self):
        """Test async message callback."""
        queue = EventQueue()
        listener = MessageChannelListener(
            event_queue=queue,
            channel="test",
            poll_interval=0.1,
        )

        call_count = {"value": 0}

        async def async_callback():
            call_count["value"] += 1
            if call_count["value"] == 1:
                return [{"content": "Async message", "sender": "user"}]
            return []

        listener.set_message_callback(async_callback)

        await listener.start()
        await asyncio.sleep(0.25)
        await listener.stop()

        assert queue.qsize() >= 1


class TestWebhookListener:
    """Tests for WebhookListener class."""

    def test_webhook_listener_creation(self):
        """Test creating a webhook listener."""
        queue = EventQueue()
        listener = WebhookListener(
            event_queue=queue,
            host="localhost",
            port=8080,
        )

        assert listener._name == "webhook"
        assert listener._host == "localhost"
        assert listener._port == 8080

    def test_register_handler(self):
        """Test registering webhook handlers."""
        queue = EventQueue()
        listener = WebhookListener(event_queue=queue)

        def handler(data):
            return Event(type=EventType.WEBHOOK_RECEIVED, payload=data)

        listener.register_handler("/github", handler)
        listener.register_handler("/stripe", handler)

        assert "/github" in listener._handlers
        assert "/stripe" in listener._handlers

    def test_get_statistics(self):
        """Test getting webhook statistics."""
        queue = EventQueue()
        listener = WebhookListener(event_queue=queue)

        stats = listener.get_statistics()

        assert stats.events_received == 0
        assert stats.is_running is False


class TestEventListenerManager:
    """Tests for EventListenerManager class."""

    def test_manager_creation(self):
        """Test creating a listener manager."""
        manager = EventListenerManager()

        assert manager is not None
        assert len(manager.listeners) == 0

    def test_add_listener(self):
        """Test adding listeners to manager."""
        queue = EventQueue()
        manager = EventListenerManager()

        listener = CallbackListener(event_queue=queue)
        manager.add_listener(listener)

        assert len(manager.listeners) == 1

    def test_remove_listener(self):
        """Test removing listeners from manager."""
        queue = EventQueue()
        manager = EventListenerManager()

        listener = CallbackListener(event_queue=queue)
        manager.add_listener(listener)
        manager.remove_listener(listener)

        assert len(manager.listeners) == 0

    @pytest.mark.asyncio
    async def test_start_stop_all(self):
        """Test starting and stopping all listeners."""
        queue = EventQueue()
        manager = EventListenerManager()

        listener1 = CallbackListener(event_queue=queue, name="callback1")
        listener2 = CallbackListener(event_queue=queue, name="callback2")

        manager.add_listener(listener1)
        manager.add_listener(listener2)

        await manager.start_all()

        assert listener1.is_running
        assert listener2.is_running
        assert manager.is_running

        await manager.stop_all()

        assert not listener1.is_running
        assert not listener2.is_running
        assert not manager.is_running

    def test_get_statistics(self):
        """Test getting statistics for all listeners."""
        queue = EventQueue()
        manager = EventListenerManager()

        listener = CallbackListener(event_queue=queue)
        manager.add_listener(listener)

        stats = manager.get_statistics()

        assert "callback" in stats
        assert stats["callback"].is_running is False
