"""Tests for Scheduler module."""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from src.runtime.event import EventPriority
from src.runtime.queue import EventQueue
from src.runtime.scheduler import PatternLearner, RecurrencePattern, ScheduledTask, Scheduler


class TestScheduledTask:
    """Tests for ScheduledTask dataclass."""

    def test_task_creation(self):
        """Test creating a scheduled task."""
        task = ScheduledTask(
            task_id="task-123",
            name="test_task",
            payload={"key": "value"},
            next_run=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        assert task.task_id == "task-123"
        assert task.name == "test_task"
        assert task.enabled is True
        assert task.run_count == 0

    def test_is_due(self):
        """Test checking if task is due."""
        # Future task
        future_task = ScheduledTask(
            task_id="future",
            name="future",
            next_run=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert not future_task.is_due()

        # Past task
        past_task = ScheduledTask(
            task_id="past",
            name="past",
            next_run=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert past_task.is_due()

        # Disabled task
        disabled_task = ScheduledTask(
            task_id="disabled",
            name="disabled",
            next_run=datetime.now(timezone.utc) - timedelta(hours=1),
            enabled=False,
        )
        assert not disabled_task.is_due()

    def test_calculate_next_run_once(self):
        """Test next run calculation for one-time task."""
        task = ScheduledTask(
            task_id="once",
            name="once",
            recurrence=RecurrencePattern.ONCE,
        )

        # One-time task should not have next run
        assert task.calculate_next_run() is None

    def test_calculate_next_run_hourly(self):
        """Test next run calculation for hourly task."""
        now = datetime.now(timezone.utc)
        task = ScheduledTask(
            task_id="hourly",
            name="hourly",
            next_run=now,
            recurrence=RecurrencePattern.HOURLY,
        )

        next_run = task.calculate_next_run()
        assert next_run is not None
        assert (next_run - now).total_seconds() == 3600

    def test_calculate_next_run_daily(self):
        """Test next run calculation for daily task."""
        now = datetime.now(timezone.utc)
        task = ScheduledTask(
            task_id="daily",
            name="daily",
            next_run=now,
            recurrence=RecurrencePattern.DAILY,
        )

        next_run = task.calculate_next_run()
        assert next_run is not None
        assert (next_run - now).total_seconds() == 86400

    def test_calculate_next_run_custom(self):
        """Test next run calculation for custom interval."""
        now = datetime.now(timezone.utc)
        task = ScheduledTask(
            task_id="custom",
            name="custom",
            next_run=now,
            recurrence=RecurrencePattern.CUSTOM,
            custom_interval=timedelta(minutes=30),
        )

        next_run = task.calculate_next_run()
        assert next_run is not None
        assert (next_run - now).total_seconds() == 1800

    def test_mark_run(self):
        """Test marking task as run."""
        task = ScheduledTask(
            task_id="test",
            name="test",
            next_run=datetime.now(timezone.utc),
            recurrence=RecurrencePattern.HOURLY,
        )

        initial_next_run = task.next_run
        task.mark_run()

        assert task.run_count == 1
        assert task.last_run is not None
        assert task.next_run > initial_next_run

    def test_max_runs(self):
        """Test max runs limit."""
        task = ScheduledTask(
            task_id="limited",
            name="limited",
            next_run=datetime.now(timezone.utc) - timedelta(hours=1),
            max_runs=2,
            run_count=2,
        )

        # Task with max runs reached should not be due
        assert not task.is_due()

        # Should not calculate next run
        assert task.calculate_next_run() is None

    def test_to_dict_from_dict(self):
        """Test serialization round-trip."""
        original = ScheduledTask(
            task_id="test",
            name="test_task",
            payload={"key": "value"},
            next_run=datetime.now(timezone.utc),
            recurrence=RecurrencePattern.DAILY,
            priority=EventPriority.HIGH,
        )

        data = original.to_dict()
        restored = ScheduledTask.from_dict(data)

        assert restored.task_id == original.task_id
        assert restored.name == original.name
        assert restored.recurrence == original.recurrence
        assert restored.priority == original.priority


class TestScheduler:
    """Tests for Scheduler class."""

    def test_scheduler_creation(self):
        """Test creating a scheduler."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue)
        assert scheduler is not None
        assert not scheduler.is_running

    def test_schedule_task(self):
        """Test scheduling a task."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue)

        task = scheduler.schedule(
            name="test_task",
            when=datetime.now(timezone.utc) + timedelta(hours=1),
            payload={"key": "value"},
        )

        assert task.name == "test_task"
        assert task.task_id is not None
        assert scheduler.get_task(task.task_id) is not None

    def test_schedule_with_timedelta(self):
        """Test scheduling with timedelta."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue)

        task = scheduler.schedule(
            name="future_task",
            when=timedelta(hours=2),
        )

        # Next run should be approximately 2 hours from now
        time_until = (task.next_run - datetime.now(timezone.utc)).total_seconds()
        assert 7190 < time_until < 7210  # Approximately 2 hours

    def test_schedule_recurring(self):
        """Test scheduling a recurring task."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue)

        task = scheduler.schedule_recurring(
            name="recurring_task",
            interval=timedelta(minutes=30),
            start_immediately=True,
        )

        assert task.recurrence == RecurrencePattern.CUSTOM
        assert task.custom_interval == timedelta(minutes=30)

    def test_unschedule(self):
        """Test unscheduling a task."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue)

        task = scheduler.schedule(
            name="to_remove",
            when=timedelta(hours=1),
        )

        assert scheduler.unschedule(task.task_id)
        assert scheduler.get_task(task.task_id) is None
        assert not scheduler.unschedule("nonexistent")

    def test_enable_disable(self):
        """Test enabling and disabling tasks."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue)

        task = scheduler.schedule(
            name="toggleable",
            when=timedelta(hours=1),
        )

        assert task.enabled

        scheduler.disable(task.task_id)
        disabled_task = scheduler.get_task(task.task_id)
        assert disabled_task is not None and not disabled_task.enabled

        scheduler.enable(task.task_id)
        enabled_task = scheduler.get_task(task.task_id)
        assert enabled_task is not None and enabled_task.enabled

    def test_list_tasks(self):
        """Test listing scheduled tasks."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue)

        # Schedule multiple tasks
        scheduler.schedule("task1", when=timedelta(hours=1))
        scheduler.schedule("task2", when=timedelta(hours=2))
        disabled = scheduler.schedule("task3", when=timedelta(hours=3))
        scheduler.disable(disabled.task_id)

        all_tasks = scheduler.list_tasks()
        assert len(all_tasks) == 3

        enabled_tasks = scheduler.list_tasks(enabled_only=True)
        assert len(enabled_tasks) == 2

    def test_list_due_tasks(self):
        """Test listing due tasks."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue)

        # Past task (due)
        scheduler.schedule("past", when=timedelta(seconds=-10))
        # Future task (not due)
        scheduler.schedule("future", when=timedelta(hours=1))

        due = scheduler.list_tasks(due_only=True)
        assert len(due) == 1
        assert due[0].name == "past"

    @pytest.mark.asyncio
    async def test_scheduler_start_stop(self):
        """Test starting and stopping scheduler."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue, check_interval=0.1)

        await scheduler.start()
        assert scheduler.is_running

        await scheduler.stop()
        assert not scheduler.is_running

    @pytest.mark.asyncio
    async def test_due_task_creates_event(self):
        """Test that due tasks create events."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue, check_interval=0.1)

        # Schedule task that's immediately due
        scheduler.schedule(
            name="immediate",
            when=timedelta(seconds=-1),
            payload={"test": True},
        )

        await scheduler.start()

        # Wait for scheduler to process
        await asyncio.sleep(0.3)

        await scheduler.stop()

        # Should have an event in queue
        assert not queue.empty()
        event = await queue.get()
        assert event.payload["task_name"] == "immediate"

    def test_get_statistics(self):
        """Test getting scheduler statistics."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue)

        scheduler.schedule("task1", when=timedelta(hours=1))
        scheduler.schedule("task2", when=timedelta(hours=2))

        stats = scheduler.get_statistics()

        assert stats.total_tasks == 2
        assert stats.enabled_tasks == 2
        assert stats.next_task_at is not None

    def test_clear(self):
        """Test clearing all tasks."""
        queue = EventQueue()
        scheduler = Scheduler(event_queue=queue)

        scheduler.schedule("task1", when=timedelta(hours=1))
        scheduler.schedule("task2", when=timedelta(hours=2))

        cleared = scheduler.clear()
        assert cleared == 2
        assert len(scheduler.list_tasks()) == 0


class TestPatternLearner:
    """Tests for PatternLearner class."""

    def test_learner_creation(self):
        """Test creating a pattern learner."""
        learner = PatternLearner()
        assert learner is not None

    def test_record_action(self):
        """Test recording action for learning."""
        learner = PatternLearner()

        learner.record_action(
            action="post_tweet",
            timestamp=datetime.now(timezone.utc),
            success=True,
            metrics={"engagement": 100},
        )

        assert len(learner._action_history) == 1

    def test_get_optimal_time_insufficient_data(self):
        """Test optimal time with insufficient data."""
        learner = PatternLearner()

        # Only a few data points
        for i in range(5):
            learner.record_action(
                action="search",
                timestamp=datetime.now(timezone.utc),
                success=True,
            )

        # Should return None (need at least 10 data points)
        assert learner.get_optimal_time("search") is None

    def test_get_optimal_time_with_data(self):
        """Test optimal time with sufficient data."""
        learner = PatternLearner()

        # Record many actions at different hours
        for hour in range(24):
            # More successes at hour 9
            success = hour == 9
            for _ in range(2 if hour == 9 else 1):
                timestamp = datetime.now(timezone.utc).replace(hour=hour)
                learner.record_action(
                    action="post",
                    timestamp=timestamp,
                    success=success,
                )

        optimal = learner.get_optimal_time("post")
        assert optimal == 9

    def test_clear(self):
        """Test clearing pattern history."""
        learner = PatternLearner()

        learner.record_action(
            action="test",
            timestamp=datetime.now(timezone.utc),
            success=True,
        )

        learner.clear()
        assert len(learner._action_history) == 0
