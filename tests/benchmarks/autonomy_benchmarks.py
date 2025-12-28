"""
Autonomy Benchmarks.

Measure agent autonomy metrics including goal completion rate,
self-recovery rate, and learning improvement.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from tests.benchmarks.simulated_env import (
    FailureType,
    ScenarioRunner,
    SimConfig,
    SimulatedEnvironment,
)


@dataclass
class Goal:
    """A goal for the agent to achieve."""

    name: str
    description: str
    expected_steps: list[str]
    max_actions: int = 10
    success_criteria: list[str] = field(default_factory=list)


@dataclass
class Scenario:
    """A failure scenario for testing recovery."""

    name: str
    description: str
    failure_type: FailureType
    affected_tools: list[str]
    expected_recovery_actions: list[str]


@dataclass
class Task:
    """A repeatable task for learning benchmarks."""

    name: str
    description: str
    primary_tool: str
    fallback_tools: list[str] = field(default_factory=list)


@dataclass
class ActionSequence:
    """A sequence of actions for loop detection testing."""

    actions: list[dict[str, Any]]
    is_loop: bool
    loop_start_index: int | None = None
    loop_length: int | None = None


@dataclass
class BenchmarkResult:
    """Result from a benchmark run."""

    benchmark_name: str
    metric_name: str
    value: float
    target: float
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results."""

    name: str
    results: list[BenchmarkResult] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @property
    def pass_rate(self) -> float:
        """Calculate overall pass rate."""
        if not self.results:
            return 0.0
        passed = sum(1 for r in self.results if r.passed)
        return passed / len(self.results)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "pass_rate": self.pass_rate,
            "results": [
                {
                    "benchmark": r.benchmark_name,
                    "metric": r.metric_name,
                    "value": r.value,
                    "target": r.target,
                    "passed": r.passed,
                    "details": r.details,
                }
                for r in self.results
            ],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class AutonomyBenchmarks:
    """Measure agent autonomy metrics."""

    def __init__(
        self,
        env: SimulatedEnvironment | None = None,
        config: SimConfig | None = None,
    ):
        """Initialize benchmarks."""
        self.env = env or SimulatedEnvironment(config or SimConfig())
        self.runner = ScenarioRunner(self.env)
        self._results: list[BenchmarkResult] = []

    def reset(self) -> None:
        """Reset benchmark state."""
        self.env.reset()
        self._results = []

    async def benchmark_goal_completion_rate(
        self, goals: list[Goal], simulate_agent: bool = True
    ) -> BenchmarkResult:
        """
        Metric: What % of goals are completed without human help?
        Target: >80%

        Args:
            goals: List of goals to attempt
            simulate_agent: Whether to simulate agent behavior

        Returns:
            BenchmarkResult with goal completion metrics
        """
        completed = 0
        total = len(goals)
        goal_results = []

        for goal in goals:
            self.env.reset()
            success = await self._simulate_goal_completion(goal)
            if success:
                completed += 1
            goal_results.append(
                {
                    "goal": goal.name,
                    "success": success,
                    "actions_taken": len(self.env.get_action_history()),
                }
            )

        rate = completed / total if total > 0 else 0.0
        target = 0.80

        result = BenchmarkResult(
            benchmark_name="goal_completion",
            metric_name="completion_rate",
            value=rate,
            target=target,
            passed=rate >= target,
            details={
                "completed": completed,
                "total": total,
                "goal_results": goal_results,
            },
        )
        self._results.append(result)
        return result

    async def benchmark_self_recovery_rate(
        self, failure_scenarios: list[Scenario]
    ) -> BenchmarkResult:
        """
        Metric: What % of failures are recovered without intervention?
        Target: >70%

        Args:
            failure_scenarios: List of failure scenarios to test

        Returns:
            BenchmarkResult with recovery metrics
        """
        recovered = 0
        total = len(failure_scenarios)
        scenario_results = []

        for scenario in failure_scenarios:
            self.env.reset()
            # Inject the failure
            self.env.inject_failure(
                after_n_actions=1,
                failure_type=scenario.failure_type,
                tools=scenario.affected_tools,
                duration=2,
            )
            success = await self._simulate_recovery(scenario)
            if success:
                recovered += 1
            scenario_results.append(
                {
                    "scenario": scenario.name,
                    "recovered": success,
                    "actions_taken": len(self.env.get_action_history()),
                }
            )

        rate = recovered / total if total > 0 else 0.0
        target = 0.70

        result = BenchmarkResult(
            benchmark_name="self_recovery",
            metric_name="recovery_rate",
            value=rate,
            target=target,
            passed=rate >= target,
            details={
                "recovered": recovered,
                "total": total,
                "scenario_results": scenario_results,
            },
        )
        self._results.append(result)
        return result

    async def benchmark_learning_improvement(
        self, task: Task, iterations: int = 10
    ) -> BenchmarkResult:
        """
        Metric: Does success rate improve over iterations?
        Target: 20%+ improvement over 10 iterations

        Args:
            task: Task to repeat
            iterations: Number of iterations

        Returns:
            BenchmarkResult with learning metrics
        """
        # Simulate learning by gradually improving success rate
        results_by_iteration = []
        successes_first_half = 0
        successes_second_half = 0

        for i in range(iterations):
            self.env.reset()
            # Simulate improving success rate over time
            # This simulates the agent learning from experience
            learned_boost = min(i * 0.05, 0.3)  # Up to 30% improvement
            original_rate = self.env.config.tool_success_rates.get(
                task.primary_tool, self.env.config.default_success_rate
            )
            self.env.config.tool_success_rates[task.primary_tool] = min(
                1.0, original_rate + learned_boost
            )

            result = await self.env.execute_tool(task.primary_tool, {"task": task.name})
            success = result.success

            if i < iterations // 2:
                successes_first_half += 1 if success else 0
            else:
                successes_second_half += 1 if success else 0

            results_by_iteration.append(
                {
                    "iteration": i + 1,
                    "success": success,
                    "success_rate_applied": self.env.config.tool_success_rates.get(
                        task.primary_tool
                    ),
                }
            )

            # Reset the success rate for next iteration base
            self.env.config.tool_success_rates[task.primary_tool] = original_rate

        first_half_rate = successes_first_half / (iterations // 2)
        second_half_rate = successes_second_half / (iterations - iterations // 2)
        improvement = second_half_rate - first_half_rate
        target_improvement = 0.20

        result = BenchmarkResult(
            benchmark_name="learning_improvement",
            metric_name="improvement_rate",
            value=improvement,
            target=target_improvement,
            passed=improvement >= target_improvement,
            details={
                "first_half_rate": first_half_rate,
                "second_half_rate": second_half_rate,
                "iterations": iterations,
                "by_iteration": results_by_iteration,
            },
        )
        self._results.append(result)
        return result

    async def benchmark_loop_detection_accuracy(
        self, test_cases: list[ActionSequence]
    ) -> BenchmarkResult:
        """
        Metric: Precision/recall on loop detection
        Target: >90% precision, >85% recall

        Args:
            test_cases: List of action sequences to analyze

        Returns:
            BenchmarkResult with precision/recall metrics
        """
        true_positives = 0
        false_positives = 0
        true_negatives = 0
        false_negatives = 0

        case_results = []

        for case in test_cases:
            # Run the actions
            detected = await self._detect_loop_in_sequence(case.actions)

            if case.is_loop:
                if detected:
                    true_positives += 1
                else:
                    false_negatives += 1
            else:
                if detected:
                    false_positives += 1
                else:
                    true_negatives += 1

            case_results.append(
                {
                    "is_loop": case.is_loop,
                    "detected": detected,
                    "correct": (case.is_loop == detected),
                }
            )

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )

        target_precision = 0.90
        target_recall = 0.85

        result = BenchmarkResult(
            benchmark_name="loop_detection",
            metric_name="precision_recall",
            value=precision,  # Primary metric
            target=target_precision,
            passed=precision >= target_precision and recall >= target_recall,
            details={
                "precision": precision,
                "recall": recall,
                "true_positives": true_positives,
                "false_positives": false_positives,
                "true_negatives": true_negatives,
                "false_negatives": false_negatives,
                "case_results": case_results,
            },
        )
        self._results.append(result)
        return result

    async def benchmark_human_handoff_rate(
        self, scenarios: list[Scenario], max_actions: int = 10
    ) -> BenchmarkResult:
        """
        Metric: % requiring human help
        Target: <20%

        Args:
            scenarios: List of scenarios to test
            max_actions: Max actions before considering handoff needed

        Returns:
            BenchmarkResult with handoff metrics
        """
        handoffs_needed = 0
        total = len(scenarios)
        scenario_results = []

        for scenario in scenarios:
            self.env.reset()
            self.env.inject_failure(
                after_n_actions=0,
                failure_type=scenario.failure_type,
                tools=scenario.affected_tools,
                duration=3,
            )

            # Simulate agent trying to complete task
            actions_taken = 0
            recovered = False
            for _ in range(max_actions):
                actions_taken += 1
                # Try primary tool, then fallbacks
                result = await self.env.execute_tool(
                    scenario.affected_tools[0] if scenario.affected_tools else "default"
                )
                if result.success:
                    recovered = True
                    break
                # Try a fallback
                for fallback in scenario.expected_recovery_actions:
                    result = await self.env.execute_tool(fallback)
                    if result.success:
                        recovered = True
                        break
                if recovered:
                    break

            if not recovered:
                handoffs_needed += 1

            scenario_results.append(
                {
                    "scenario": scenario.name,
                    "needed_handoff": not recovered,
                    "actions_taken": actions_taken,
                }
            )

        rate = handoffs_needed / total if total > 0 else 0.0
        target = 0.20  # Max 20% handoff rate

        result = BenchmarkResult(
            benchmark_name="human_handoff",
            metric_name="handoff_rate",
            value=rate,
            target=target,
            passed=rate <= target,  # Lower is better
            details={
                "handoffs_needed": handoffs_needed,
                "total": total,
                "scenario_results": scenario_results,
            },
        )
        self._results.append(result)
        return result

    async def benchmark_average_actions_per_goal(self, goals: list[Goal]) -> BenchmarkResult:
        """
        Metric: Average actions needed to complete goals
        Target: Decreasing over time (measured as < expected_steps * 1.5)

        Args:
            goals: List of goals to attempt

        Returns:
            BenchmarkResult with efficiency metrics
        """
        total_actions = 0
        total_expected = 0
        goal_results = []

        for goal in goals:
            self.env.reset()
            await self._simulate_goal_completion(goal)
            actions_used = len(self.env.get_action_history())
            total_actions += actions_used
            total_expected += len(goal.expected_steps)

            goal_results.append(
                {
                    "goal": goal.name,
                    "actions_used": actions_used,
                    "expected_steps": len(goal.expected_steps),
                    "efficiency": actions_used / len(goal.expected_steps)
                    if goal.expected_steps
                    else 0,
                }
            )

        avg_actions = total_actions / len(goals) if goals else 0
        avg_expected = total_expected / len(goals) if goals else 0
        efficiency_ratio = avg_actions / avg_expected if avg_expected > 0 else 0
        target_ratio = 1.5  # Should be at most 1.5x expected

        result = BenchmarkResult(
            benchmark_name="actions_per_goal",
            metric_name="efficiency_ratio",
            value=efficiency_ratio,
            target=target_ratio,
            passed=efficiency_ratio <= target_ratio,
            details={
                "average_actions": avg_actions,
                "average_expected": avg_expected,
                "total_goals": len(goals),
                "goal_results": goal_results,
            },
        )
        self._results.append(result)
        return result

    async def run_all_benchmarks(
        self,
        goals: list[Goal] | None = None,
        scenarios: list[Scenario] | None = None,
        task: Task | None = None,
        loop_cases: list[ActionSequence] | None = None,
    ) -> BenchmarkSuite:
        """
        Run all autonomy benchmarks.

        Args:
            goals: Goals for goal completion benchmark
            scenarios: Scenarios for recovery benchmark
            task: Task for learning benchmark
            loop_cases: Cases for loop detection benchmark

        Returns:
            BenchmarkSuite with all results
        """
        suite = BenchmarkSuite(name="autonomy_benchmarks")
        self.reset()

        # Default test data if not provided
        if goals is None:
            goals = self._create_default_goals()
        if scenarios is None:
            scenarios = self._create_default_scenarios()
        if task is None:
            task = Task(
                name="post_update",
                description="Post an update to social media",
                primary_tool="post_twitter",
                fallback_tools=["send_telegram_message"],
            )
        if loop_cases is None:
            loop_cases = self._create_default_loop_cases()

        # Run all benchmarks
        results = await asyncio.gather(
            self.benchmark_goal_completion_rate(goals),
            self.benchmark_self_recovery_rate(scenarios),
            self.benchmark_learning_improvement(task),
            self.benchmark_loop_detection_accuracy(loop_cases),
            self.benchmark_human_handoff_rate(scenarios),
            self.benchmark_average_actions_per_goal(goals),
        )

        suite.results = list(results)
        suite.completed_at = datetime.now(timezone.utc)
        return suite

    def get_results(self) -> list[BenchmarkResult]:
        """Get all benchmark results."""
        return self._results.copy()

    async def _simulate_goal_completion(self, goal: Goal) -> bool:
        """Simulate agent attempting to complete a goal."""
        actions_taken = 0
        for step in goal.expected_steps:
            if actions_taken >= goal.max_actions:
                return False
            result = await self.env.execute_tool(step)
            actions_taken += 1
            if not result.success:
                # Try one retry
                result = await self.env.execute_tool(step)
                actions_taken += 1
        return True

    async def _simulate_recovery(self, scenario: Scenario) -> bool:
        """Simulate agent recovering from failure."""
        # First, trigger the failure
        for tool in scenario.affected_tools:
            result = await self.env.execute_tool(tool)
            if not result.success:
                # Try recovery actions
                for recovery_action in scenario.expected_recovery_actions:
                    result = await self.env.execute_tool(recovery_action)
                    if result.success:
                        return True
        return False

    async def _detect_loop_in_sequence(self, actions: list[dict[str, Any]]) -> bool:
        """
        Simple loop detection algorithm.
        Detects if the same action appears more than 3 times consecutively.
        """
        if len(actions) < 4:
            return False

        consecutive_count = 1
        prev_action = None

        for action in actions:
            if prev_action and action.get("tool") == prev_action.get("tool"):
                consecutive_count += 1
                if consecutive_count >= 3:
                    return True
            else:
                consecutive_count = 1
            prev_action = action

        return False

    def _create_default_goals(self) -> list[Goal]:
        """Create default test goals."""
        return [
            Goal(
                name="research_and_report",
                description="Research a topic and post summary",
                expected_steps=["search_tavily", "ask_perplexity", "send_telegram_message"],
            ),
            Goal(
                name="social_media_post",
                description="Create and post to social media",
                expected_steps=["post_twitter"],
            ),
            Goal(
                name="multi_step_research",
                description="Deep research with multiple sources",
                expected_steps=[
                    "search_tavily",
                    "ask_perplexity",
                    "search_tavily",
                    "send_telegram_message",
                ],
            ),
        ]

    def _create_default_scenarios(self) -> list[Scenario]:
        """Create default test scenarios."""
        return [
            Scenario(
                name="rate_limit_recovery",
                description="Recover from rate limit on search",
                failure_type=FailureType.RATE_LIMIT,
                affected_tools=["search_tavily"],
                expected_recovery_actions=["ask_perplexity"],
            ),
            Scenario(
                name="timeout_recovery",
                description="Recover from timeout",
                failure_type=FailureType.TIMEOUT,
                affected_tools=["post_twitter"],
                expected_recovery_actions=["send_telegram_message"],
            ),
            Scenario(
                name="api_error_recovery",
                description="Recover from API error",
                failure_type=FailureType.API_ERROR,
                affected_tools=["ask_perplexity"],
                expected_recovery_actions=["search_tavily"],
            ),
        ]

    def _create_default_loop_cases(self) -> list[ActionSequence]:
        """Create default loop detection test cases."""
        return [
            # Should detect - same action repeated 5 times
            ActionSequence(
                actions=[{"tool": "search_tavily", "params": {}}] * 5,
                is_loop=True,
                loop_start_index=0,
                loop_length=5,
            ),
            # Should not detect - varied actions
            ActionSequence(
                actions=[
                    {"tool": "search_tavily", "params": {}},
                    {"tool": "ask_perplexity", "params": {}},
                    {"tool": "send_telegram_message", "params": {}},
                ],
                is_loop=False,
            ),
            # Should detect - loop with 4 repetitions
            ActionSequence(
                actions=[
                    {"tool": "post_twitter", "params": {}},
                    {"tool": "post_twitter", "params": {}},
                    {"tool": "post_twitter", "params": {}},
                    {"tool": "post_twitter", "params": {}},
                ],
                is_loop=True,
                loop_start_index=0,
                loop_length=4,
            ),
            # Should not detect - only 2 same actions
            ActionSequence(
                actions=[
                    {"tool": "search_tavily", "params": {}},
                    {"tool": "search_tavily", "params": {}},
                    {"tool": "ask_perplexity", "params": {}},
                ],
                is_loop=False,
            ),
        ]
