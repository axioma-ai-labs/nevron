"""Tests for Plan Tree module."""

import pytest

from src.planning.goal import Goal
from src.planning.plan_tree import ActionStep, NodeStatus, PlanNode, PlanTree


class TestNodeStatus:
    """Tests for NodeStatus enum."""

    def test_node_status_values(self):
        """Test all node status values exist."""
        assert NodeStatus.PENDING.value == "pending"
        assert NodeStatus.ACTIVE.value == "active"
        assert NodeStatus.COMPLETED.value == "completed"
        assert NodeStatus.FAILED.value == "failed"
        assert NodeStatus.SKIPPED.value == "skipped"


class TestActionStep:
    """Tests for ActionStep dataclass."""

    def test_action_step_creation(self):
        """Test creating an action step."""
        action = ActionStep(
            id="action-001",
            action_name="search_tavily",
            arguments={"query": "test"},
            description="Search for test",
        )

        assert action.id == "action-001"
        assert action.action_name == "search_tavily"
        assert action.arguments == {"query": "test"}
        assert action.status == NodeStatus.PENDING

    def test_action_step_create_factory(self):
        """Test ActionStep.create factory method."""
        action = ActionStep.create(
            action_name="mcp:fetch",
            arguments={"url": "https://example.com"},
            description="Fetch a page",
            estimated_duration_seconds=60.0,
        )

        assert action.id is not None
        assert action.action_name == "mcp:fetch"
        assert action.estimated_duration_seconds == 60.0

    def test_action_step_start(self):
        """Test starting an action."""
        action = ActionStep.create(action_name="test_action")
        assert action.started_at is None

        action.start()

        assert action.status == NodeStatus.ACTIVE
        assert action.started_at is not None

    def test_action_step_complete(self):
        """Test completing an action."""
        action = ActionStep.create(action_name="test_action")
        action.start()
        action.complete(result={"data": "test"})

        assert action.status == NodeStatus.COMPLETED
        assert action.result == {"data": "test"}
        assert action.completed_at is not None

    def test_action_step_fail(self):
        """Test failing an action."""
        action = ActionStep.create(action_name="test_action")
        action.start()
        action.fail("Connection error")

        assert action.status == NodeStatus.FAILED
        assert action.error == "Connection error"
        assert action.completed_at is not None

    def test_action_step_to_dict(self):
        """Test converting action to dictionary."""
        action = ActionStep.create(
            action_name="search",
            arguments={"q": "test"},
            description="Search test",
        )

        result = action.to_dict()

        assert result["action_name"] == "search"
        assert result["arguments"] == {"q": "test"}
        assert result["status"] == "pending"

    def test_action_step_from_dict(self):
        """Test creating action from dictionary."""
        data = {
            "id": "action-002",
            "action_name": "analyze",
            "arguments": {},
            "description": "Analyze data",
            "status": "completed",
            "result": "success",
        }

        action = ActionStep.from_dict(data)

        assert action.id == "action-002"
        assert action.action_name == "analyze"
        assert action.status == NodeStatus.COMPLETED


