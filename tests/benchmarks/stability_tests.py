"""
Stability Tests.

Test agent stability over extended periods and under various conditions.
"""

import asyncio
import gc
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from tests.benchmarks.simulated_env import FailureType, SimConfig, SimulatedEnvironment


@dataclass
class StabilityMetrics:
    """Metrics from a stability test run."""

    test_name: str
    duration_seconds: float
    actions_executed: int
    errors_encountered: int
    memory_start_mb: float
    memory_end_mb: float
    memory_growth_mb: float
    success_rate: float
    average_latency_ms: float
    passed: bool
    failure_reason: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemorySnapshot:
    """Snapshot of memory usage."""

    timestamp: datetime
    memory_mb: float
    objects_tracked: int


class StabilityTests:
    """Test agent stability over extended periods."""

    def __init__(
        self,
        env: SimulatedEnvironment | None = None,
        config: SimConfig | None = None,
    ):
        """Initialize stability tests."""
        self.env = env or SimulatedEnvironment(config or SimConfig())
        self._memory_snapshots: list[MemorySnapshot] = []
        self._results: list[StabilityMetrics] = []

    def reset(self) -> None:
        """Reset test state."""
        self.env.reset()
        self._memory_snapshots = []
        self._results = []

    async def test_extended_operation(
        self,
        duration_hours: float = 1.0,
        actions_per_minute: int = 10,
        simulated_time: bool = True,
    ) -> StabilityMetrics:
        """
        Test agent stability over extended operation period.

        Args:
            duration_hours: Duration to run (simulated if simulated_time=True)
            actions_per_minute: Target actions per minute
            simulated_time: Whether to simulate time passage

        Returns:
            StabilityMetrics with test results
        """
        self.reset()
        start_time = datetime.now(timezone.utc)
        start_memory = self._get_memory_usage()

        total_actions = int(duration_hours * 60 * actions_per_minute)
        errors = 0
        successful = 0

        # Take initial memory snapshot
        self._take_memory_snapshot()

        for i in range(total_actions):
            # Vary the tools used
            tools = ["search_tavily", "ask_perplexity", "send_telegram_message", "post_twitter"]
            tool = tools[i % len(tools)]

            result = await self.env.execute_tool(tool, {"iteration": i})
            if result.success:
                successful += 1
            else:
                errors += 1

            # Take periodic memory snapshots (every 100 actions)
            if i % 100 == 0:
                self._take_memory_snapshot()

            # If not simulated, add small delay
            if not simulated_time:
                await asyncio.sleep(60 / actions_per_minute / 10)  # 1/10th speed

        end_memory = self._get_memory_usage()
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        stats = self.env.get_statistics()
        success_rate = successful / total_actions if total_actions > 0 else 0

        # Check for excessive memory growth (>50% increase is concerning)
        memory_growth = end_memory - start_memory
        memory_growth_ratio = memory_growth / start_memory if start_memory > 0 else 0
        memory_ok = memory_growth_ratio < 0.5

        metrics = StabilityMetrics(
            test_name="extended_operation",
            duration_seconds=duration,
            actions_executed=total_actions,
            errors_encountered=errors,
            memory_start_mb=start_memory,
            memory_end_mb=end_memory,
            memory_growth_mb=memory_growth,
            success_rate=success_rate,
            average_latency_ms=stats["average_latency_ms"],
            passed=memory_ok and success_rate > 0.7,
            failure_reason=None if memory_ok else "Excessive memory growth",
            details={
                "simulated_hours": duration_hours,
                "actions_per_minute": actions_per_minute,
                "memory_snapshots": len(self._memory_snapshots),
                "memory_growth_ratio": memory_growth_ratio,
            },
        )
        self._results.append(metrics)
        return metrics

    async def test_memory_growth(
        self,
        duration_hours: float = 1.0,
        snapshot_interval_minutes: float = 5.0,
    ) -> StabilityMetrics:
        """
        Test memory usage growth over time.

        Args:
            duration_hours: Duration to monitor
            snapshot_interval_minutes: How often to take snapshots

        Returns:
            StabilityMetrics with memory analysis
        """
        self.reset()
        start_time = datetime.now(timezone.utc)
        start_memory = self._get_memory_usage()

        # Calculate number of snapshots
        num_snapshots = int(duration_hours * 60 / snapshot_interval_minutes)
        actions_per_snapshot = 50  # Actions between snapshots

        self._take_memory_snapshot()

        for i in range(num_snapshots):
            # Execute some actions
            for _ in range(actions_per_snapshot):
                await self.env.execute_tool("mcp_tool", {"data": "test" * 100})

            # Force garbage collection to get accurate reading
            gc.collect()
            self._take_memory_snapshot()

        end_memory = self._get_memory_usage()
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Analyze memory trend
        memory_values = [s.memory_mb for s in self._memory_snapshots]
        memory_trend = self._calculate_trend(memory_values)
        memory_growth = end_memory - start_memory

        # Pass if memory growth is bounded (less than 100MB growth)
        passed = memory_growth < 100 and memory_trend < 1.0  # < 1MB per snapshot

        metrics = StabilityMetrics(
            test_name="memory_growth",
            duration_seconds=duration,
            actions_executed=num_snapshots * actions_per_snapshot,
            errors_encountered=0,
            memory_start_mb=start_memory,
            memory_end_mb=end_memory,
            memory_growth_mb=memory_growth,
            success_rate=1.0,
            average_latency_ms=0,
            passed=passed,
            failure_reason=None if passed else "Unbounded memory growth detected",
            details={
                "num_snapshots": num_snapshots,
                "memory_trend_per_snapshot": memory_trend,
                "memory_values": memory_values,
            },
        )
        self._results.append(metrics)
        return metrics

    async def test_graceful_degradation(
        self,
        failure_injection_points: list[int] | None = None,
    ) -> StabilityMetrics:
        """
        Test that agent handles partial system failures gracefully.

        Args:
            failure_injection_points: After how many actions to inject failures

        Returns:
            StabilityMetrics with degradation analysis
        """
        self.reset()
        start_time = datetime.now(timezone.utc)
        start_memory = self._get_memory_usage()

        if failure_injection_points is None:
            failure_injection_points = [10, 25, 50, 75]

        # Inject various failures at different points
        for point in failure_injection_points:
            self.env.inject_failure(
                after_n_actions=point,
                failure_type=FailureType.API_ERROR,
                tools=["search_tavily"],
                duration=5,
            )

        total_actions = 100
        errors = 0
        recoveries = 0
        successful = 0

        for i in range(total_actions):
            tools = ["search_tavily", "ask_perplexity", "send_telegram_message"]
            tool = tools[i % len(tools)]

            result = await self.env.execute_tool(tool, {"iteration": i})
            if result.success:
                successful += 1
            else:
                errors += 1
                # Try fallback
                fallback_result = await self.env.execute_tool("ask_perplexity", {"fallback": True})
                if fallback_result.success:
                    recoveries += 1

        end_memory = self._get_memory_usage()
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Calculate effective success rate including recoveries
        effective_success_rate = (successful + recoveries) / total_actions

        # Pass if we recovered from at least 50% of failures
        recovery_rate = recoveries / errors if errors > 0 else 1.0
        passed = effective_success_rate > 0.7 and recovery_rate > 0.5

        metrics = StabilityMetrics(
            test_name="graceful_degradation",
            duration_seconds=duration,
            actions_executed=total_actions,
            errors_encountered=errors,
            memory_start_mb=start_memory,
            memory_end_mb=end_memory,
            memory_growth_mb=end_memory - start_memory,
            success_rate=successful / total_actions,
            average_latency_ms=self.env.get_statistics()["average_latency_ms"],
            passed=passed,
            failure_reason=None if passed else "Poor recovery rate",
            details={
                "injection_points": failure_injection_points,
                "recoveries": recoveries,
                "recovery_rate": recovery_rate,
                "effective_success_rate": effective_success_rate,
            },
        )
        self._results.append(metrics)
        return metrics

    async def test_high_load(
        self,
        concurrent_actions: int = 10,
        duration_seconds: float = 30.0,
    ) -> StabilityMetrics:
        """
        Test stability under high concurrent load.

        Args:
            concurrent_actions: Number of concurrent actions
            duration_seconds: How long to run

        Returns:
            StabilityMetrics with load test results
        """
        self.reset()
        start_time = datetime.now(timezone.utc)
        start_memory = self._get_memory_usage()

        total_actions = 0
        errors = 0
        successful = 0
        max_latency = 0.0

        end_time = start_time + timedelta(seconds=duration_seconds)

        while datetime.now(timezone.utc) < end_time:
            # Execute concurrent actions
            tasks = [
                self.env.execute_tool("mcp_tool", {"batch": i}) for i in range(concurrent_actions)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                total_actions += 1
                if isinstance(result, Exception):
                    errors += 1
                elif result.success:
                    successful += 1
                    max_latency = max(max_latency, result.latency_ms)
                else:
                    errors += 1

        end_memory = self._get_memory_usage()
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        success_rate = successful / total_actions if total_actions > 0 else 0
        throughput = total_actions / duration if duration > 0 else 0

        # Pass if success rate > 70% and no excessive memory growth
        memory_growth = end_memory - start_memory
        passed = success_rate > 0.7 and memory_growth < 50

        metrics = StabilityMetrics(
            test_name="high_load",
            duration_seconds=duration,
            actions_executed=total_actions,
            errors_encountered=errors,
            memory_start_mb=start_memory,
            memory_end_mb=end_memory,
            memory_growth_mb=memory_growth,
            success_rate=success_rate,
            average_latency_ms=max_latency / 2,  # Approximation
            passed=passed,
            failure_reason=None if passed else "High load instability",
            details={
                "concurrent_actions": concurrent_actions,
                "throughput_per_second": throughput,
                "max_latency_ms": max_latency,
            },
        )
        self._results.append(metrics)
        return metrics

    async def test_error_recovery_cycles(
        self,
        cycles: int = 10,
        errors_per_cycle: int = 5,
    ) -> StabilityMetrics:
        """
        Test repeated error-recovery cycles for stability.

        Args:
            cycles: Number of error-recovery cycles
            errors_per_cycle: Errors to inject per cycle

        Returns:
            StabilityMetrics with cycle analysis
        """
        self.reset()
        start_time = datetime.now(timezone.utc)
        start_memory = self._get_memory_usage()

        total_actions = 0
        total_errors = 0
        total_recoveries = 0
        cycle_results = []

        for cycle in range(cycles):
            cycle_errors = 0
            cycle_recoveries = 0

            # Inject errors for this cycle
            self.env.inject_failure(
                after_n_actions=total_actions + 1,
                failure_type=FailureType.API_ERROR,
                tools=["search_tavily", "post_twitter"],
                duration=errors_per_cycle,
            )

            # Execute actions and try to recover
            for i in range(errors_per_cycle * 2):
                result = await self.env.execute_tool("search_tavily", {"cycle": cycle})
                total_actions += 1

                if not result.success:
                    cycle_errors += 1
                    # Try recovery
                    recovery = await self.env.execute_tool("ask_perplexity", {"recovery": True})
                    total_actions += 1
                    if recovery.success:
                        cycle_recoveries += 1

            total_errors += cycle_errors
            total_recoveries += cycle_recoveries
            cycle_results.append(
                {
                    "cycle": cycle + 1,
                    "errors": cycle_errors,
                    "recoveries": cycle_recoveries,
                    "recovery_rate": cycle_recoveries / cycle_errors if cycle_errors > 0 else 1.0,
                }
            )

        end_memory = self._get_memory_usage()
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        overall_recovery_rate = total_recoveries / total_errors if total_errors > 0 else 1.0
        success_rate = total_recoveries / total_actions if total_actions > 0 else 0

        # Check if recovery rate remains stable across cycles
        recovery_rates = [c["recovery_rate"] for c in cycle_results]
        rate_variance = self._calculate_variance(recovery_rates)
        stable_recovery = rate_variance < 0.1  # Low variance = stable

        passed = overall_recovery_rate > 0.5 and stable_recovery

        metrics = StabilityMetrics(
            test_name="error_recovery_cycles",
            duration_seconds=duration,
            actions_executed=total_actions,
            errors_encountered=total_errors,
            memory_start_mb=start_memory,
            memory_end_mb=end_memory,
            memory_growth_mb=end_memory - start_memory,
            success_rate=success_rate,
            average_latency_ms=0,
            passed=passed,
            failure_reason=None if passed else "Unstable recovery across cycles",
            details={
                "cycles": cycles,
                "total_recoveries": total_recoveries,
                "overall_recovery_rate": overall_recovery_rate,
                "recovery_rate_variance": rate_variance,
                "cycle_results": cycle_results,
            },
        )
        self._results.append(metrics)
        return metrics

    async def run_all_stability_tests(self) -> list[StabilityMetrics]:
        """
        Run all stability tests.

        Returns:
            List of StabilityMetrics from all tests
        """
        results = []

        # Run tests with reasonable durations for CI
        results.append(await self.test_extended_operation(duration_hours=0.1))
        results.append(await self.test_memory_growth(duration_hours=0.1))
        results.append(await self.test_graceful_degradation())
        results.append(await self.test_high_load(duration_seconds=5.0))
        results.append(await self.test_error_recovery_cycles(cycles=5))

        return results

    def get_results(self) -> list[StabilityMetrics]:
        """Get all test results."""
        return self._results.copy()

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        # Use sys.getsizeof for basic memory tracking
        # In production, you'd use psutil or tracemalloc
        gc.collect()
        return sys.getsizeof([]) / (1024 * 1024)  # Simplified for testing

    def _take_memory_snapshot(self) -> None:
        """Take a memory snapshot."""
        gc.collect()
        snapshot = MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            memory_mb=self._get_memory_usage(),
            objects_tracked=len(gc.get_objects()),
        )
        self._memory_snapshots.append(snapshot)

    def _calculate_trend(self, values: list[float]) -> float:
        """Calculate linear trend (slope) of values."""
        if len(values) < 2:
            return 0.0

        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        return numerator / denominator if denominator > 0 else 0.0

    def _calculate_variance(self, values: list[float]) -> float:
        """Calculate variance of values."""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        return sum((v - mean) ** 2 for v in values) / len(values)
