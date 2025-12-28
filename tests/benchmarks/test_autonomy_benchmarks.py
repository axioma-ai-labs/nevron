"""Tests for autonomy benchmarks."""

import pytest

from tests.benchmarks.autonomy_benchmarks import (
    ActionSequence,
    AutonomyBenchmarks,
    BenchmarkResult,
    BenchmarkSuite,
    Goal,
    Scenario,
    Task,
)
from tests.benchmarks.simulated_env import FailureType, SimConfig


class TestBenchmarkResult:
    """Tests for BenchmarkResult dataclass."""

    def test_passed_result(self):
        """Test passed benchmark result."""
        result = BenchmarkResult(
            benchmark_name="test",
            metric_name="success_rate",
            value=0.85,
            target=0.80,
            passed=True,
        )

        assert result.passed is True
        assert result.value > result.target

    def test_failed_result(self):
        """Test failed benchmark result."""
        result = BenchmarkResult(
            benchmark_name="test",
            metric_name="success_rate",
            value=0.70,
            target=0.80,
            passed=False,
        )

        assert result.passed is False
        assert result.value < result.target


class TestBenchmarkSuite:
    """Tests for BenchmarkSuite dataclass."""

    def test_pass_rate_calculation(self):
        """Test pass rate calculation."""
        suite = BenchmarkSuite(name="test_suite")
        suite.results = [
            BenchmarkResult("test1", "metric", 0.9, 0.8, True),
            BenchmarkResult("test2", "metric", 0.7, 0.8, False),
            BenchmarkResult("test3", "metric", 0.85, 0.8, True),
            BenchmarkResult("test4", "metric", 0.95, 0.8, True),
        ]

        assert suite.pass_rate == 0.75  # 3 out of 4 passed

    def test_empty_suite(self):
        """Test empty suite pass rate."""
        suite = BenchmarkSuite(name="empty")
        assert suite.pass_rate == 0.0

    def test_to_dict(self):
        """Test serialization."""
        suite = BenchmarkSuite(name="test")
        suite.results = [
            BenchmarkResult("test1", "metric", 0.9, 0.8, True),
        ]

        data = suite.to_dict()

        assert data["name"] == "test"
        assert len(data["results"]) == 1
        assert data["pass_rate"] == 1.0


class TestGoal:
    """Tests for Goal dataclass."""

    def test_goal_creation(self):
        """Test goal creation."""
        goal = Goal(
            name="research",
            description="Research a topic",
            expected_steps=["search", "analyze", "summarize"],
            max_actions=10,
        )

        assert goal.name == "research"
        assert len(goal.expected_steps) == 3
        assert goal.max_actions == 10


class TestScenario:
    """Tests for Scenario dataclass."""

    def test_scenario_creation(self):
        """Test scenario creation."""
        scenario = Scenario(
            name="rate_limit_recovery",
            description="Recover from rate limit",
            failure_type=FailureType.RATE_LIMIT,
            affected_tools=["search_tavily"],
            expected_recovery_actions=["ask_perplexity"],
        )

        assert scenario.failure_type == FailureType.RATE_LIMIT
        assert "search_tavily" in scenario.affected_tools


class TestActionSequence:
    """Tests for ActionSequence dataclass."""

    def test_loop_sequence(self):
        """Test loop action sequence."""
        seq = ActionSequence(
            actions=[{"tool": "search", "params": {}}] * 5,
            is_loop=True,
            loop_start_index=0,
            loop_length=5,
        )

        assert seq.is_loop is True
        assert len(seq.actions) == 5

    def test_non_loop_sequence(self):
        """Test non-loop action sequence."""
        seq = ActionSequence(
            actions=[
                {"tool": "search", "params": {}},
                {"tool": "analyze", "params": {}},
                {"tool": "post", "params": {}},
            ],
            is_loop=False,
        )

        assert seq.is_loop is False


class TestAutonomyBenchmarks:
    """Tests for AutonomyBenchmarks class."""

    @pytest.fixture
    def benchmarks(self):
        """Create benchmarks instance."""
        config = SimConfig(seed=42, default_success_rate=0.9)
        return AutonomyBenchmarks(config=config)

    @pytest.mark.asyncio
    async def test_goal_completion_benchmark(self, benchmarks):
        """Test goal completion rate benchmark."""
        goals = [
            Goal(
                name="simple_goal",
                description="Simple goal",
                expected_steps=["action1"],
                max_actions=5,
            ),
            Goal(
                name="complex_goal",
                description="Complex goal",
                expected_steps=["action1", "action2", "action3"],
                max_actions=10,
            ),
        ]

        result = await benchmarks.benchmark_goal_completion_rate(goals)

        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "goal_completion"
        assert "completed" in result.details
        assert "total" in result.details

    @pytest.mark.asyncio
    async def test_self_recovery_benchmark(self, benchmarks):
        """Test self recovery rate benchmark."""
        scenarios = [
            Scenario(
                name="rate_limit",
                description="Rate limit scenario",
                failure_type=FailureType.RATE_LIMIT,
                affected_tools=["search"],
                expected_recovery_actions=["fallback"],
            ),
        ]

        result = await benchmarks.benchmark_self_recovery_rate(scenarios)

        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "self_recovery"

    @pytest.mark.asyncio
    async def test_learning_improvement_benchmark(self, benchmarks):
        """Test learning improvement benchmark."""
        task = Task(
            name="test_task",
            description="Test task",
            primary_tool="primary",
            fallback_tools=["fallback"],
        )

        result = await benchmarks.benchmark_learning_improvement(task, iterations=5)

        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "learning_improvement"
        assert "first_half_rate" in result.details
        assert "second_half_rate" in result.details

    @pytest.mark.asyncio
    async def test_loop_detection_benchmark(self, benchmarks):
        """Test loop detection accuracy benchmark."""
        test_cases = [
            ActionSequence(
                actions=[{"tool": "search", "params": {}}] * 5,
                is_loop=True,
            ),
            ActionSequence(
                actions=[
                    {"tool": "search", "params": {}},
                    {"tool": "post", "params": {}},
                ],
                is_loop=False,
            ),
        ]

        result = await benchmarks.benchmark_loop_detection_accuracy(test_cases)

        assert isinstance(result, BenchmarkResult)
        assert result.benchmark_name == "loop_detection"
        assert "precision" in result.details
        assert "recall" in result.details

    @pytest.mark.asyncio
    async def test_run_all_benchmarks(self, benchmarks):
        """Test running all benchmarks."""
        suite = await benchmarks.run_all_benchmarks()

        assert isinstance(suite, BenchmarkSuite)
        assert len(suite.results) >= 4  # At least 4 benchmarks
        assert suite.completed_at is not None

    def test_reset(self, benchmarks):
        """Test benchmark reset."""
        benchmarks._results = [1, 2, 3]
        benchmarks.reset()

        assert len(benchmarks._results) == 0