class TestPlanNode:
    """Tests for PlanNode dataclass."""

    @pytest.fixture
    def sample_goal(self):
        """Create a sample goal."""
        return Goal.create(
            description="Sample goal",
            success_criteria=["Done"],
        )

    @pytest.fixture
    def sample_actions(self):
        """Create sample actions."""
        return [
            ActionStep.create(action_name="action1"),
            ActionStep.create(action_name="action2"),
        ]

    def test_plan_node_creation(self, sample_goal):
        """Test creating a plan node."""
        node = PlanNode(
            id="node-001",
            goal=sample_goal,
            confidence=0.9,
            approach="Direct approach",
        )

        assert node.id == "node-001"
        assert node.goal == sample_goal
        assert node.confidence == 0.9
        assert len(node.actions) == 0
        assert len(node.children) == 0

    def test_plan_node_create_factory(self, sample_goal, sample_actions):
        """Test PlanNode.create factory method."""
        node = PlanNode.create(
            goal=sample_goal,
            actions=sample_actions,
            confidence=0.85,
            approach="Test approach",
        )

        assert node.id is not None
        assert len(node.actions) == 2
        assert node.estimated_steps == 2

    def test_plan_node_add_child(self, sample_goal):
        """Test adding child nodes."""
        parent = PlanNode.create(goal=sample_goal)
        child_goal = Goal.create(description="Child goal")
        child = PlanNode.create(goal=child_goal)

        parent.add_child(child)

        assert len(parent.children) == 1
        assert child.parent == parent
        assert child.goal.id in parent.goal.subgoal_ids

    def test_plan_node_remove_child(self, sample_goal):
        """Test removing child nodes."""
        parent = PlanNode.create(goal=sample_goal)
        child_goal = Goal.create(description="Child goal")
        child = PlanNode.create(goal=child_goal)

        parent.add_child(child)
        removed = parent.remove_child(child.id)

        assert removed == child
        assert len(parent.children) == 0

    def test_plan_node_add_action(self, sample_goal):
        """Test adding actions."""
        node = PlanNode.create(goal=sample_goal)
        action = ActionStep.create(action_name="new_action")

        node.add_action(action)

        assert len(node.actions) == 1
        assert node.estimated_steps == 1

    def test_plan_node_get_next_action(self, sample_goal, sample_actions):
        """Test getting next pending action."""
        node = PlanNode.create(goal=sample_goal, actions=sample_actions)

        next_action = node.get_next_action()
        assert next_action == sample_actions[0]

        sample_actions[0].complete()
        next_action = node.get_next_action()
        assert next_action == sample_actions[1]

    def test_plan_node_get_current_action(self, sample_goal, sample_actions):
        """Test getting current active action."""
        node = PlanNode.create(goal=sample_goal, actions=sample_actions)

        assert node.get_current_action() is None

        sample_actions[0].start()
        assert node.get_current_action() == sample_actions[0]

    def test_plan_node_status(self, sample_goal):
        """Test node status property."""
        node = PlanNode.create(goal=sample_goal)

        assert node.status == NodeStatus.PENDING

        sample_goal.start()
        assert node.status == NodeStatus.ACTIVE

        sample_goal.complete()
        assert node.status == NodeStatus.COMPLETED

    def test_plan_node_progress(self, sample_goal, sample_actions):
        """Test node progress property."""
        node = PlanNode.create(goal=sample_goal, actions=sample_actions)

        assert node.progress == 0.0

        sample_actions[0].complete()
        assert node.progress == 0.5

        sample_actions[1].complete()
        assert node.progress == 1.0

    def test_plan_node_is_leaf(self, sample_goal):
        """Test is_leaf property."""
        parent = PlanNode.create(goal=sample_goal)
        assert parent.is_leaf is True

        child = PlanNode.create(goal=Goal.create(description="Child"))
        parent.add_child(child)
        assert parent.is_leaf is False

    def test_plan_node_depth(self, sample_goal):
        """Test depth property."""
        root = PlanNode.create(goal=sample_goal)
        assert root.depth == 0

        child = PlanNode.create(goal=Goal.create(description="Child"))
        root.add_child(child)
        assert child.depth == 1

        grandchild = PlanNode.create(goal=Goal.create(description="Grandchild"))
        child.add_child(grandchild)
        assert grandchild.depth == 2

    def test_plan_node_get_ancestors(self, sample_goal):
        """Test getting ancestor nodes."""
        root = PlanNode.create(goal=sample_goal)
        child = PlanNode.create(goal=Goal.create(description="Child"))
        grandchild = PlanNode.create(goal=Goal.create(description="Grandchild"))

        root.add_child(child)
        child.add_child(grandchild)

        ancestors = grandchild.get_ancestors()
        assert len(ancestors) == 2
        assert ancestors[0] == child
        assert ancestors[1] == root

    def test_plan_node_get_descendants(self, sample_goal):
        """Test getting descendant nodes."""
        root = PlanNode.create(goal=sample_goal)
        child1 = PlanNode.create(goal=Goal.create(description="Child 1"))
        child2 = PlanNode.create(goal=Goal.create(description="Child 2"))
        grandchild = PlanNode.create(goal=Goal.create(description="Grandchild"))

        root.add_child(child1)
        root.add_child(child2)
        child1.add_child(grandchild)

        descendants = root.get_descendants()
        assert len(descendants) == 3

    def test_plan_node_find_node(self, sample_goal):
        """Test finding a node by ID."""
        root = PlanNode.create(goal=sample_goal)
        child = PlanNode.create(goal=Goal.create(description="Child"))
        root.add_child(child)

        found = root.find_node(child.id)
        assert found == child

        not_found = root.find_node("nonexistent")
        assert not_found is None

    def test_plan_node_to_dict(self, sample_goal, sample_actions):
        """Test converting node to dictionary."""
        node = PlanNode.create(
            goal=sample_goal,
            actions=sample_actions,
            approach="Test approach",
        )

        result = node.to_dict()

        assert "id" in result
        assert "goal" in result
        assert "actions" in result
        assert len(result["actions"]) == 2
        assert result["approach"] == "Test approach"


