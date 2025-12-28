"""Tests for Goal module."""

from datetime import datetime, timedelta, timezone

from src.planning.goal import Goal, GoalDecomposition, GoalPriority, GoalRegistry, GoalStatus


class TestGoalStatus:
    """Tests for GoalStatus enum."""

    def test_goal_status_values(self):
        """Test all goal status values exist."""
        assert GoalStatus.PENDING.value == "pending"
        assert GoalStatus.IN_PROGRESS.value == "in_progress"
        assert GoalStatus.COMPLETED.value == "completed"
        assert GoalStatus.FAILED.value == "failed"
        assert GoalStatus.BLOCKED.value == "blocked"
        assert GoalStatus.CANCELLED.value == "cancelled"


class TestGoalPriority:
    """Tests for GoalPriority enum."""

    def test_goal_priority_values(self):
        """Test all goal priority values exist."""
        assert GoalPriority.CRITICAL.value == "critical"
        assert GoalPriority.HIGH.value == "high"
        assert GoalPriority.MEDIUM.value == "medium"
        assert GoalPriority.LOW.value == "low"
        assert GoalPriority.OPTIONAL.value == "optional"


class TestGoal:
    """Tests for Goal dataclass."""

    def test_goal_creation(self):
        """Test creating a goal."""
        goal = Goal(
            id="test-001",
            description="Test goal",
            success_criteria=["Criterion 1", "Criterion 2"],
            priority=GoalPriority.HIGH,
        )

        assert goal.id == "test-001"
        assert goal.description == "Test goal"
        assert len(goal.success_criteria) == 2
        assert goal.priority == GoalPriority.HIGH
        assert goal.status == GoalStatus.PENDING
        assert goal.progress == 0.0

    def test_goal_create_factory(self):
        """Test Goal.create factory method."""
        goal = Goal.create(
            description="Factory goal",
            success_criteria=["Done"],
            priority=GoalPriority.LOW,
        )

        assert goal.id is not None
        assert len(goal.id) == 36  # UUID format
        assert goal.description == "Factory goal"

    def test_goal_start(self):
        """Test starting a goal."""
        goal = Goal.create(description="Start test")
        assert goal.status == GoalStatus.PENDING
        assert goal.started_at is None

        goal.start()

        assert goal.status == GoalStatus.IN_PROGRESS
        assert goal.started_at is not None

    def test_goal_complete(self):
        """Test completing a goal."""
        goal = Goal.create(description="Complete test")
        goal.start()
        goal.complete()

        assert goal.status == GoalStatus.COMPLETED
        assert goal.completed_at is not None
        assert goal.progress == 1.0

    def test_goal_fail(self):
        """Test failing a goal."""
        goal = Goal.create(description="Fail test")
        goal.start()
        goal.fail("Something went wrong")

        assert goal.status == GoalStatus.FAILED
        assert goal.failure_reason == "Something went wrong"
        assert goal.completed_at is not None

    def test_goal_block(self):
        """Test blocking a goal."""
        goal = Goal.create(description="Block test")
        goal.block("Waiting on dependency")

        assert goal.status == GoalStatus.BLOCKED
        assert goal.metadata["block_reason"] == "Waiting on dependency"

    def test_goal_retry(self):
        """Test retrying a goal."""
        goal = Goal.create(description="Retry test")
        goal.start()
        goal.fail("First attempt failed")

        assert goal.can_retry() is True
        result = goal.retry()

        assert result is True
        assert goal.status == GoalStatus.IN_PROGRESS
        assert goal.retry_count == 1
        assert goal.failure_reason is None

    def test_goal_max_retries(self):
        """Test max retry limit."""
        goal = Goal.create(description="Max retry test")
        goal.max_retries = 2

        for i in range(3):
            goal.start()
            goal.fail(f"Attempt {i + 1} failed")
            if goal.can_retry():
                goal.retry()

        assert goal.retry_count == 2
        assert goal.can_retry() is False

    def test_goal_update_progress(self):
        """Test updating goal progress."""
        goal = Goal.create(description="Progress test")

        goal.update_progress(0.5)
        assert goal.progress == 0.5

        # Test clamping
        goal.update_progress(1.5)
        assert goal.progress == 1.0

        goal.update_progress(-0.5)
        assert goal.progress == 0.0

    def test_goal_is_terminal(self):
        """Test is_terminal property."""
        goal = Goal.create(description="Terminal test")

        assert goal.is_terminal is False

        goal.complete()
        assert goal.is_terminal is True

    def test_goal_is_active(self):
        """Test is_active property."""
        goal = Goal.create(description="Active test")

        assert goal.is_active is False

        goal.start()
        assert goal.is_active is True

        goal.complete()
        assert goal.is_active is False

    def test_goal_is_overdue(self):
        """Test is_overdue property."""
        goal = Goal.create(
            description="Overdue test",
            deadline=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        assert goal.is_overdue is True

        goal_future = Goal.create(
            description="Future test",
            deadline=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert goal_future.is_overdue is False

    def test_goal_subgoals(self):
        """Test subgoal management."""
        goal = Goal.create(description="Parent goal")

        goal.add_subgoal("sub-1")
        goal.add_subgoal("sub-2")

        assert len(goal.subgoal_ids) == 2
        assert "sub-1" in goal.subgoal_ids

        goal.remove_subgoal("sub-1")
        assert len(goal.subgoal_ids) == 1
        assert "sub-1" not in goal.subgoal_ids

    def test_goal_to_dict(self):
        """Test converting goal to dictionary."""
        goal = Goal.create(
            description="Dict test",
            success_criteria=["Done"],
            priority=GoalPriority.HIGH,
        )

        result = goal.to_dict()

        assert result["description"] == "Dict test"
        assert result["priority"] == "high"
        assert result["status"] == "pending"
        assert "created_at" in result

    def test_goal_from_dict(self):
        """Test creating goal from dictionary."""
        data = {
            "id": "from-dict-001",
            "description": "From dict",
            "success_criteria": ["Test"],
            "priority": "high",
            "status": "in_progress",
            "progress": 0.5,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        goal = Goal.from_dict(data)

        assert goal.id == "from-dict-001"
        assert goal.description == "From dict"
        assert goal.priority == GoalPriority.HIGH
        assert goal.status == GoalStatus.IN_PROGRESS

    def test_goal_str(self):
        """Test goal string representation."""
        goal = Goal.create(description="String test goal representation")
        result = str(goal)

        assert "Goal(" in result
        assert "String test goal" in result
        assert "pending" in result


class TestGoalDecomposition:
    """Tests for GoalDecomposition dataclass."""

    def test_decomposition_creation(self):
        """Test creating a goal decomposition."""
        original = Goal.create(description="Original goal")
        subgoals = [
            Goal.create(description="Subgoal 1"),
            Goal.create(description="Subgoal 2"),
        ]

        decomposition = GoalDecomposition(
            original_goal=original,
            subgoals=subgoals,
            reasoning="Broke it down",
            confidence=0.9,
            approach="Sequential",
        )

        assert decomposition.original_goal == original
        assert len(decomposition.subgoals) == 2
        assert decomposition.confidence == 0.9

    def test_decomposition_to_dict(self):
        """Test converting decomposition to dictionary."""
        original = Goal.create(description="Original")
        decomposition = GoalDecomposition(
            original_goal=original,
            subgoals=[],
            reasoning="Test",
            confidence=0.8,
            approach="Direct",
        )

        result = decomposition.to_dict()

        assert "original_goal" in result
        assert "subgoals" in result
        assert result["confidence"] == 0.8


class TestGoalRegistry:
    """Tests for GoalRegistry class."""

    def test_registry_add_and_get(self):
        """Test adding and getting goals."""
        registry = GoalRegistry()
        goal = Goal.create(description="Registry test")

        registry.add(goal)

        assert goal.id in registry
        assert registry.get(goal.id) == goal

    def test_registry_remove(self):
        """Test removing goals."""
        registry = GoalRegistry()
        goal = Goal.create(description="Remove test")

        registry.add(goal)
        removed = registry.remove(goal.id)

        assert removed == goal
        assert goal.id not in registry

    def test_registry_get_all(self):
        """Test getting all goals."""
        registry = GoalRegistry()
        goal1 = Goal.create(description="Goal 1")
        goal2 = Goal.create(description="Goal 2")

        registry.add(goal1)
        registry.add(goal2)

        all_goals = registry.get_all()
        assert len(all_goals) == 2

    def test_registry_get_by_status(self):
        """Test filtering goals by status."""
        registry = GoalRegistry()
        pending = Goal.create(description="Pending")
        active = Goal.create(description="Active")
        active.start()

        registry.add(pending)
        registry.add(active)

        pending_goals = registry.get_by_status(GoalStatus.PENDING)
        assert len(pending_goals) == 1
        assert pending_goals[0] == pending

        active_goals = registry.get_active()
        assert len(active_goals) == 1
        assert active_goals[0] == active

    def test_registry_get_children(self):
        """Test getting child goals."""
        registry = GoalRegistry()
        parent = Goal.create(description="Parent")
        child1 = Goal.create(description="Child 1", parent_id=parent.id)
        child2 = Goal.create(description="Child 2", parent_id=parent.id)
        other = Goal.create(description="Other")

        registry.add(parent)
        registry.add(child1)
        registry.add(child2)
        registry.add(other)

        children = registry.get_children(parent.id)
        assert len(children) == 2

    def test_registry_get_root_goals(self):
        """Test getting root goals."""
        registry = GoalRegistry()
        root = Goal.create(description="Root")
        child = Goal.create(description="Child", parent_id=root.id)

        registry.add(root)
        registry.add(child)

        roots = registry.get_root_goals()
        assert len(roots) == 1
        assert roots[0] == root

    def test_registry_get_overdue(self):
        """Test getting overdue goals."""
        registry = GoalRegistry()
        overdue = Goal.create(
            description="Overdue",
            deadline=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        overdue.start()  # Make it non-terminal

        on_time = Goal.create(
            description="On time",
            deadline=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        registry.add(overdue)
        registry.add(on_time)

        overdue_goals = registry.get_overdue()
        assert len(overdue_goals) == 1
        assert overdue_goals[0] == overdue

    def test_registry_clear(self):
        """Test clearing the registry."""
        registry = GoalRegistry()
        registry.add(Goal.create(description="Goal 1"))
        registry.add(Goal.create(description="Goal 2"))

        registry.clear()

        assert len(registry) == 0

    def test_registry_len(self):
        """Test registry length."""
        registry = GoalRegistry()
        assert len(registry) == 0

        registry.add(Goal.create(description="Goal"))
        assert len(registry) == 1
