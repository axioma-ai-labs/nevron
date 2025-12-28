"""Tests for Replanning Engine module."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.planning.goal import Goal
from src.planning.plan_tree import ActionStep, NodeStatus, PlanNode, PlanTree
from src.planning.replanning import (
    FailureAnalysis,
    FailureType,
    ReplanningConfig,
    ReplanningEngine,
    ReplanningStrategy,
)


class TestFailureType:
    """Tests for FailureType enum."""

    def test_failure_type_values(self):
        """Test all failure type values exist."""
        assert FailureType.ACTION_ERROR.value == "action_error"
        assert FailureType.TIMEOUT.value == "timeout"
        assert FailureType.INVALID_RESULT.value == "invalid_result"
        assert FailureType.RATE_LIMITED.value == "rate_limited"
        assert FailureType.PERMISSION_DENIED.value == "permission_denied"


class TestReplanningStrategy:
    """Tests for ReplanningStrategy enum."""

    def test_replanning_strategy_values(self):
        """Test all replanning strategy values exist."""
        assert ReplanningStrategy.RETRY.value == "retry"
        assert ReplanningStrategy.SKIP.value == "skip"
        assert ReplanningStrategy.ALTERNATIVE.value == "alternative"
        assert ReplanningStrategy.BACKTRACK.value == "backtrack"
        assert ReplanningStrategy.ABORT.value == "abort"


class TestReplanningConfig:
    """Tests for ReplanningConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ReplanningConfig()

        assert config.max_retries_per_action == 3
        assert config.max_alternatives == 3
        assert config.backtrack_limit == 2
        assert config.enable_llm_analysis is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ReplanningConfig(
            max_retries_per_action=5,
            max_alternatives=5,
        )

        assert config.max_retries_per_action == 5
        assert config.max_alternatives == 5


@pytest.fixture
def mock_llm():
    """Mock the LLM."""
    llm = AsyncMock()
    return llm


@pytest.fixture
def replanning_engine(mock_llm):
    """Create a ReplanningEngine with mocked LLM."""
    with patch("src.planning.replanning.LLM", return_value=mock_llm):
        engine = ReplanningEngine(
            available_actions=["search_tavily", "analyze_news"],
        )
        engine.llm = mock_llm
        return engine


@pytest.fixture
def sample_plan_tree():
    """Create a sample plan tree for testing."""
    root_goal = Goal.create(description="Root goal")
    root = PlanNode.create(
        goal=root_goal,
        actions=[
            ActionStep.create(action_name="action1"),
            ActionStep.create(action_name="action2"),
        ],
    )
    return PlanTree(root)


