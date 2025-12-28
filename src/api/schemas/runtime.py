"""Runtime-related schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RuntimeState(BaseModel):
    """Runtime state response."""

    state: str
    is_running: bool
    is_paused: bool


class RuntimeStatistics(BaseModel):
    """Full runtime statistics."""

    state: str
    started_at: Optional[datetime] = None
    uptime_seconds: float = 0.0
    events_processed: int = 0
    events_failed: int = 0
    current_queue_size: int = 0
    last_event_at: Optional[datetime] = None


class QueueStatistics(BaseModel):
    """Event queue statistics."""

    size: int
    paused: bool
    total_enqueued: int
    total_dequeued: int
    total_expired: int
    by_priority: Dict[str, int]
    by_type: Dict[str, int]


class ScheduledTask(BaseModel):
    """Scheduled task information."""

    name: str
    next_run: datetime
    last_run: Optional[datetime] = None
    run_count: int = 0
    is_recurring: bool = False
    interval_seconds: Optional[float] = None


class SchedulerStatistics(BaseModel):
    """Scheduler statistics."""

    tasks_scheduled: int
    tasks_executed: int
    next_task: Optional[str] = None
    next_run_at: Optional[datetime] = None


class BackgroundProcess(BaseModel):
    """Background process information."""

    name: str
    state: str
    iterations: int = 0
    errors: int = 0
    last_run_at: Optional[datetime] = None
    last_error: Optional[str] = None


class BackgroundStatistics(BaseModel):
    """Background process statistics."""

    processes: List[BackgroundProcess]
    total_running: int
    total_errors: int


class ScheduleRequest(BaseModel):
    """Request to schedule a task."""

    name: str
    when: Optional[datetime] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    recurring: bool = False
    interval_seconds: Optional[float] = None


class FullRuntimeStatistics(BaseModel):
    """Complete runtime statistics including all components."""

    runtime: RuntimeStatistics
    queue: QueueStatistics
    scheduler: SchedulerStatistics
    background: BackgroundStatistics
