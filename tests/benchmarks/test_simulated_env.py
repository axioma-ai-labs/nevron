"""Tests for simulated environment framework."""

import pytest

from tests.benchmarks.simulated_env import (
    FailureType,
    ScenarioRunner,
    SimConfig,
    SimulatedEnvironment,
    ToolResult,
)


class TestSimConfig:
    """Tests for SimConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SimConfig()

        assert config.default_success_rate == 0.8
        assert config.latency_range == (10.0, 100.0)
        assert config.random_failures_enabled is False
        assert config.seed is None

    def test_custom_config(self):
        """Test custom configuration."""
        config = SimConfig(
            tool_success_rates={"search": 0.9},
            default_success_rate=0.7,
            seed=42,
        )

        assert config.tool_success_rates["search"] == 0.9
        assert config.default_success_rate == 0.7
        assert config.seed == 42


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_result(self):
        """Test successful tool result."""
        result = ToolResult(
            success=True,
            data={"key": "value"},
            tool_name="test_tool",
            latency_ms=50.0,
        )

        assert result.success is True
        assert result.data["key"] == "value"
        assert result.error is None

    def test_failure_result(self):
        """Test failed tool result."""
        result = ToolResult(
            success=False,
            error="Tool failed",
            tool_name="test_tool",
            latency_ms=100.0,
        )

        assert result.success is False
        assert result.error == "Tool failed"
        assert result.data is None


class TestSimulatedEnvironment:
    """Tests for SimulatedEnvironment class."""

    @pytest.fixture
    def env(self):
        """Create environment with fixed seed for reproducibility."""
        config = SimConfig(seed=42, default_success_rate=0.8)
        return SimulatedEnvironment(config)

    @pytest.mark.asyncio
    async def test_execute_tool_success(self, env):
        """Test successful tool execution."""
        # With 80% success rate, most should succeed
        successes = 0
        for _ in range(10):
            result = await env.execute_tool("test_tool", {"param": "value"})
            if result.success:
                successes += 1

        # With seed=42, should be relatively consistent
        assert successes >= 5

    @pytest.mark.asyncio
    async def test_execute_tool_with_custom_success_rate(self):
        """Test tool with custom success rate."""
        config = SimConfig(
            tool_success_rates={"always_succeeds": 1.0, "always_fails": 0.0},
            seed=42,
        )
        env = SimulatedEnvironment(config)

        # Always succeeds tool
        for _ in range(5):
            result = await env.execute_tool("always_succeeds")
            assert result.success is True

        # Always fails tool
        for _ in range(5):
            result = await env.execute_tool("always_fails")
            assert result.success is False

    @pytest.mark.asyncio
    async def test_inject_failure(self, env):
        """Test failure injection."""
        env.inject_failure(
            after_n_actions=2,
            failure_type=FailureType.RATE_LIMIT,
            tools=["target_tool"],
            duration=2,
        )

        # First two actions should not be affected
        _result1 = await env.execute_tool("target_tool")
        _result2 = await env.execute_tool("target_tool")

        # Next two should fail due to injection
        result3 = await env.execute_tool("target_tool")
        _result4 = await env.execute_tool("target_tool")

        # After duration, should resume normal
        _result5 = await env.execute_tool("target_tool")

        # Results 3 and 4 should have rate limit error
        assert result3.success is False
        assert "rate limit" in result3.error.lower()

    @pytest.mark.asyncio
    async def test_custom_handler(self, env):
        """Test custom tool handler."""

        def custom_handler(params):
            return ToolResult(
                success=True,
                data={"custom": params.get("value", "default")},
                tool_name="custom_tool",
            )

        env.register_custom_handler("custom_tool", custom_handler)

        result = await env.execute_tool("custom_tool", {"value": "test"})

        assert result.success is True
        assert result.data["custom"] == "test"

    @pytest.mark.asyncio
    async def test_action_history(self, env):
        """Test action history tracking."""
        await env.execute_tool("tool_a", {"param": 1})
        await env.execute_tool("tool_b", {"param": 2})
        await env.execute_tool("tool_a", {"param": 3})

        history = env.get_action_history()

        assert len(history) == 3
        assert history[0].tool == "tool_a"
        assert history[1].tool == "tool_b"
        assert history[2].tool == "tool_a"

    @pytest.mark.asyncio
    async def test_statistics(self, env):
        """Test statistics tracking."""
        for i in range(10):
            await env.execute_tool("test_tool", {"i": i})

        stats = env.get_statistics()

        assert stats["total_actions"] == 10
        assert "success_rate" in stats
        assert "by_tool" in stats
        assert "test_tool" in stats["by_tool"]

    def test_reset(self, env):
        """Test environment reset."""
        env._action_count = 10
        env._action_history = [1, 2, 3]

        env.reset()

        assert env._action_count == 0
        assert len(env._action_history) == 0

    def test_create_loop_scenario(self, env):
        """Test loop scenario creation."""
        actions = env.create_loop_scenario(
            repeated_action="search",
            repetition_count=5,
            should_detect=True,
        )

        assert len(actions) == 5
        assert all(a["tool"] == "search" for a in actions)


class TestScenarioRunner:
    """Tests for ScenarioRunner class."""

    @pytest.fixture
    def runner(self):
        """Create scenario runner."""
        config = SimConfig(seed=42, default_success_rate=0.9)
        env = SimulatedEnvironment(config)
        return ScenarioRunner(env)

    @pytest.mark.asyncio
    async def test_run_scenario(self, runner):
        """Test running a scenario."""
        actions = [
            {"tool": "search", "params": {"query": "test"}},
            {"tool": "analyze", "params": {}},
            {"tool": "post", "params": {"content": "result"}},
        ]

        results = await runner.run_scenario(actions)

        assert len(results) == 3
        assert all(isinstance(r, ToolResult) for r in results)
