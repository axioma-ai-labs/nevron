"""
Benchmark Runner.

CLI runner for autonomy benchmarks with metrics collection and reporting.
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tests.benchmarks.autonomy_benchmarks import (
    ActionSequence,
    AutonomyBenchmarks,
    BenchmarkSuite,
    Goal,
    Scenario,
    Task,
)
from tests.benchmarks.simulated_env import FailureType, SimConfig, SimulatedEnvironment
from tests.benchmarks.stability_tests import StabilityMetrics, StabilityTests


@dataclass
class BenchmarkRunConfig:
    """Configuration for a benchmark run."""

    # Output settings
    output_dir: Path = field(default_factory=lambda: Path("benchmarks/results"))
    output_format: str = "json"  # json, markdown, console
    verbose: bool = False

    # Benchmark selection
    run_autonomy: bool = True
    run_stability: bool = True

    # Simulation settings
    seed: int | None = None
    default_success_rate: float = 0.8


@dataclass
class BenchmarkRunResult:
    """Complete result from a benchmark run."""

    timestamp: datetime
    config: BenchmarkRunConfig
    autonomy_suite: BenchmarkSuite | None = None
    stability_results: list[StabilityMetrics] = field(default_factory=list)

    @property
    def overall_passed(self) -> bool:
        """Check if all benchmarks passed."""
        autonomy_passed = self.autonomy_suite.pass_rate >= 0.8 if self.autonomy_suite else True
        stability_passed = all(r.passed for r in self.stability_results)
        return autonomy_passed and stability_passed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "overall_passed": self.overall_passed,
            "autonomy": self.autonomy_suite.to_dict() if self.autonomy_suite else None,
            "stability": [
                {
                    "test_name": r.test_name,
                    "passed": r.passed,
                    "duration_seconds": r.duration_seconds,
                    "success_rate": r.success_rate,
                    "memory_growth_mb": r.memory_growth_mb,
                    "failure_reason": r.failure_reason,
                }
                for r in self.stability_results
            ],
        }


class BenchmarkRunner:
    """Runner for benchmark suites."""

    def __init__(self, config: BenchmarkRunConfig | None = None):
        """Initialize runner."""
        self.config = config or BenchmarkRunConfig()
        self._sim_config = SimConfig(
            seed=self.config.seed,
            default_success_rate=self.config.default_success_rate,
        )
        self._env = SimulatedEnvironment(self._sim_config)

    async def run_all(self) -> BenchmarkRunResult:
        """Run all configured benchmarks."""
        result = BenchmarkRunResult(
            timestamp=datetime.now(timezone.utc),
            config=self.config,
        )

        if self.config.run_autonomy:
            if self.config.verbose:
                print("Running autonomy benchmarks...")
            result.autonomy_suite = await self._run_autonomy_benchmarks()

        if self.config.run_stability:
            if self.config.verbose:
                print("Running stability tests...")
            result.stability_results = await self._run_stability_tests()

        # Save results
        self._save_results(result)

        return result

    async def run_autonomy_only(self) -> BenchmarkSuite:
        """Run only autonomy benchmarks."""
        return await self._run_autonomy_benchmarks()

    async def run_stability_only(self) -> list[StabilityMetrics]:
        """Run only stability tests."""
        return await self._run_stability_tests()

    async def _run_autonomy_benchmarks(self) -> BenchmarkSuite:
        """Run autonomy benchmark suite."""
        benchmarks = AutonomyBenchmarks(self._env, self._sim_config)

        # Create test data
        goals = self._create_test_goals()
        scenarios = self._create_test_scenarios()
        task = self._create_test_task()
        loop_cases = self._create_loop_test_cases()

        suite = await benchmarks.run_all_benchmarks(
            goals=goals,
            scenarios=scenarios,
            task=task,
            loop_cases=loop_cases,
        )

        if self.config.verbose:
            self._print_autonomy_results(suite)

        return suite

    async def _run_stability_tests(self) -> list[StabilityMetrics]:
        """Run stability test suite."""
        stability = StabilityTests(self._env, self._sim_config)
        results = await stability.run_all_stability_tests()

        if self.config.verbose:
            self._print_stability_results(results)

        return results

    def _create_test_goals(self) -> list[Goal]:
        """Create test goals from scenarios."""
        return [
            Goal(
                name="research_and_report",
                description="Research AI trends and post summary to Telegram",
                expected_steps=[
                    "search_tavily",
                    "ask_perplexity",
                    "send_telegram_message",
                ],
                max_actions=10,
                success_criteria=["Summary posted", "No human intervention"],
            ),
            Goal(
                name="social_media_update",
                description="Post update to social media",
                expected_steps=["post_twitter"],
                max_actions=5,
            ),
            Goal(
                name="multi_source_research",
                description="Gather info from multiple sources",
                expected_steps=[
                    "search_tavily",
                    "ask_perplexity",
                    "search_tavily",
                ],
                max_actions=8,
            ),
            Goal(
                name="notification_task",
                description="Send notifications via multiple channels",
                expected_steps=[
                    "send_telegram_message",
                    "post_twitter",
                ],
                max_actions=6,
            ),
        ]

    def _create_test_scenarios(self) -> list[Scenario]:
        """Create failure recovery scenarios."""
        return [
            Scenario(
                name="search_rate_limit",
                description="Search API hits rate limit",
                failure_type=FailureType.RATE_LIMIT,
                affected_tools=["search_tavily"],
                expected_recovery_actions=["ask_perplexity"],
            ),
            Scenario(
                name="twitter_timeout",
                description="Twitter API times out",
                failure_type=FailureType.TIMEOUT,
                affected_tools=["post_twitter"],
                expected_recovery_actions=["send_telegram_message"],
            ),
            Scenario(
                name="perplexity_error",
                description="Perplexity returns error",
                failure_type=FailureType.API_ERROR,
                affected_tools=["ask_perplexity"],
                expected_recovery_actions=["search_tavily"],
            ),
            Scenario(
                name="network_failure",
                description="Network connectivity issues",
                failure_type=FailureType.NETWORK_ERROR,
                affected_tools=["search_tavily", "ask_perplexity"],
                expected_recovery_actions=["mcp_tool"],
            ),
        ]

    def _create_test_task(self) -> Task:
        """Create a test task for learning benchmark."""
        return Task(
            name="post_update",
            description="Post an update to social media",
            primary_tool="post_twitter",
            fallback_tools=["send_telegram_message"],
        )

    def _create_loop_test_cases(self) -> list[ActionSequence]:
        """Create loop detection test cases."""
        return [
            # True loop - same action 5 times
            ActionSequence(
                actions=[{"tool": "search_tavily", "params": {}}] * 5,
                is_loop=True,
                loop_start_index=0,
                loop_length=5,
            ),
            # Not a loop - varied actions
            ActionSequence(
                actions=[
                    {"tool": "search_tavily", "params": {}},
                    {"tool": "ask_perplexity", "params": {}},
                    {"tool": "send_telegram_message", "params": {}},
                    {"tool": "post_twitter", "params": {}},
                ],
                is_loop=False,
            ),
            # True loop - 4 repetitions
            ActionSequence(
                actions=[{"tool": "post_twitter", "params": {}}] * 4,
                is_loop=True,
                loop_start_index=0,
                loop_length=4,
            ),
            # Not a loop - alternating pattern
            ActionSequence(
                actions=[
                    {"tool": "search_tavily", "params": {}},
                    {"tool": "ask_perplexity", "params": {}},
                    {"tool": "search_tavily", "params": {}},
                    {"tool": "ask_perplexity", "params": {}},
                ],
                is_loop=False,
            ),
            # Edge case - exactly 3 (threshold)
            ActionSequence(
                actions=[{"tool": "mcp_tool", "params": {}}] * 3,
                is_loop=True,
                loop_start_index=0,
                loop_length=3,
            ),
            # Not a loop - only 2 same
            ActionSequence(
                actions=[
                    {"tool": "search_tavily", "params": {}},
                    {"tool": "search_tavily", "params": {}},
                    {"tool": "ask_perplexity", "params": {}},
                ],
                is_loop=False,
            ),
        ]

    def _save_results(self, result: BenchmarkRunResult) -> None:
        """Save benchmark results to file."""
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        timestamp_str = result.timestamp.strftime("%Y%m%d_%H%M%S")

        if self.config.output_format == "json":
            output_file = self.config.output_dir / f"benchmark_{timestamp_str}.json"
            with open(output_file, "w") as f:
                json.dump(result.to_dict(), f, indent=2)
        elif self.config.output_format == "markdown":
            output_file = self.config.output_dir / f"benchmark_{timestamp_str}.md"
            with open(output_file, "w") as f:
                f.write(self._format_markdown(result))

        if self.config.verbose:
            print(f"\nResults saved to: {output_file}")

    def _format_markdown(self, result: BenchmarkRunResult) -> str:
        """Format results as markdown."""
        lines = [
            "# Benchmark Results",
            "",
            f"**Date:** {result.timestamp.isoformat()}",
            f"**Overall Status:** {'PASSED' if result.overall_passed else 'FAILED'}",
            "",
        ]

        if result.autonomy_suite:
            lines.extend(
                [
                    "## Autonomy Benchmarks",
                    "",
                    f"**Pass Rate:** {result.autonomy_suite.pass_rate:.1%}",
                    "",
                    "| Benchmark | Metric | Value | Target | Status |",
                    "|-----------|--------|-------|--------|--------|",
                ]
            )
            for r in result.autonomy_suite.results:
                status = "PASS" if r.passed else "FAIL"
                lines.append(
                    f"| {r.benchmark_name} | {r.metric_name} | "
                    f"{r.value:.2f} | {r.target:.2f} | {status} |"
                )
            lines.append("")

        if result.stability_results:
            lines.extend(
                [
                    "## Stability Tests",
                    "",
                    "| Test | Duration | Success Rate | Memory Growth | Status |",
                    "|------|----------|--------------|---------------|--------|",
                ]
            )
            for r in result.stability_results:
                status = "PASS" if r.passed else "FAIL"
                lines.append(
                    f"| {r.test_name} | {r.duration_seconds:.1f}s | "
                    f"{r.success_rate:.1%} | {r.memory_growth_mb:.1f}MB | {status} |"
                )
            lines.append("")

        return "\n".join(lines)

    def _print_autonomy_results(self, suite: BenchmarkSuite) -> None:
        """Print autonomy results to console."""
        print("\n=== Autonomy Benchmark Results ===")
        print(f"Pass Rate: {suite.pass_rate:.1%}\n")

        for result in suite.results:
            status = "PASS" if result.passed else "FAIL"
            print(f"  {result.benchmark_name}:")
            print(
                f"    {result.metric_name}: {result.value:.3f} (target: {result.target:.3f}) [{status}]"
            )

    def _print_stability_results(self, results: list[StabilityMetrics]) -> None:
        """Print stability results to console."""
        print("\n=== Stability Test Results ===\n")

        for result in results:
            status = "PASS" if result.passed else "FAIL"
            print(f"  {result.test_name}: [{status}]")
            print(f"    Duration: {result.duration_seconds:.1f}s")
            print(f"    Success Rate: {result.success_rate:.1%}")
            print(f"    Memory Growth: {result.memory_growth_mb:.1f}MB")
            if result.failure_reason:
                print(f"    Failure: {result.failure_reason}")
            print()


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Run Nevron benchmarks")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("benchmarks/results"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "console"],
        default="json",
        help="Output format",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--autonomy-only",
        action="store_true",
        help="Run only autonomy benchmarks",
    )
    parser.add_argument(
        "--stability-only",
        action="store_true",
        help="Run only stability tests",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility",
    )

    args = parser.parse_args()

    config = BenchmarkRunConfig(
        output_dir=args.output_dir,
        output_format=args.format,
        verbose=args.verbose,
        run_autonomy=not args.stability_only,
        run_stability=not args.autonomy_only,
        seed=args.seed,
    )

    runner = BenchmarkRunner(config)

    try:
        result = asyncio.run(runner.run_all())
        if result.overall_passed:
            print("\nAll benchmarks PASSED")
            return 0
        else:
            print("\nSome benchmarks FAILED")
            return 1
    except KeyboardInterrupt:
        print("\nBenchmark run interrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
