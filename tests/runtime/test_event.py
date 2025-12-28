"""Tests for Event module."""

from datetime import datetime, timedelta, timezone

from src.runtime.event import Event, EventPriority, EventSource, EventType


class TestEvent:
    """Tests for Event dataclass."""

    def test_event_creation(self):
        """Test creating an event."""
        event = Event(
            type=EventType.MESSAGE_RECEIVED,
            payload={"content": "Hello"},
        )

        assert event.type == EventType.MESSAGE_RECEIVED
        assert event.payload["content"] == "Hello"
        assert event.priority == EventPriority.NORMAL
        assert event.source == EventSource.INTERNAL
        assert event.event_id is not None
        assert event.created_at is not None

    def test_event_comparison_by_priority(self):
        """Test event comparison for queue ordering."""
        high = Event(type=EventType.GOAL_DEADLINE, priority=EventPriority.HIGH)
        normal = Event(type=EventType.MESSAGE_RECEIVED, priority=EventPriority.NORMAL)
        low = Event(type=EventType.SCHEDULE_TRIGGERED, priority=EventPriority.LOW)

        # Higher priority (lower value) should come first
        assert high < normal
        assert normal < low
        assert high < low

    def test_event_comparison_by_time(self):
        """Test event comparison when priority is equal."""
        now = datetime.now(timezone.utc)
        earlier = Event(
            type=EventType.MESSAGE_RECEIVED,
            priority=EventPriority.NORMAL,
        )
        earlier.created_at = now - timedelta(seconds=10)

        later = Event(
            type=EventType.MESSAGE_RECEIVED,
            priority=EventPriority.NORMAL,
        )
        later.created_at = now

        # Earlier event should come first when priority is equal
        assert earlier < later

    def test_event_equality(self):
        """Test event equality by ID."""
        event1 = Event(type=EventType.MESSAGE_RECEIVED)
        event2 = Event(type=EventType.MESSAGE_RECEIVED)
        event3 = Event(type=EventType.MESSAGE_RECEIVED)
        event3.event_id = event1.event_id

        assert event1 != event2  # Different IDs
        assert event1 == event3  # Same ID

    def test_is_expired(self):
        """Test deadline expiration check."""
        # Event without deadline
        event1 = Event(type=EventType.MESSAGE_RECEIVED)
        assert not event1.is_expired()

        # Event with past deadline
        event2 = Event(
            type=EventType.GOAL_DEADLINE,
            deadline=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert event2.is_expired()

        # Event with future deadline
        event3 = Event(
            type=EventType.GOAL_DEADLINE,
            deadline=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert not event3.is_expired()

    def test_time_until_deadline(self):
        """Test time until deadline calculation."""
        # No deadline
        event1 = Event(type=EventType.MESSAGE_RECEIVED)
        assert event1.time_until_deadline() is None

        # Future deadline
        event2 = Event(
            type=EventType.GOAL_DEADLINE,
            deadline=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        remaining = event2.time_until_deadline()
        assert remaining is not None
        assert 3500 < remaining < 3700  # Approximately 1 hour

    def test_to_dict(self):
        """Test converting event to dict."""
        event = Event(
            type=EventType.MESSAGE_RECEIVED,
            priority=EventPriority.HIGH,
            source=EventSource.EXTERNAL,
            payload={"key": "value"},
        )

        data = event.to_dict()

        assert data["type"] == "message"
        assert data["priority"] == 1
        assert data["source"] == "external"
        assert data["payload"]["key"] == "value"
        assert "event_id" in data
        assert "created_at" in data

    def test_from_dict(self):
        """Test creating event from dict."""
        data = {
            "type": "webhook",
            "priority": 2,
            "source": "external",
            "payload": {"endpoint": "/test"},
        }

        event = Event.from_dict(data)

        assert event.type == EventType.WEBHOOK_RECEIVED
        assert event.priority == EventPriority.NORMAL
        assert event.source == EventSource.EXTERNAL
        assert event.payload["endpoint"] == "/test"


class TestEventFactoryMethods:
    """Tests for Event factory methods."""

    def test_message_factory(self):
        """Test message event factory."""
        event = Event.message(
            content="Hello world",
            channel="telegram",
            sender="user123",
        )

        assert event.type == EventType.MESSAGE_RECEIVED
        assert event.priority == EventPriority.NORMAL
        assert event.source == EventSource.EXTERNAL
        assert event.payload["content"] == "Hello world"
        assert event.payload["channel"] == "telegram"
        assert event.payload["sender"] == "user123"

    def test_webhook_factory(self):
        """Test webhook event factory."""
        event = Event.webhook(
            endpoint="/github",
            data={"action": "push"},
            headers={"X-GitHub-Event": "push"},
        )

        assert event.type == EventType.WEBHOOK_RECEIVED
        assert event.source == EventSource.EXTERNAL
        assert event.payload["endpoint"] == "/github"
        assert event.payload["data"]["action"] == "push"
        assert event.payload["headers"]["X-GitHub-Event"] == "push"

    def test_scheduled_factory(self):
        """Test scheduled event factory."""
        event = Event.scheduled(
            task_id="task-123",
            task_name="daily_report",
            task_payload={"report_type": "summary"},
        )

        assert event.type == EventType.SCHEDULE_TRIGGERED
        assert event.priority == EventPriority.LOW
        assert event.source == EventSource.SCHEDULED
        assert event.payload["task_id"] == "task-123"
        assert event.payload["task_name"] == "daily_report"

    def test_goal_deadline_factory(self):
        """Test goal deadline event factory."""
        deadline = datetime.now(timezone.utc) + timedelta(hours=2)
        event = Event.goal_deadline(
            goal_id="goal-456",
            goal_description="Complete task X",
            deadline=deadline,
        )

        assert event.type == EventType.GOAL_DEADLINE
        assert event.priority == EventPriority.HIGH
        assert event.source == EventSource.GOAL
        assert event.deadline == deadline
        assert event.payload["goal_id"] == "goal-456"

    def test_action_result_success(self):
        """Test action result factory for success."""
        event = Event.action_result(
            action="search",
            success=True,
            result={"count": 10},
        )

        assert event.type == EventType.ACTION_SUCCEEDED
        assert event.priority == EventPriority.NORMAL
        assert event.payload["success"] is True
        assert event.payload["result"]["count"] == 10

    def test_action_result_failure(self):
        """Test action result factory for failure."""
        event = Event.action_result(
            action="search",
            success=False,
            error="Rate limit exceeded",
        )

        assert event.type == EventType.ACTION_FAILED
        assert event.priority == EventPriority.HIGH
        assert event.payload["success"] is False
        assert event.payload["error"] == "Rate limit exceeded"

    def test_background_factory(self):
        """Test background event factory."""
        event = Event.background(
            event_type=EventType.MEMORY_CONSOLIDATION,
            payload={"consolidated": 50},
        )

        assert event.type == EventType.MEMORY_CONSOLIDATION
        assert event.priority == EventPriority.BACKGROUND
        assert event.source == EventSource.BACKGROUND

    def test_error_factory(self):
        """Test error event factory."""
        event = Event.error(
            error_type="ConnectionError",
            message="Failed to connect",
            details={"host": "api.example.com"},
        )

        assert event.type == EventType.ERROR
        assert event.priority == EventPriority.HIGH
        assert event.payload["error_type"] == "ConnectionError"
        assert event.payload["message"] == "Failed to connect"


class TestEventType:
    """Tests for EventType enum."""

    def test_all_types_have_values(self):
        """Test all event types have string values."""
        for event_type in EventType:
            assert isinstance(event_type.value, str)
            assert len(event_type.value) > 0


class TestEventPriority:
    """Tests for EventPriority enum."""

    def test_priority_ordering(self):
        """Test priority values are ordered correctly."""
        assert EventPriority.CRITICAL.value < EventPriority.HIGH.value
        assert EventPriority.HIGH.value < EventPriority.NORMAL.value
        assert EventPriority.NORMAL.value < EventPriority.LOW.value
        assert EventPriority.LOW.value < EventPriority.BACKGROUND.value
