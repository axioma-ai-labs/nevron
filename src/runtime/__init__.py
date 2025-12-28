"""Event-Driven Runtime Module.

Provides an event-driven runtime for the autonomous agent with:
- Priority event queue
- External event listeners (webhooks, messages)
- Background processes (memory consolidation, health checks)
- Self-scheduling with patterns
"""

from src.runtime.background import BackgroundProcessManager
from src.runtime.event import Event, EventPriority, EventSource, EventType
from src.runtime.listener import EventListenerManager, WebhookListener
from src.runtime.processor import EventProcessor
from src.runtime.queue import EventQueue
from src.runtime.runtime import AutonomousRuntime, RuntimeState
from src.runtime.scheduler import RecurrencePattern, ScheduledTask, Scheduler

__all__ = [
    # Event System
    "Event",
    "EventType",
    "EventPriority",
    "EventSource",
    "EventQueue",
    # Listeners
    "WebhookListener",
    "EventListenerManager",
    # Scheduler
    "Scheduler",
    "ScheduledTask",
    "RecurrencePattern",
    # Background
    "BackgroundProcessManager",
    # Processing
    "EventProcessor",
    # Runtime
    "AutonomousRuntime",
    "RuntimeState",
]
