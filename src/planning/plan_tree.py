"""Plan Tree structure for hierarchical planning.

Provides a tree-based plan representation that tracks
goals, actions, and execution progress.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from src.planning.goal import Goal, GoalStatus


class NodeStatus(str, Enum):
    """Status of a plan node."""

    PENDING = "pending"  # Not yet started
    ACTIVE = "active"  # Currently being executed
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"  # Execution failed
    SKIPPED = "skipped"  # Skipped (e.g., due to replanning)


@dataclass
class ActionStep:
    """Represents a single action step in a plan.

    Actions are the lowest-level executable units in the plan tree.
    They correspond to agent actions or MCP tool calls.
    """

    id: str
    action_name: str  # e.g., "search_tavily" or "mcp:fetch"
    arguments: Dict[str, Any] = field(default_factory=dict)
    description: Optional[str] = None
    status: NodeStatus = NodeStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_duration_seconds: float = 30.0

    @classmethod
    def create(
        cls,
        action_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        estimated_duration_seconds: float = 30.0,
    ) -> "ActionStep":
        """Create a new action step with a generated ID.

        Args:
            action_name: Name of the action to execute
            arguments: Arguments for the action
            description: Human-readable description
            estimated_duration_seconds: Estimated time to complete

        Returns:
            New ActionStep instance
        """
        return cls(
            id=str(uuid.uuid4()),
            action_name=action_name,
            arguments=arguments or {},
            description=description,
            estimated_duration_seconds=estimated_duration_seconds,
        )

    def start(self) -> None:
        """Mark action as started."""
        self.status = NodeStatus.ACTIVE
        self.started_at = datetime.now(timezone.utc)

    def complete(self, result: Any = None) -> None:
        """Mark action as completed successfully.

        Args:
            result: Result from the action execution
        """
        self.status = NodeStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.now(timezone.utc)

    def fail(self, error: str) -> None:
        """Mark action as failed.

        Args:
            error: Error message describing the failure
        """
        self.status = NodeStatus.FAILED
        self.error = error
        self.completed_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "action_name": self.action_name,
            "arguments": self.arguments,
            "description": self.description,
            "status": self.status.value,
            "result": str(self.result) if self.result else None,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "estimated_duration_seconds": self.estimated_duration_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionStep":
        """Create ActionStep from dictionary.

        Args:
            data: Dictionary with action data

        Returns:
            ActionStep instance
        """
        return cls(
            id=data["id"],
            action_name=data["action_name"],
            arguments=data.get("arguments", {}),
            description=data.get("description"),
            status=NodeStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error"),
            started_at=datetime.fromisoformat(data["started_at"])
            if data.get("started_at")
            else None,
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            estimated_duration_seconds=data.get("estimated_duration_seconds", 30.0),
        )


@dataclass
class PlanNode:
    """Represents a node in the plan tree.

    Each node has a goal, optional action sequence,
    and child nodes for sub-goals.
    """

    id: str
    goal: Goal
    actions: List[ActionStep] = field(default_factory=list)
    children: List["PlanNode"] = field(default_factory=list)
    parent: Optional["PlanNode"] = None
    confidence: float = 1.0  # Confidence in this plan branch (0.0 to 1.0)
    estimated_steps: int = 0
    approach: str = ""  # Description of the approach taken
    reasoning: str = ""  # Reasoning behind this plan branch
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        goal: Goal,
        actions: Optional[List[ActionStep]] = None,
        confidence: float = 1.0,
        approach: str = "",
        reasoning: str = "",
        parent: Optional["PlanNode"] = None,
    ) -> "PlanNode":
        """Create a new plan node with a generated ID.

        Args:
            goal: Goal for this node
            actions: Action sequence for this node
            confidence: Confidence in this plan branch
            approach: Description of the approach
            reasoning: Reasoning behind this plan
            parent: Parent node

        Returns:
            New PlanNode instance
        """
        actions = actions or []
        return cls(
            id=str(uuid.uuid4()),
            goal=goal,
            actions=actions,
            confidence=confidence,
            approach=approach,
            reasoning=reasoning,
            parent=parent,
            estimated_steps=len(actions),
        )

    def add_child(self, child: "PlanNode") -> None:
        """Add a child node.

        Args:
            child: Child plan node to add
        """
        child.parent = self
        self.children.append(child)
        self.goal.add_subgoal(child.goal.id)

    def remove_child(self, child_id: str) -> Optional["PlanNode"]:
        """Remove a child node by ID.

        Args:
            child_id: ID of the child to remove

        Returns:
            Removed child if found
        """
        for i, child in enumerate(self.children):
            if child.id == child_id:
                removed = self.children.pop(i)
                self.goal.remove_subgoal(removed.goal.id)
                return removed
        return None

    def add_action(self, action: ActionStep) -> None:
        """Add an action step.

        Args:
            action: Action step to add
        """
        self.actions.append(action)
        self.estimated_steps = len(self.actions)

    def get_next_action(self) -> Optional[ActionStep]:
        """Get the next pending action.

        Returns:
            Next action to execute, or None if all done
        """
        for action in self.actions:
            if action.status == NodeStatus.PENDING:
                return action
        return None

    def get_current_action(self) -> Optional[ActionStep]:
        """Get the currently active action.

        Returns:
            Active action, or None if none active
        """
        for action in self.actions:
            if action.status == NodeStatus.ACTIVE:
                return action
        return None

    @property
    def status(self) -> NodeStatus:
        """Get the overall status of this node.

        Returns:
            Node status based on goal and action states
        """
        if self.goal.status == GoalStatus.COMPLETED:
            return NodeStatus.COMPLETED
        if self.goal.status == GoalStatus.FAILED:
            return NodeStatus.FAILED
        if self.goal.status == GoalStatus.IN_PROGRESS:
            return NodeStatus.ACTIVE
        return NodeStatus.PENDING

    @property
    def progress(self) -> float:
        """Calculate progress based on completed actions.

        Returns:
            Progress as a float between 0.0 and 1.0
        """
        if not self.actions:
            # If no actions, base progress on children
            if not self.children:
                return 0.0 if not self.goal.is_terminal else 1.0
            return sum(c.progress for c in self.children) / len(self.children)

        completed = sum(1 for a in self.actions if a.status == NodeStatus.COMPLETED)
        return completed / len(self.actions)

    @property
    def is_leaf(self) -> bool:
        """Check if this is a leaf node (no children).

        Returns:
            True if no children
        """
        return len(self.children) == 0

    @property
    def depth(self) -> int:
        """Get the depth of this node in the tree.

        Returns:
            Depth (0 for root)
        """
        if self.parent is None:
            return 0
        return self.parent.depth + 1

    def get_ancestors(self) -> List["PlanNode"]:
        """Get all ancestor nodes.

        Returns:
            List of ancestors from parent to root
        """
        ancestors = []
        node = self.parent
        while node is not None:
            ancestors.append(node)
            node = node.parent
        return ancestors

    def get_descendants(self) -> List["PlanNode"]:
        """Get all descendant nodes (breadth-first).

        Returns:
            List of all descendants
        """
        descendants = []
        queue = list(self.children)
        while queue:
            node = queue.pop(0)
            descendants.append(node)
            queue.extend(node.children)
        return descendants

    def find_node(self, node_id: str) -> Optional["PlanNode"]:
        """Find a node by ID in this subtree.

        Args:
            node_id: ID of the node to find

        Returns:
            Found node or None
        """
        if self.id == node_id:
            return self
        for child in self.children:
            found = child.find_node(node_id)
            if found:
                return found
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding parent to avoid cycles).

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "goal": self.goal.to_dict(),
            "actions": [a.to_dict() for a in self.actions],
            "children": [c.to_dict() for c in self.children],
            "confidence": self.confidence,
            "estimated_steps": self.estimated_steps,
            "approach": self.approach,
            "reasoning": self.reasoning,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation."""
        return f"PlanNode({self.id[:8]}): {self.goal.description[:40]} [{self.status.value}]"


