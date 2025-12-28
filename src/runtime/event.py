"""Event types and structures for the event-driven runtime."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4


class EventType(Enum):
    """Types of events that can be processed."""

    # External triggers
    WEBHOOK_RECEIVED = "webhook"
    MESSAGE_RECEIVED = "message"
    SCHEDULE_TRIGGERED = "schedule"

    # Internal triggers
    GOAL_DEADLINE = "goal_deadline"
    SUBGOAL_COMPLETE = "subgoal_complete"
    ACTION_FAILED = "action_failed"
    ACTION_SUCCEEDED = "action_succeeded"

    # Background processes
    MEMORY_CONSOLIDATION = "memory_consolidation"
    HEALTH_CHECK = "health_check"
    LEARNING_UPDATE = "learning_update"

    # System events
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    ERROR = "error"
    INTERVENTION = "intervention"

    # User-defined
    CUSTOM = "custom"


class EventPriority(Enum):
    """Priority levels for events (lower value = higher priority)."""

    CRITICAL = 0  # System-critical, process immediately
    HIGH = 1  # Goal deadlines, interventions
    NORMAL = 2  # User messages, webhooks
    LOW = 3  # Scheduled tasks
    BACKGROUND = 4  # Background processes


class EventSource(Enum):
    """Source of the event."""

    EXTERNAL = "external"  # Webhooks, messages
    SCHEDULED = "scheduled"  # Scheduler-triggered
    GOAL = "goal"  # Goal-related
    INTERNAL = "internal"  # System-internal
    BACKGROUND = "background"  # Background processes


@dataclass
class Event:
    """Represents an event in the runtime queue.

    Events are the fundamental unit of work in the event-driven runtime.
    They are prioritized and processed in order.
    """

    type: EventType
    payload: Dict[str, Any] = field(default_factory=dict)
    priority: EventPriority = EventPriority.NORMAL
    source: EventSource = EventSource.INTERNAL
    deadline: Optional[datetime] = None
    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "Event") -> bool:
        """Compare events by priority for queue ordering."""
        if not isinstance(other, Event):
            return NotImplemented
        # First compare priority value (lower = higher priority)
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        # Then compare by creation time (earlier = higher priority)
        return self.created_at < other.created_at

    def __le__(self, other: "Event") -> bool:
        """Compare events by priority for queue ordering."""
        if not isinstance(other, Event):
            return NotImplemented
        return self < other or self == other

    def __gt__(self, other: "Event") -> bool:
        """Compare events by priority for queue ordering."""
        if not isinstance(other, Event):
            return NotImplemented
        return not self <= other

    def __ge__(self, other: "Event") -> bool:
        """Compare events by priority for queue ordering."""
        if not isinstance(other, Event):
            return NotImplemented
        return not self < other

    def __eq__(self, other: object) -> bool:
        """Check equality by event_id."""
        if not isinstance(other, Event):
            return NotImplemented
        return self.event_id == other.event_id

    def __hash__(self) -> int:
        """Hash by event_id."""
        return hash(self.event_id)

    def is_expired(self) -> bool:
        """Check if event has passed its deadline."""
        if self.deadline is None:
            return False
        return datetime.now(timezone.utc) > self.deadline

    def time_until_deadline(self) -> Optional[float]:
        """Get seconds until deadline, or None if no deadline."""
        if self.deadline is None:
            return None
        delta = self.deadline - datetime.now(timezone.utc)
        return delta.total_seconds()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "type": self.type.value,
            "priority": self.priority.value,
            "source": self.source.value,
            "payload": self.payload,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        return cls(
            event_id=data.get("event_id", str(uuid4())),
            type=EventType(data["type"]),
            priority=EventPriority(data.get("priority", EventPriority.NORMAL.value)),
            source=EventSource(data.get("source", EventSource.INTERNAL.value)),
            payload=data.get("payload", {}),
            deadline=(
                datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None
            ),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now(timezone.utc)
            ),
            metadata=data.get("metadata", {}),
        )

    # Factory methods for common event types

    @classmethod
    def message(
        cls,
        content: str,
        channel: str = "unknown",
        sender: Optional[str] = None,
        **kwargs: Any,
    ) -> "Event":
        """Create a message received event."""
        return cls(
            type=EventType.MESSAGE_RECEIVED,
            priority=EventPriority.NORMAL,
            source=EventSource.EXTERNAL,
            payload={
                "content": content,
                "channel": channel,
                "sender": sender,
                **kwargs,
            },
        )

    @classmethod
    def webhook(
        cls,
        endpoint: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> "Event":
        """Create a webhook received event."""
        return cls(
            type=EventType.WEBHOOK_RECEIVED,
            priority=EventPriority.NORMAL,
            source=EventSource.EXTERNAL,
            payload={
                "endpoint": endpoint,
                "data": data,
                "headers": headers or {},
            },
        )

    @classmethod
    def scheduled(
        cls,
        task_id: str,
        task_name: str,
        task_payload: Optional[Dict[str, Any]] = None,
    ) -> "Event":
        """Create a scheduled task event."""
        return cls(
            type=EventType.SCHEDULE_TRIGGERED,
            priority=EventPriority.LOW,
            source=EventSource.SCHEDULED,
            payload={
                "task_id": task_id,
                "task_name": task_name,
                "task_payload": task_payload or {},
            },
        )

    @classmethod
    def goal_deadline(
        cls,
        goal_id: str,
        goal_description: str,
        deadline: datetime,
    ) -> "Event":
        """Create a goal deadline event."""
        return cls(
            type=EventType.GOAL_DEADLINE,
            priority=EventPriority.HIGH,
            source=EventSource.GOAL,
            deadline=deadline,
            payload={
                "goal_id": goal_id,
                "goal_description": goal_description,
            },
        )

    @classmethod
    def action_result(
        cls,
        action: str,
        success: bool,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> "Event":
        """Create an action result event."""
        return cls(
            type=EventType.ACTION_SUCCEEDED if success else EventType.ACTION_FAILED,
            priority=EventPriority.NORMAL if success else EventPriority.HIGH,
            source=EventSource.INTERNAL,
            payload={
                "action": action,
                "success": success,
                "result": result or {},
                "error": error,
            },
        )

    @classmethod
    def background(
        cls,
        event_type: EventType,
        payload: Optional[Dict[str, Any]] = None,
    ) -> "Event":
        """Create a background process event."""
        return cls(
            type=event_type,
            priority=EventPriority.BACKGROUND,
            source=EventSource.BACKGROUND,
            payload=payload or {},
        )

    @classmethod
    def system(
        cls,
        event_type: EventType,
        payload: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> "Event":
        """Create a system event."""
        return cls(
            type=event_type,
            priority=priority,
            source=EventSource.INTERNAL,
            payload=payload or {},
        )

    @classmethod
    def error(
        cls,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> "Event":
        """Create an error event."""
        return cls(
            type=EventType.ERROR,
            priority=EventPriority.HIGH,
            source=EventSource.INTERNAL,
            payload={
                "error_type": error_type,
                "message": message,
                "details": details or {},
            },
        )
