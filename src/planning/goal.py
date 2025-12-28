"""Goal representation for hierarchical planning.

Provides data structures for representing goals, sub-goals,
and goal status tracking in the planning system.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class GoalStatus(str, Enum):
    """Status of a goal in the planning system."""

    PENDING = "pending"  # Goal not yet started
    IN_PROGRESS = "in_progress"  # Goal is being worked on
    COMPLETED = "completed"  # Goal successfully achieved
    FAILED = "failed"  # Goal could not be achieved
    BLOCKED = "blocked"  # Goal is waiting on dependencies
    CANCELLED = "cancelled"  # Goal was cancelled


class GoalPriority(str, Enum):
    """Priority levels for goals."""

    CRITICAL = "critical"  # Must be done immediately
    HIGH = "high"  # Should be done soon
    MEDIUM = "medium"  # Normal priority
    LOW = "low"  # Can be deferred
    OPTIONAL = "optional"  # Nice to have


@dataclass
class Goal:
    """Represents a goal in the hierarchical planning system.

    Goals can have sub-goals, forming a tree structure.
    Each goal tracks its status, progress, and success criteria.
    """

    id: str
    description: str
    success_criteria: List[str]
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.PENDING
    deadline: Optional[datetime] = None
    parent_id: Optional[str] = None
    subgoal_ids: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    failure_reason: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3

    @classmethod
    def create(
        cls,
        description: str,
        success_criteria: Optional[List[str]] = None,
        priority: GoalPriority = GoalPriority.MEDIUM,
        deadline: Optional[datetime] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "Goal":
        """Create a new goal with a generated ID.

        Args:
            description: Goal description
            success_criteria: List of criteria for success
            priority: Goal priority level
            deadline: Optional deadline
            parent_id: Optional parent goal ID
            metadata: Optional metadata

        Returns:
            New Goal instance
        """
        return cls(
            id=str(uuid.uuid4()),
            description=description,
            success_criteria=success_criteria or [],
            priority=priority,
            deadline=deadline,
            parent_id=parent_id,
            metadata=metadata or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert goal to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "description": self.description,
            "success_criteria": self.success_criteria,
            "priority": self.priority.value,
            "status": self.status.value,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "parent_id": self.parent_id,
            "subgoal_ids": self.subgoal_ids,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "metadata": self.metadata,
            "failure_reason": self.failure_reason,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Goal":
        """Create Goal from dictionary.

        Args:
            data: Dictionary with goal data

        Returns:
            Goal instance
        """
        return cls(
            id=data["id"],
            description=data["description"],
            success_criteria=data.get("success_criteria", []),
            priority=GoalPriority(data.get("priority", "medium")),
            status=GoalStatus(data.get("status", "pending")),
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            parent_id=data.get("parent_id"),
            subgoal_ids=data.get("subgoal_ids", []),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.now(timezone.utc)),
            started_at=datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None,
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            progress=data.get("progress", 0.0),
            metadata=data.get("metadata", {}),
            failure_reason=data.get("failure_reason"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )

    def start(self) -> None:
        """Mark goal as started."""
        self.status = GoalStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc)

    def complete(self) -> None:
        """Mark goal as completed."""
        self.status = GoalStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
        self.progress = 1.0

    def fail(self, reason: str) -> None:
        """Mark goal as failed.

        Args:
            reason: Reason for failure
        """
        self.status = GoalStatus.FAILED
        self.failure_reason = reason
        self.completed_at = datetime.now(timezone.utc)

    def block(self, reason: Optional[str] = None) -> None:
        """Mark goal as blocked.

        Args:
            reason: Optional reason for blocking
        """
        self.status = GoalStatus.BLOCKED
        if reason:
            self.metadata["block_reason"] = reason

    def can_retry(self) -> bool:
        """Check if goal can be retried.

        Returns:
            True if retry is possible
        """
        return self.retry_count < self.max_retries

    def retry(self) -> bool:
        """Attempt to retry the goal.

        Returns:
            True if retry was initiated, False if max retries exceeded
        """
        if not self.can_retry():
            return False
        self.retry_count += 1
        self.status = GoalStatus.IN_PROGRESS
        self.failure_reason = None
        return True

    def update_progress(self, progress: float) -> None:
        """Update goal progress.

        Args:
            progress: New progress value (0.0 to 1.0)
        """
        self.progress = max(0.0, min(1.0, progress))

    @property
    def is_terminal(self) -> bool:
        """Check if goal is in a terminal state.

        Returns:
            True if goal is completed, failed, or cancelled
        """
        return self.status in (GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.CANCELLED)

    @property
    def is_active(self) -> bool:
        """Check if goal is actively being worked on.

        Returns:
            True if goal is in progress
        """
        return self.status == GoalStatus.IN_PROGRESS

    @property
    def is_overdue(self) -> bool:
        """Check if goal is past its deadline.

        Returns:
            True if deadline has passed
        """
        if not self.deadline:
            return False
        return datetime.now(timezone.utc) > self.deadline

    def add_subgoal(self, subgoal_id: str) -> None:
        """Add a subgoal to this goal.

        Args:
            subgoal_id: ID of the subgoal
        """
        if subgoal_id not in self.subgoal_ids:
            self.subgoal_ids.append(subgoal_id)

    def remove_subgoal(self, subgoal_id: str) -> None:
        """Remove a subgoal from this goal.

        Args:
            subgoal_id: ID of the subgoal
        """
        if subgoal_id in self.subgoal_ids:
            self.subgoal_ids.remove(subgoal_id)

    def __str__(self) -> str:
        """String representation of goal."""
        return f"Goal({self.id[:8]}): {self.description[:50]} [{self.status.value}]"


@dataclass
class GoalDecomposition:
    """Result of decomposing a goal into sub-goals.

    Contains the original goal, generated sub-goals,
    and metadata about the decomposition process.
    """

    original_goal: Goal
    subgoals: List[Goal]
    reasoning: str  # Explanation of the decomposition
    confidence: float  # Confidence in the decomposition (0.0 to 1.0)
    approach: str  # Description of the approach taken
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "original_goal": self.original_goal.to_dict(),
            "subgoals": [g.to_dict() for g in self.subgoals],
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "approach": self.approach,
            "created_at": self.created_at.isoformat(),
        }


class GoalRegistry:
    """Registry for tracking all goals in the system.

    Provides methods for adding, retrieving, and querying goals.
    """

    def __init__(self) -> None:
        """Initialize the goal registry."""
        self._goals: Dict[str, Goal] = {}

    def add(self, goal: Goal) -> None:
        """Add a goal to the registry.

        Args:
            goal: Goal to add
        """
        self._goals[goal.id] = goal

    def get(self, goal_id: str) -> Optional[Goal]:
        """Get a goal by ID.

        Args:
            goal_id: ID of the goal

        Returns:
            Goal if found, None otherwise
        """
        return self._goals.get(goal_id)

    def remove(self, goal_id: str) -> Optional[Goal]:
        """Remove a goal from the registry.

        Args:
            goal_id: ID of the goal

        Returns:
            Removed goal if found
        """
        return self._goals.pop(goal_id, None)

    def get_all(self) -> List[Goal]:
        """Get all goals.

        Returns:
            List of all goals
        """
        return list(self._goals.values())

    def get_by_status(self, status: GoalStatus) -> List[Goal]:
        """Get goals by status.

        Args:
            status: Status to filter by

        Returns:
            List of matching goals
        """
        return [g for g in self._goals.values() if g.status == status]

    def get_active(self) -> List[Goal]:
        """Get all active goals.

        Returns:
            List of active goals
        """
        return self.get_by_status(GoalStatus.IN_PROGRESS)

    def get_pending(self) -> List[Goal]:
        """Get all pending goals.

        Returns:
            List of pending goals
        """
        return self.get_by_status(GoalStatus.PENDING)

    def get_children(self, goal_id: str) -> List[Goal]:
        """Get child goals of a parent goal.

        Args:
            goal_id: Parent goal ID

        Returns:
            List of child goals
        """
        return [g for g in self._goals.values() if g.parent_id == goal_id]

    def get_root_goals(self) -> List[Goal]:
        """Get all root goals (goals without parents).

        Returns:
            List of root goals
        """
        return [g for g in self._goals.values() if g.parent_id is None]

    def get_overdue(self) -> List[Goal]:
        """Get all overdue goals.

        Returns:
            List of overdue goals
        """
        return [g for g in self._goals.values() if g.is_overdue and not g.is_terminal]

    def clear(self) -> None:
        """Clear all goals from the registry."""
        self._goals.clear()

    def __len__(self) -> int:
        """Get number of goals in registry."""
        return len(self._goals)

    def __contains__(self, goal_id: str) -> bool:
        """Check if goal is in registry."""
        return goal_id in self._goals