class PlanTree:
    """Tree structure for hierarchical plans.

    Manages the plan tree, tracks execution progress,
    and provides navigation methods.
    """

    def __init__(self, root: PlanNode):
        """Initialize plan tree with a root node.

        Args:
            root: Root node of the plan tree
        """
        self.root = root
        self._current_node: PlanNode = root
        self._action_history: List[Tuple[str, ActionStep, bool]] = []  # (node_id, action, success)
        self._created_at = datetime.now(timezone.utc)
        self._last_action_at: Optional[datetime] = None

    @property
    def current_node(self) -> PlanNode:
        """Get the current node being executed.

        Returns:
            Current plan node
        """
        return self._current_node

    @current_node.setter
    def current_node(self, node: PlanNode) -> None:
        """Set the current node.

        Args:
            node: New current node
        """
        self._current_node = node

    def get_next_action(self) -> Optional[ActionStep]:
        """Get the next action to execute from the current plan.

        Traverses the tree depth-first to find the next pending action.

        Returns:
            Next action to execute, or None if plan is complete
        """
        # First check current node
        action = self._current_node.get_next_action()
        if action:
            return action

        # If current node has children with pending actions, go deeper
        for child in self._current_node.children:
            if child.status == NodeStatus.PENDING:
                self._current_node = child
                return self.get_next_action()

        # If no actions in current subtree, try siblings
        if self._current_node.parent:
            parent = self._current_node.parent
            for sibling in parent.children:
                if sibling.id != self._current_node.id and sibling.status == NodeStatus.PENDING:
                    self._current_node = sibling
                    return self.get_next_action()

            # Move up to parent
            self._current_node = parent
            return self.get_next_action()

        # No more actions
        return None

    def mark_action_complete(self, action: ActionStep, success: bool, result: Any = None) -> None:
        """Update plan based on action outcome.

        Args:
            action: The completed action
            success: Whether the action succeeded
            result: Result or error from the action
        """
        self._last_action_at = datetime.now(timezone.utc)
        self._action_history.append((self._current_node.id, action, success))

        if success:
            action.complete(result)
        else:
            action.fail(str(result) if result else "Unknown error")

        # Update node and goal progress
        self._update_progress()

    def _update_progress(self) -> None:
        """Update progress for current node and ancestors."""
        node: Optional[PlanNode] = self._current_node

        while node is not None:
            # Update goal progress based on node progress
            node.goal.update_progress(node.progress)

            # Check if node is complete
            if node.progress >= 1.0:
                all_success = all(a.status == NodeStatus.COMPLETED for a in node.actions)
                children_success = all(c.status == NodeStatus.COMPLETED for c in node.children)

                if all_success and children_success:
                    node.goal.complete()
                elif any(a.status == NodeStatus.FAILED for a in node.actions):
                    node.goal.fail("One or more actions failed")

            node = node.parent

    def needs_replanning(self) -> bool:
        """Check if the plan needs to be re-planned.

        Returns:
            True if replanning is needed
        """
        # Check for failed actions
        current_action = self._current_node.get_current_action()
        if current_action and current_action.status == NodeStatus.FAILED:
            return True

        # Check if current goal is blocked or failed
        if self._current_node.goal.status in (GoalStatus.FAILED, GoalStatus.BLOCKED):
            return True

        # Check for too many failures in recent history
        recent_failures = sum(1 for _, _, success in self._action_history[-5:] if not success)
        if recent_failures >= 3:
            return True

        return False

    def get_failure_context(self) -> Dict[str, Any]:
        """Get context about recent failures for replanning.

        Returns:
            Dictionary with failure context
        """
        failed_actions = [
            (node_id, action.to_dict())
            for node_id, action, success in self._action_history
            if not success
        ]

        current_action = self._current_node.get_current_action()
        current_error = current_action.error if current_action else None

        return {
            "current_node_id": self._current_node.id,
            "current_goal": self._current_node.goal.description,
            "current_error": current_error,
            "failed_actions": failed_actions[-5:],  # Last 5 failures
            "total_failures": len(failed_actions),
            "goal_status": self._current_node.goal.status.value,
        }

    def find_node(self, node_id: str) -> Optional[PlanNode]:
        """Find a node by ID anywhere in the tree.

        Args:
            node_id: ID of the node to find

        Returns:
            Found node or None
        """
        return self.root.find_node(node_id)

    def get_active_branch(self) -> List[PlanNode]:
        """Get the current active branch from root to current node.

        Returns:
            List of nodes from root to current
        """
        branch = self._current_node.get_ancestors()
        branch.reverse()
        branch.append(self._current_node)
        return branch

    def get_all_pending_actions(self) -> List[Tuple[PlanNode, ActionStep]]:
        """Get all pending actions in the tree.

        Returns:
            List of (node, action) tuples
        """
        pending = []

        def traverse(node: PlanNode) -> None:
            for action in node.actions:
                if action.status == NodeStatus.PENDING:
                    pending.append((node, action))
            for child in node.children:
                traverse(child)

        traverse(self.root)
        return pending

    @property
    def progress(self) -> float:
        """Get overall plan progress.

        Returns:
            Progress as a float between 0.0 and 1.0
        """
        return self.root.progress

    @property
    def is_complete(self) -> bool:
        """Check if the plan is complete.

        Returns:
            True if all goals are achieved
        """
        return self.root.goal.is_terminal and self.root.goal.status == GoalStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Check if the plan has failed.

        Returns:
            True if the root goal has failed
        """
        return self.root.goal.status == GoalStatus.FAILED

    @property
    def total_steps(self) -> int:
        """Get total number of action steps in the plan.

        Returns:
            Total step count
        """
        total = len(self.root.actions)
        for node in self.root.get_descendants():
            total += len(node.actions)
        return total

    @property
    def completed_steps(self) -> int:
        """Get number of completed action steps.

        Returns:
            Completed step count
        """
        completed = sum(1 for a in self.root.actions if a.status == NodeStatus.COMPLETED)
        for node in self.root.get_descendants():
            completed += sum(1 for a in node.actions if a.status == NodeStatus.COMPLETED)
        return completed

    def get_statistics(self) -> Dict[str, Any]:
        """Get plan execution statistics.

        Returns:
            Dictionary with plan statistics
        """
        all_nodes = [self.root] + self.root.get_descendants()
        all_actions = []
        for node in all_nodes:
            all_actions.extend(node.actions)

        completed = sum(1 for a in all_actions if a.status == NodeStatus.COMPLETED)
        failed = sum(1 for a in all_actions if a.status == NodeStatus.FAILED)
        pending = sum(1 for a in all_actions if a.status == NodeStatus.PENDING)

        return {
            "total_nodes": len(all_nodes),
            "total_actions": len(all_actions),
            "completed_actions": completed,
            "failed_actions": failed,
            "pending_actions": pending,
            "progress": self.progress,
            "is_complete": self.is_complete,
            "is_failed": self.is_failed,
            "created_at": self._created_at.isoformat(),
            "last_action_at": self._last_action_at.isoformat() if self._last_action_at else None,
            "action_history_length": len(self._action_history),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert plan tree to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "root": self.root.to_dict(),
            "current_node_id": self._current_node.id,
            "created_at": self._created_at.isoformat(),
            "last_action_at": self._last_action_at.isoformat() if self._last_action_at else None,
            "statistics": self.get_statistics(),
        }

    def visualize(self, node: Optional[PlanNode] = None, indent: int = 0) -> str:
        """Create a text visualization of the plan tree.

        Args:
            node: Starting node (defaults to root)
            indent: Current indentation level

        Returns:
            String visualization
        """
        if node is None:
            node = self.root

        lines = []
        prefix = "  " * indent

        # Node info
        status_icon = {
            NodeStatus.PENDING: "[ ]",
            NodeStatus.ACTIVE: "[>]",
            NodeStatus.COMPLETED: "[x]",
            NodeStatus.FAILED: "[!]",
            NodeStatus.SKIPPED: "[-]",
        }

        icon = status_icon.get(node.status, "[ ]")
        lines.append(f"{prefix}{icon} {node.goal.description[:50]}")

        # Actions
        for action in node.actions:
            action_icon = status_icon.get(action.status, "[ ]")
            lines.append(f"{prefix}  {action_icon} {action.action_name}")

        # Children
        for child in node.children:
            lines.append(self.visualize(child, indent + 1))

        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation."""
        return f"PlanTree(progress={self.progress:.1%}, steps={self.completed_steps}/{self.total_steps})"
