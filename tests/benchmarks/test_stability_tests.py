"""Tests for stability tests framework."""

import pytest

from tests.benchmarks.simulated_env import SimConfig
from tests.benchmarks.stability_tests import MemorySnapshot, StabilityMetrics, StabilityTests


class TestStabilityMetrics:
    """Tests for StabilityMetrics dataclass."""

    def test_passed_metrics(self):
        """Test passed stability metrics."""
        metrics = StabilityMetrics(
            test_name="test",
            duration_seconds=10.0,
            actions_executed=100,
            errors_encountered=5,
            memory_start_mb=50.0,
            memory_end_mb=55.0,
            memory_growth_mb=5.0,
            success_rate=0.95,
            average_latency_ms=50.0,
            passed=True,
        )

        assert metrics.passed is True
        assert metrics.success_rate == 0.95

    def test_failed_metrics(self):
        """Test failed stability metrics."""
        metrics = StabilityMetrics(
            test_name="test",
            duration_seconds=10.0,
            actions_executed=100,
            errors_encountered=50,
            memory_start_mb=50.0,
            memory_end_mb=150.0,
            memory_growth_mb=100.0,
            success_rate=0.50,
            average_latency_ms=500.0,
            passed=False,
            failure_reason="High memory growth",
        )

        assert metrics.passed is False
        assert metrics.failure_reason == "High memory growth"


class TestMemorySnapshot:
    """Tests for MemorySnapshot dataclass."""

    def test_snapshot_creation(self):
        """Test memory snapshot creation."""
        from datetime import datetime, timezone

        snapshot = MemorySnapshot(
            timestamp=datetime.now(timezone.utc),
            memory_mb=100.0,
            objects_tracked=5000,
        )

        assert snapshot.memory_mb == 100.0
        assert snapshot.objects_tracked == 5000


class TestStabilityTests:
    """Tests for StabilityTests class."""

    @pytest.fixture
    def stability(self):
        """Create stability tests instance."""
        config = SimConfig(seed=42, default_success_rate=0.9)
        return StabilityTests(config=config)

    @pytest.mark.asyncio
    async def test_extended_operation(self, stability):
        """Test extended operation stability test."""
        metrics = await stability.test_extended_operation(
            duration_hours=0.01,  # Very short for testing
            actions_per_minute=60,
            simulated_time=True,
        )

        assert isinstance(metrics, StabilityMetrics)
        assert metrics.test_name == "extended_operation"
        assert metrics.actions_executed > 0

    @pytest.mark.asyncio
    async def test_memory_growth(self, stability):
        """Test memory growth test."""
        metrics = await stability.test_memory_growth(
            duration_hours=0.01,
            snapshot_interval_minutes=0.5,
        )

        assert isinstance(metrics, StabilityMetrics)
        assert metrics.test_name == "memory_growth"
        assert "num_snapshots" in metrics.details

    @pytest.mark.asyncio
    async def test_graceful_degradation(self, stability):
        """Test graceful degradation test."""
        metrics = await stability.test_graceful_degradation(
            failure_injection_points=[5, 15, 30],
        )

        assert isinstance(metrics, StabilityMetrics)
        assert metrics.test_name == "graceful_degradation"
        assert "recovery_rate" in metrics.details

    @pytest.mark.asyncio
    async def test_high_load(self, stability):
        """Test high load test."""
        metrics = await stability.test_high_load(
            concurrent_actions=5,
            duration_seconds=1.0,
        )

        assert isinstance(metrics, StabilityMetrics)
        assert metrics.test_name == "high_load"
        assert "throughput_per_second" in metrics.details

    @pytest.mark.asyncio
    async def test_error_recovery_cycles(self, stability):
        """Test error recovery cycles test."""
        metrics = await stability.test_error_recovery_cycles(
            cycles=3,
            errors_per_cycle=2,
        )

        assert isinstance(metrics, StabilityMetrics)
        assert metrics.test_name == "error_recovery_cycles"
        assert "cycle_results" in metrics.details

    @pytest.mark.asyncio
    async def test_run_all_stability_tests(self, stability):
        """Test running all stability tests."""
        results = await stability.run_all_stability_tests()

        assert len(results) >= 5
        assert all(isinstance(r, StabilityMetrics) for r in results)

    def test_reset(self, stability):
        """Test stability tests reset."""
        stability._memory_snapshots = [1, 2, 3]
        stability._results = [1, 2, 3]

        stability.reset()

        assert len(stability._memory_snapshots) == 0
        assert len(stability._results) == 0

    def test_calculate_trend(self, stability):
        """Test trend calculation."""
        # Increasing trend
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        trend = stability._calculate_trend(values)
        assert trend > 0

        # Decreasing trend
        values = [5.0, 4.0, 3.0, 2.0, 1.0]
        trend = stability._calculate_trend(values)
        assert trend < 0

        # Flat trend
        values = [3.0, 3.0, 3.0, 3.0]
        trend = stability._calculate_trend(values)
        assert abs(trend) < 0.01

    def test_calculate_variance(self, stability):
        """Test variance calculation."""
        # High variance
        values = [1.0, 10.0, 1.0, 10.0]
        variance = stability._calculate_variance(values)
        assert variance > 10

        # Low variance
        values = [5.0, 5.1, 4.9, 5.0]
        variance = stability._calculate_variance(values)
        assert variance < 0.1

        # Zero variance
        values = [5.0, 5.0, 5.0]
        variance = stability._calculate_variance(values)
        assert variance == 0.0