class TestReplanningEngine:
    """Tests for ReplanningEngine class."""

    def test_engine_creation(self, replanning_engine):
        """Test creating an engine."""
        assert replanning_engine is not None
        assert len(replanning_engine._available_actions) == 2

    def test_set_available_actions(self, replanning_engine):
        """Test updating available actions."""
        replanning_engine.set_available_actions(["action1"])
        assert replanning_engine._available_actions == ["action1"]

    def test_classify_failure_timeout(self, replanning_engine):
        """Test classifying timeout failure."""
        failure_type = replanning_engine._classify_failure("Operation timed out")
        assert failure_type == FailureType.TIMEOUT

    def test_classify_failure_rate_limited(self, replanning_engine):
        """Test classifying rate limit failure."""
        failure_type = replanning_engine._classify_failure("Rate limit exceeded")
        assert failure_type == FailureType.RATE_LIMITED

    def test_classify_failure_permission(self, replanning_engine):
        """Test classifying permission failure."""
        failure_type = replanning_engine._classify_failure("Access denied")
        assert failure_type == FailureType.PERMISSION_DENIED

    def test_classify_failure_resource(self, replanning_engine):
        """Test classifying resource failure."""
        failure_type = replanning_engine._classify_failure("Resource not found")
        assert failure_type == FailureType.RESOURCE_UNAVAILABLE

    def test_classify_failure_unknown(self, replanning_engine):
        """Test classifying unknown failure."""
        failure_type = replanning_engine._classify_failure("Something happened")
        assert failure_type == FailureType.UNKNOWN

    def test_can_recover_permission_denied(self, replanning_engine):
        """Test that permission denied is not recoverable."""
        action = ActionStep.create(action_name="test")
        can_recover = replanning_engine._can_recover(FailureType.PERMISSION_DENIED, action)
        assert can_recover is False

    def test_can_recover_other(self, replanning_engine):
        """Test that other failures are recoverable."""
        action = ActionStep.create(action_name="test")
        can_recover = replanning_engine._can_recover(FailureType.TIMEOUT, action)
        assert can_recover is True

    def test_determine_strategy_rate_limited(self, replanning_engine):
        """Test strategy for rate limited failure."""
        strategy = replanning_engine._determine_strategy(
            FailureType.RATE_LIMITED, retry_count=0, can_recover=True
        )
        assert strategy == ReplanningStrategy.WAIT_AND_RETRY

    def test_determine_strategy_timeout(self, replanning_engine):
        """Test strategy for timeout failure."""
        strategy = replanning_engine._determine_strategy(
            FailureType.TIMEOUT, retry_count=0, can_recover=True
        )
        assert strategy == ReplanningStrategy.RETRY

        strategy = replanning_engine._determine_strategy(
            FailureType.TIMEOUT, retry_count=3, can_recover=True
        )
        assert strategy == ReplanningStrategy.ALTERNATIVE

    def test_determine_strategy_precondition(self, replanning_engine):
        """Test strategy for precondition failure."""
        strategy = replanning_engine._determine_strategy(
            FailureType.PRECONDITION_NOT_MET, retry_count=0, can_recover=True
        )
        assert strategy == ReplanningStrategy.BACKTRACK

    def test_determine_strategy_not_recoverable(self, replanning_engine):
        """Test strategy when not recoverable."""
        strategy = replanning_engine._determine_strategy(
            FailureType.PERMISSION_DENIED, retry_count=0, can_recover=False
        )
        assert strategy == ReplanningStrategy.ABORT

    @pytest.mark.asyncio
    async def test_analyze_failure(self, replanning_engine, mock_llm):
        """Test analyzing a failure."""
        mock_llm.generate_response.return_value = "Network connectivity issue"

        goal = Goal.create(description="Test goal")
        node = PlanNode.create(goal=goal)
        action = ActionStep.create(action_name="test_action")

        analysis = await replanning_engine.analyze_failure(
            action=action,
            node=node,
            error="Connection timeout after 30s",
        )

        assert analysis is not None
        assert isinstance(analysis, FailureAnalysis)
        assert analysis.failure_type == FailureType.TIMEOUT
        assert analysis.can_recover is True

    @pytest.mark.asyncio
    async def test_analyze_failure_llm_disabled(self, mock_llm):
        """Test failure analysis with LLM disabled."""
        with patch("src.planning.replanning.LLM", return_value=mock_llm):
            config = ReplanningConfig(enable_llm_analysis=False)
            engine = ReplanningEngine(config=config)
            engine.llm = mock_llm

            goal = Goal.create(description="Test")
            node = PlanNode.create(goal=goal)
            action = ActionStep.create(action_name="test")

            analysis = await engine.analyze_failure(action=action, node=node, error="Error")

            # LLM should not be called
            mock_llm.generate_response.assert_not_called()
            assert analysis.reasoning == ""

    @pytest.mark.asyncio
    async def test_generate_alternatives(self, replanning_engine, mock_llm):
        """Test generating alternative approaches."""
        mock_llm.generate_response.return_value = json.dumps(
            {
                "alternatives": [
                    {
                        "approach": "Alternative 1",
                        "actions": [
                            {
                                "action_name": "search_tavily",
                                "description": "Search differently",
                                "arguments": {"query": "alternative"},
                            }
                        ],
                    },
                ]
            }
        )

        goal = Goal.create(description="Test")
        node = PlanNode.create(goal=goal)
        action = ActionStep.create(action_name="failed_action")
        action.fail("Error")

        analysis = FailureAnalysis(
            failure_type=FailureType.ACTION_ERROR,
            failed_action=action,
            failed_node=node,
            error_message="Error",
        )

        plan_tree = PlanTree(node)
        alternatives = await replanning_engine.generate_alternatives(analysis, plan_tree)

        assert len(alternatives) == 1
        assert alternatives[0].approach == "Alternative 1"

    @pytest.mark.asyncio
    async def test_generate_alternatives_parse_error(self, replanning_engine, mock_llm):
        """Test generating alternatives with parse error."""
        mock_llm.generate_response.return_value = "invalid json"

        goal = Goal.create(description="Test")
        node = PlanNode.create(goal=goal)
        action = ActionStep.create(action_name="failed")

        analysis = FailureAnalysis(
            failure_type=FailureType.ACTION_ERROR,
            failed_action=action,
            failed_node=node,
            error_message="Error",
        )

        plan_tree = PlanTree(node)
        alternatives = await replanning_engine.generate_alternatives(analysis, plan_tree)

        assert alternatives == []

    @pytest.mark.asyncio
    async def test_replan_retry(self, replanning_engine, sample_plan_tree):
        """Test replanning with retry strategy."""
        action = sample_plan_tree.root.actions[0]
        action.fail("Temporary error")

        analysis = FailureAnalysis(
            failure_type=FailureType.TIMEOUT,
            failed_action=action,
            failed_node=sample_plan_tree.root,
            error_message="Timeout",
            recommended_strategy=ReplanningStrategy.RETRY,
        )

        result = await replanning_engine.replan(sample_plan_tree, analysis)

        assert result.success is True
        assert result.strategy_used == ReplanningStrategy.RETRY
        assert action.status == NodeStatus.PENDING  # Reset for retry

    @pytest.mark.asyncio
    async def test_replan_skip(self, replanning_engine, sample_plan_tree):
        """Test replanning with skip strategy."""
        action = sample_plan_tree.root.actions[0]

        analysis = FailureAnalysis(
            failure_type=FailureType.RESOURCE_UNAVAILABLE,
            failed_action=action,
            failed_node=sample_plan_tree.root,
            error_message="Not found",
            recommended_strategy=ReplanningStrategy.SKIP,
        )

        result = await replanning_engine.replan(sample_plan_tree, analysis)

        assert result.success is True
        assert result.strategy_used == ReplanningStrategy.SKIP
        assert action.status == NodeStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_replan_wait_and_retry(self, replanning_engine, sample_plan_tree):
        """Test replanning with wait and retry strategy."""
        action = sample_plan_tree.root.actions[0]

        analysis = FailureAnalysis(
            failure_type=FailureType.RATE_LIMITED,
            failed_action=action,
            failed_node=sample_plan_tree.root,
            error_message="Rate limited",
            recommended_strategy=ReplanningStrategy.WAIT_AND_RETRY,
            retry_after_seconds=10.0,
        )

        result = await replanning_engine.replan(sample_plan_tree, analysis)

        assert result.success is True
        assert result.strategy_used == ReplanningStrategy.WAIT_AND_RETRY
        assert "Wait" in result.message

    @pytest.mark.asyncio
    async def test_replan_alternative(self, replanning_engine, mock_llm, sample_plan_tree):
        """Test replanning with alternative strategy."""
        mock_llm.generate_response.return_value = json.dumps(
            {
                "alternatives": [
                    {
                        "approach": "Alternative approach",
                        "actions": [
                            {
                                "action_name": "analyze_news",
                                "description": "Try this",
                                "arguments": {},
                            }
                        ],
                    }
                ]
            }
        )

        action = sample_plan_tree.root.actions[0]

        analysis = FailureAnalysis(
            failure_type=FailureType.ACTION_ERROR,
            failed_action=action,
            failed_node=sample_plan_tree.root,
            error_message="Failed",
            recommended_strategy=ReplanningStrategy.ALTERNATIVE,
        )

        result = await replanning_engine.replan(sample_plan_tree, analysis)

        assert result.success is True
        assert result.strategy_used == ReplanningStrategy.ALTERNATIVE
        assert len(result.alternative_nodes) > 0

    @pytest.mark.asyncio
    async def test_replan_backtrack(self, replanning_engine):
        """Test replanning with backtrack strategy."""
        # Create tree with parent-child
        root = PlanNode.create(goal=Goal.create(description="Root"))
        child = PlanNode.create(
            goal=Goal.create(description="Child"),
            actions=[ActionStep.create(action_name="child_action")],
        )
        root.add_child(child)
        plan_tree = PlanTree(root)
        plan_tree.current_node = child

        action = child.actions[0]

        analysis = FailureAnalysis(
            failure_type=FailureType.PRECONDITION_NOT_MET,
            failed_action=action,
            failed_node=child,
            error_message="Precondition failed",
            recommended_strategy=ReplanningStrategy.BACKTRACK,
        )

        result = await replanning_engine.replan(plan_tree, analysis)

        assert result.success is True
        assert result.strategy_used == ReplanningStrategy.BACKTRACK
        assert plan_tree.current_node == root  # Backtracked

    @pytest.mark.asyncio
    async def test_replan_abort(self, replanning_engine, sample_plan_tree):
        """Test replanning with abort strategy."""
        action = sample_plan_tree.root.actions[0]

        analysis = FailureAnalysis(
            failure_type=FailureType.PERMISSION_DENIED,
            failed_action=action,
            failed_node=sample_plan_tree.root,
            error_message="Access denied",
            recommended_strategy=ReplanningStrategy.ABORT,
            can_recover=False,
        )

        result = await replanning_engine.replan(sample_plan_tree, analysis)

        assert result.success is False
        assert result.strategy_used == ReplanningStrategy.ABORT

    def test_should_replan(self, replanning_engine, sample_plan_tree):
        """Test should_replan method."""
        assert replanning_engine.should_replan(sample_plan_tree) is False

        # Make it need replanning by recording failures in history
        for i in range(3):
            action = sample_plan_tree.root.actions[0] if sample_plan_tree.root.actions else None
            if action:
                sample_plan_tree.mark_action_complete(action, success=False, result=f"Error {i}")

        assert replanning_engine.should_replan(sample_plan_tree) is True

    def test_get_failure_history(self, replanning_engine):
        """Test getting failure history."""
        history = replanning_engine.get_failure_history()
        assert history == []

    def test_clear_failure_history(self, replanning_engine):
        """Test clearing failure history."""
        # Add a fake entry
        replanning_engine._failure_history.append(None)

        replanning_engine.clear_failure_history()
        assert len(replanning_engine._failure_history) == 0

    def test_get_statistics_empty(self, replanning_engine):
        """Test getting statistics with no failures."""
        stats = replanning_engine.get_statistics()

        assert stats["total_failures"] == 0
        assert stats["recovery_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_get_statistics_with_failures(self, replanning_engine, mock_llm):
        """Test getting statistics with failures."""
        mock_llm.generate_response.return_value = "Analysis"

        goal = Goal.create(description="Test")
        node = PlanNode.create(goal=goal)
        action = ActionStep.create(action_name="test")

        # Analyze some failures
        await replanning_engine.analyze_failure(action=action, node=node, error="Timeout")
        await replanning_engine.analyze_failure(
            action=action, node=node, error="Rate limit exceeded"
        )

        stats = replanning_engine.get_statistics()

        assert stats["total_failures"] == 2
        assert stats["recovery_rate"] > 0
        assert "by_type" in stats
        assert "by_strategy" in stats
