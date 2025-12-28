"""Task scheduler for the event-driven runtime."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from loguru import logger

from src.runtime.event import Event, EventPriority
from src.runtime.queue import EventQueue


class RecurrencePattern(Enum):
    """Recurrence patterns for scheduled tasks."""

    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # Uses custom_interval


@dataclass
class ScheduledTask:
    """A task scheduled for future execution."""

    task_id: str
    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    next_run: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    recurrence: RecurrencePattern = RecurrencePattern.ONCE
    custom_interval: Optional[timedelta] = None
    priority: EventPriority = EventPriority.LOW
    enabled: bool = True
    last_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None  # None = unlimited
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_due(self) -> bool:
        """Check if task is due for execution."""
        if not self.enabled:
            return False
        if self.max_runs is not None and self.run_count >= self.max_runs:
            return False
        return datetime.now(timezone.utc) >= self.next_run

    def calculate_next_run(self) -> Optional[datetime]:
        """Calculate the next run time based on recurrence pattern.

        Returns:
            Next run time or None if no more runs
        """
        if self.recurrence == RecurrencePattern.ONCE:
            return None

        if self.max_runs is not None and self.run_count >= self.max_runs:
            return None

        base_time = self.next_run or datetime.now(timezone.utc)

        if self.recurrence == RecurrencePattern.HOURLY:
            return base_time + timedelta(hours=1)
        elif self.recurrence == RecurrencePattern.DAILY:
            return base_time + timedelta(days=1)
        elif self.recurrence == RecurrencePattern.WEEKLY:
            return base_time + timedelta(weeks=1)
        elif self.recurrence == RecurrencePattern.MONTHLY:
            # Approximate month as 30 days
            return base_time + timedelta(days=30)
        elif self.recurrence == RecurrencePattern.CUSTOM:
            if self.custom_interval:
                return base_time + self.custom_interval
            return None

        return None

    def mark_run(self) -> None:
        """Mark the task as having run."""
        self.last_run = datetime.now(timezone.utc)
        self.run_count += 1
        self.next_run = self.calculate_next_run() or self.next_run

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "payload": self.payload,
            "next_run": self.next_run.isoformat(),
            "recurrence": self.recurrence.value,
            "custom_interval": (
                self.custom_interval.total_seconds() if self.custom_interval else None
            ),
            "priority": self.priority.value,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "run_count": self.run_count,
            "max_runs": self.max_runs,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduledTask":
        """Create from dictionary."""
        return cls(
            task_id=data["task_id"],
            name=data["name"],
            payload=data.get("payload", {}),
            next_run=datetime.fromisoformat(data["next_run"]),
            recurrence=RecurrencePattern(data.get("recurrence", "once")),
            custom_interval=(
                timedelta(seconds=data["custom_interval"]) if data.get("custom_interval") else None
            ),
            priority=EventPriority(data.get("priority", EventPriority.LOW.value)),
            enabled=data.get("enabled", True),
            last_run=(datetime.fromisoformat(data["last_run"]) if data.get("last_run") else None),
            run_count=data.get("run_count", 0),
            max_runs=data.get("max_runs"),
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now(timezone.utc)
            ),
        )


@dataclass
class SchedulerStatistics:
    """Statistics for the scheduler."""

    total_tasks: int = 0
    enabled_tasks: int = 0
    tasks_executed: int = 0
    tasks_skipped: int = 0
    next_task_at: Optional[datetime] = None


class Scheduler:
    """Task scheduler for the event-driven runtime.

    Manages scheduled tasks and generates events when tasks are due.
    """

    def __init__(
        self,
        event_queue: EventQueue,
        check_interval: float = 10.0,
    ):
        """Initialize scheduler.

        Args:
            event_queue: Queue to push task events to
            check_interval: How often to check for due tasks (seconds)
        """
        self._queue = event_queue
        self._check_interval = check_interval
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task: Optional[asyncio.Task[None]] = None
        self._statistics = SchedulerStatistics()
        self._pattern_learner: Optional[PatternLearner] = None

    def schedule(
        self,
        name: str,
        when: datetime | timedelta,
        payload: Optional[Dict[str, Any]] = None,
        recurrence: RecurrencePattern = RecurrencePattern.ONCE,
        custom_interval: Optional[timedelta] = None,
        priority: EventPriority = EventPriority.LOW,
        max_runs: Optional[int] = None,
        task_id: Optional[str] = None,
    ) -> ScheduledTask:
        """Schedule a task for future execution.

        Args:
            name: Task name
            when: When to run (datetime or timedelta from now)
            payload: Task payload
            recurrence: Recurrence pattern
            custom_interval: Custom interval for CUSTOM recurrence
            priority: Event priority
            max_runs: Maximum number of runs (None = unlimited)
            task_id: Optional task ID (generated if not provided)

        Returns:
            The scheduled task
        """
        if isinstance(when, timedelta):
            next_run = datetime.now(timezone.utc) + when
        else:
            next_run = when

        task = ScheduledTask(
            task_id=task_id or str(uuid4()),
            name=name,
            payload=payload or {},
            next_run=next_run,
            recurrence=recurrence,
            custom_interval=custom_interval,
            priority=priority,
            max_runs=max_runs,
        )

        self._tasks[task.task_id] = task
        self._statistics.total_tasks = len(self._tasks)
        self._update_enabled_count()

        logger.info(f"Scheduled task: {name} (next run: {next_run})")
        return task

    def schedule_recurring(
        self,
        name: str,
        interval: timedelta,
        payload: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.LOW,
        start_immediately: bool = False,
    ) -> ScheduledTask:
        """Schedule a recurring task with custom interval.

        Args:
            name: Task name
            interval: Interval between runs
            payload: Task payload
            priority: Event priority
            start_immediately: Whether to run immediately

        Returns:
            The scheduled task
        """
        when = timedelta(seconds=0) if start_immediately else interval
        return self.schedule(
            name=name,
            when=when,
            payload=payload,
            recurrence=RecurrencePattern.CUSTOM,
            custom_interval=interval,
            priority=priority,
        )

    def unschedule(self, task_id: str) -> bool:
        """Remove a scheduled task.

        Args:
            task_id: ID of task to remove

        Returns:
            True if task was removed
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._statistics.total_tasks = len(self._tasks)
            self._update_enabled_count()
            logger.info(f"Unscheduled task: {task_id}")
            return True
        return False

    def enable(self, task_id: str) -> bool:
        """Enable a task.

        Args:
            task_id: ID of task to enable

        Returns:
            True if task was found and enabled
        """
        if task_id in self._tasks:
            self._tasks[task_id].enabled = True
            self._update_enabled_count()
            return True
        return False

    def disable(self, task_id: str) -> bool:
        """Disable a task.

        Args:
            task_id: ID of task to disable

        Returns:
            True if task was found and disabled
        """
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            self._update_enabled_count()
            return True
        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task or None
        """
        return self._tasks.get(task_id)

    def list_tasks(
        self,
        enabled_only: bool = False,
        due_only: bool = False,
    ) -> List[ScheduledTask]:
        """List scheduled tasks.

        Args:
            enabled_only: Only return enabled tasks
            due_only: Only return tasks that are due

        Returns:
            List of tasks
        """
        tasks = list(self._tasks.values())

        if enabled_only:
            tasks = [t for t in tasks if t.enabled]
        if due_only:
            tasks = [t for t in tasks if t.is_due()]

        return sorted(tasks, key=lambda t: t.next_run)

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            logger.warning("Scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._scheduler_loop())
        logger.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Scheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_due_tasks()
            except Exception as e:
                logger.error(f"Scheduler error: {e}")

            await asyncio.sleep(self._check_interval)

    async def _check_due_tasks(self) -> None:
        """Check for and execute due tasks."""
        due_tasks = self.list_tasks(due_only=True)

        for task in due_tasks:
            try:
                # Create event for the task
                event = Event.scheduled(
                    task_id=task.task_id,
                    task_name=task.name,
                    task_payload=task.payload,
                )
                event.priority = task.priority

                # Push to queue
                await self._queue.put(event)
                self._statistics.tasks_executed += 1

                # Update task
                task.mark_run()

                # Remove if no more runs
                if task.recurrence == RecurrencePattern.ONCE:
                    self.unschedule(task.task_id)
                elif task.max_runs and task.run_count >= task.max_runs:
                    self.unschedule(task.task_id)

                logger.debug(f"Task triggered: {task.name}")

            except Exception as e:
                self._statistics.tasks_skipped += 1
                logger.error(f"Failed to trigger task {task.name}: {e}")

        # Update next task time
        upcoming = self.list_tasks(enabled_only=True)
        self._statistics.next_task_at = upcoming[0].next_run if upcoming else None

    def _update_enabled_count(self) -> None:
        """Update the enabled task count."""
        self._statistics.enabled_tasks = sum(1 for t in self._tasks.values() if t.enabled)

    def get_statistics(self) -> SchedulerStatistics:
        """Get scheduler statistics.

        Returns:
            Current statistics
        """
        self._statistics.total_tasks = len(self._tasks)
        self._update_enabled_count()

        upcoming = self.list_tasks(enabled_only=True)
        self._statistics.next_task_at = upcoming[0].next_run if upcoming else None

        return self._statistics

    def clear(self) -> int:
        """Clear all scheduled tasks.

        Returns:
            Number of tasks cleared
        """
        count = len(self._tasks)
        self._tasks.clear()
        self._statistics = SchedulerStatistics()
        logger.info(f"Cleared {count} scheduled tasks")
        return count

    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    def set_pattern_learner(self, learner: "PatternLearner") -> None:
        """Set pattern learner for automatic scheduling.

        Args:
            learner: Pattern learner instance
        """
        self._pattern_learner = learner


class PatternLearner:
    """Learn optimal timing patterns from action history.

    Analyzes past actions to suggest optimal scheduling times.
    """

    def __init__(self):
        """Initialize pattern learner."""
        self._patterns: Dict[str, Dict[str, Any]] = {}
        self._action_history: List[Dict[str, Any]] = []

    def record_action(
        self,
        action: str,
        timestamp: datetime,
        success: bool,
        metrics: Optional[Dict[str, float]] = None,
    ) -> None:
        """Record an action for pattern learning.

        Args:
            action: Action name
            timestamp: When action occurred
            success: Whether action succeeded
            metrics: Optional metrics (e.g., engagement score)
        """
        self._action_history.append(
            {
                "action": action,
                "timestamp": timestamp,
                "hour": timestamp.hour,
                "day_of_week": timestamp.weekday(),
                "success": success,
                "metrics": metrics or {},
            }
        )

    def get_optimal_time(
        self,
        action: str,
        metric: str = "success",
    ) -> Optional[int]:
        """Get optimal hour for an action based on history.

        Args:
            action: Action name
            metric: Metric to optimize ("success" or a custom metric name)

        Returns:
            Optimal hour (0-23) or None if not enough data
        """
        action_data = [h for h in self._action_history if h["action"] == action]

        if len(action_data) < 10:  # Need at least 10 data points
            return None

        # Group by hour
        hour_scores: Dict[int, List[float]] = {}
        for data in action_data:
            hour = data["hour"]
            if hour not in hour_scores:
                hour_scores[hour] = []

            if metric == "success":
                hour_scores[hour].append(1.0 if data["success"] else 0.0)
            elif metric in data.get("metrics", {}):
                hour_scores[hour].append(data["metrics"][metric])

        # Find best hour
        best_hour = None
        best_score = -1.0

        for hour, scores in hour_scores.items():
            if scores:
                avg = sum(scores) / len(scores)
                if avg > best_score:
                    best_score = avg
                    best_hour = hour

        return best_hour

    def suggest_schedule(
        self,
        action: str,
        recurrence: RecurrencePattern = RecurrencePattern.DAILY,
    ) -> Optional[ScheduledTask]:
        """Suggest a scheduled task based on patterns.

        Args:
            action: Action name
            recurrence: Desired recurrence pattern

        Returns:
            Suggested scheduled task or None
        """
        optimal_hour = self.get_optimal_time(action)

        if optimal_hour is None:
            return None

        # Calculate next run at optimal hour
        now = datetime.now(timezone.utc)
        next_run = now.replace(hour=optimal_hour, minute=0, second=0, microsecond=0)
        if next_run <= now:
            next_run += timedelta(days=1)

        return ScheduledTask(
            task_id=str(uuid4()),
            name=f"learned_{action}",
            payload={"action": action, "learned": True},
            next_run=next_run,
            recurrence=recurrence,
        )

    def clear(self) -> None:
        """Clear pattern history."""
        self._patterns.clear()
        self._action_history.clear()