class TestPlanTree:
    """Tests for PlanTree class."""

    @pytest.fixture
    def sample_tree(self):
        """Create a sample plan tree."""
        root_goal = Goal.create(description="Root goal")
        root = PlanNode.create(
            goal=root_goal,
            actions=[
                ActionStep.create(action_name="root_action1"),
                ActionStep.create(action_name="root_action2"),
            ],
        )

        child1_goal = Goal.create(description="Child 1")
        child1 = PlanNode.create(
            goal=child1_goal,
            actions=[ActionStep.create(action_name="child1_action")],
        )

        child2_goal = Goal.create(description="Child 2")
        child2 = PlanNode.create(
            goal=child2_goal,
            actions=[ActionStep.create(action_name="child2_action")],
        )

        root.add_child(child1)
        root.add_child(child2)

        return PlanTree(root)

    def test_plan_tree_creation(self, sample_tree):
        """Test creating a plan tree."""
        assert sample_tree.root is not None
        assert sample_tree.current_node == sample_tree.root

    def test_plan_tree_get_next_action(self, sample_tree):
        """Test getting next action."""
        action = sample_tree.get_next_action()
        assert action is not None
        assert action.action_name == "root_action1"

    def test_plan_tree_mark_action_complete(self, sample_tree):
        """Test marking action complete."""
        action = sample_tree.get_next_action()
        sample_tree.mark_action_complete(action, success=True, result="done")

        assert action.status == NodeStatus.COMPLETED
        assert action.result == "done"

    def test_plan_tree_mark_action_failed(self, sample_tree):
        """Test marking action failed."""
        action = sample_tree.get_next_action()
        sample_tree.mark_action_complete(action, success=False, result="error")

        assert action.status == NodeStatus.FAILED
        assert action.error == "error"

    def test_plan_tree_needs_replanning_after_failure(self, sample_tree):
        """Test needs_replanning after failure."""
        action = sample_tree.get_next_action()
        # Mark the action as failed through the tree (which adds to history)
        sample_tree.mark_action_complete(action, success=False, result="Error")
        # Add a couple more failures to trigger replanning
        action2 = sample_tree.get_next_action()
        sample_tree.mark_action_complete(action2, success=False, result="Error 2")
        action3 = sample_tree.root.children[0].actions[0] if sample_tree.root.children else None
        if action3:
            sample_tree.mark_action_complete(action3, success=False, result="Error 3")

        assert sample_tree.needs_replanning() is True

    def test_plan_tree_get_failure_context(self, sample_tree):
        """Test getting failure context."""
        action = sample_tree.get_next_action()
        sample_tree.mark_action_complete(action, success=False, result="Error message")

        context = sample_tree.get_failure_context()

        assert "current_node_id" in context
        assert "current_goal" in context
        assert "failed_actions" in context

    def test_plan_tree_find_node(self, sample_tree):
        """Test finding a node in the tree."""
        # Find root
        found = sample_tree.find_node(sample_tree.root.id)
        assert found == sample_tree.root

        # Find child
        child = sample_tree.root.children[0]
        found = sample_tree.find_node(child.id)
        assert found == child

    def test_plan_tree_get_active_branch(self, sample_tree):
        """Test getting active branch."""
        branch = sample_tree.get_active_branch()
        assert len(branch) == 1  # Just root
        assert branch[0] == sample_tree.root

    def test_plan_tree_get_all_pending_actions(self, sample_tree):
        """Test getting all pending actions."""
        pending = sample_tree.get_all_pending_actions()
        assert len(pending) == 4  # 2 root + 1 child1 + 1 child2

    def test_plan_tree_progress(self, sample_tree):
        """Test overall progress."""
        assert sample_tree.progress == 0.0

        # Complete first action
        action = sample_tree.get_next_action()
        sample_tree.mark_action_complete(action, success=True)

        assert sample_tree.progress > 0.0

    def test_plan_tree_is_complete(self, sample_tree):
        """Test is_complete property."""
        assert sample_tree.is_complete is False

        # Complete all actions and goals
        sample_tree.root.goal.complete()
        assert sample_tree.is_complete is True

    def test_plan_tree_is_failed(self, sample_tree):
        """Test is_failed property."""
        assert sample_tree.is_failed is False

        sample_tree.root.goal.fail("Failed")
        assert sample_tree.is_failed is True

    def test_plan_tree_total_steps(self, sample_tree):
        """Test total_steps property."""
        assert sample_tree.total_steps == 4

    def test_plan_tree_completed_steps(self, sample_tree):
        """Test completed_steps property."""
        assert sample_tree.completed_steps == 0

        action = sample_tree.get_next_action()
        sample_tree.mark_action_complete(action, success=True)

        assert sample_tree.completed_steps == 1

    def test_plan_tree_get_statistics(self, sample_tree):
        """Test getting statistics."""
        stats = sample_tree.get_statistics()

        assert "total_nodes" in stats
        assert "total_actions" in stats
        assert "completed_actions" in stats
        assert "progress" in stats

    def test_plan_tree_to_dict(self, sample_tree):
        """Test converting tree to dictionary."""
        result = sample_tree.to_dict()

        assert "root" in result
        assert "current_node_id" in result
        assert "statistics" in result

    def test_plan_tree_visualize(self, sample_tree):
        """Test tree visualization."""
        visualization = sample_tree.visualize()

        assert "Root goal" in visualization
        assert "root_action1" in visualization

    def test_plan_tree_str(self, sample_tree):
        """Test string representation."""
        result = str(sample_tree)

        assert "PlanTree" in result
        assert "progress=" in result
