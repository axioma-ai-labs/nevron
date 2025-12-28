"""
Integration tests for Metacognitive Monitor.

Tests that metacognition properly monitors agent behavior
and intervenes when necessary.

NOTE: These tests describe the intended API for metacognitive monitoring.
Some APIs may not be fully implemented yet.
"""

import pytest


# Skip entire module if imports fail (APIs not implemented yet)
try:
    from src.metacognition.monitor import (
        ActionRecord,
        ConfidenceLevel,
        InterventionType,
        MetacognitiveMonitor,
        MonitorConfig,
    )
except ImportError as e:
    pytest.skip(
        f"Metacognition integration tests require unimplemented API: {e}",
        allow_module_level=True,
    )


class TestMetacognitionIntervention:
    """Test metacognition interrupts appropriately."""

    @pytest.fixture
    def monitor(self):
        """Create metacognitive monitor instance."""
        config = MonitorConfig(
            loop_detection_threshold=3,
            confidence_threshold=0.4,
            max_consecutive_failures=3,
            intervention_cooldown=0.0,  # No cooldown for tests
        )
        return MetacognitiveMonitor(config=config)

    @pytest.mark.asyncio
    async def test_loop_detection_triggers_intervention(self, monitor):
        """Test that repetitive actions cause replanning."""
        # Record same action multiple times
        for i in range(5):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"action-{i}",
                    action_type="search_tavily",
                    parameters={"query": "same query"},
                    success=True,
                    duration_ms=100,
                )
            )

        # Check for loop detection
        result = await monitor.analyze()

        assert result is not None
        assert result.loop_detected is True
        assert result.intervention_needed is True
        assert result.intervention_type == InterventionType.REPLAN

    @pytest.mark.asyncio
    async def test_varied_actions_no_loop(self, monitor):
        """Test that varied actions don't trigger loop detection."""
        actions = ["search_tavily", "ask_perplexity", "send_message", "post_twitter"]

        for i, action in enumerate(actions):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"action-{i}",
                    action_type=action,
                    parameters={},
                    success=True,
                    duration_ms=100,
                )
            )

        result = await monitor.analyze()

        assert result.loop_detected is False
        assert result.intervention_needed is False

    @pytest.mark.asyncio
    async def test_low_confidence_triggers_handoff(self, monitor):
        """Test that uncertain situations request help."""
        # Simulate low confidence scenario
        await monitor.set_confidence(ConfidenceLevel.LOW)

        # Record an uncertain action
        await monitor.record_action(
            ActionRecord(
                action_id="uncertain-action",
                action_type="complex_task",
                parameters={"confidence": 0.2},
                success=False,
                duration_ms=500,
            )
        )

        result = await monitor.analyze()

        assert result.confidence_level == ConfidenceLevel.LOW
        assert result.intervention_needed is True
        assert result.intervention_type == InterventionType.HUMAN_HANDOFF

    @pytest.mark.asyncio
    async def test_consecutive_failures_trigger_intervention(self, monitor):
        """Test that multiple failures trigger intervention."""
        # Record consecutive failures
        for i in range(4):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"failed-{i}",
                    action_type="failing_action",
                    parameters={},
                    success=False,
                    error="Action failed",
                    duration_ms=100,
                )
            )

        result = await monitor.analyze()

        assert result.failure_streak >= 3
        assert result.intervention_needed is True

    @pytest.mark.asyncio
    async def test_success_resets_failure_streak(self, monitor):
        """Test that success resets the failure counter."""
        # Record some failures
        for i in range(2):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"failed-{i}",
                    action_type="action",
                    parameters={},
                    success=False,
                    duration_ms=100,
                )
            )

        # Record a success
        await monitor.record_action(
            ActionRecord(
                action_id="success-1",
                action_type="action",
                parameters={},
                success=True,
                duration_ms=100,
            )
        )

        result = await monitor.analyze()

        assert result.failure_streak == 0

    @pytest.mark.asyncio
    async def test_goal_progress_monitoring(self, monitor):
        """Test that goal progress is tracked."""
        # Set a goal
        await monitor.set_current_goal(
            goal_id="goal-001",
            description="Complete research task",
            expected_steps=5,
        )

        # Record progress
        for i in range(3):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"progress-{i}",
                    action_type="step_action",
                    parameters={},
                    success=True,
                    duration_ms=100,
                    contributes_to_goal=True,
                )
            )

        progress = await monitor.get_goal_progress("goal-001")

        assert progress is not None
        assert progress["steps_completed"] == 3
        assert progress["steps_remaining"] == 2
        assert progress["completion_percentage"] == 60.0

    @pytest.mark.asyncio
    async def test_stalled_progress_detection(self, monitor):
        """Test detection of stalled progress."""
        await monitor.set_current_goal(
            goal_id="goal-002",
            description="Stalling goal",
            expected_steps=5,
        )

        # Record actions that don't contribute to goal
        for i in range(5):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"non-progress-{i}",
                    action_type="unrelated_action",
                    parameters={},
                    success=True,
                    duration_ms=100,
                    contributes_to_goal=False,
                )
            )

        result = await monitor.analyze()

        assert result.progress_stalled is True
        assert result.intervention_needed is True

    @pytest.mark.asyncio
    async def test_resource_monitoring(self, monitor):
        """Test monitoring of resource usage."""
        # Simulate resource-intensive actions
        for i in range(10):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"resource-{i}",
                    action_type="api_call",
                    parameters={},
                    success=True,
                    duration_ms=1000,
                    resource_usage={"api_calls": 1, "tokens": 500},
                )
            )

        resources = await monitor.get_resource_usage()

        assert resources["total_api_calls"] == 10
        assert resources["total_tokens"] == 5000
        assert resources["average_duration_ms"] == 1000

    @pytest.mark.asyncio
    async def test_intervention_recommendations(self, monitor):
        """Test that appropriate interventions are recommended."""
        # Create a complex situation
        await monitor.set_confidence(ConfidenceLevel.MEDIUM)

        # Record a loop
        for i in range(4):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"loop-{i}",
                    action_type="repeated_action",
                    parameters={"same": "params"},
                    success=True,
                    duration_ms=100,
                )
            )

        result = await monitor.analyze()

        # Should recommend specific intervention
        assert result.intervention_needed is True
        assert result.recommendation is not None
        assert len(result.recommendation) > 0


class TestMetacognitiveAnalysis:
    """Test metacognitive analysis capabilities."""

    @pytest.fixture
    def monitor(self):
        """Create monitor with default config."""
        return MetacognitiveMonitor()

    @pytest.mark.asyncio
    async def test_action_pattern_analysis(self, monitor):
        """Test analysis of action patterns."""
        # Record a pattern of actions
        pattern = [
            ("search", {"query": "topic A"}),
            ("analyze", {"data": "results"}),
            ("post", {"content": "summary"}),
        ]

        for i, (action, params) in enumerate(pattern):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"pattern-{i}",
                    action_type=action,
                    parameters=params,
                    success=True,
                    duration_ms=100,
                )
            )

        patterns = await monitor.analyze_patterns()

        assert len(patterns) >= 1
        assert patterns[0]["actions"] == ["search", "analyze", "post"]

    @pytest.mark.asyncio
    async def test_efficiency_analysis(self, monitor):
        """Test efficiency metrics analysis."""
        # Record actions with varying efficiency
        await monitor.record_action(
            ActionRecord(
                action_id="fast-1",
                action_type="quick_search",
                parameters={},
                success=True,
                duration_ms=50,
            )
        )
        await monitor.record_action(
            ActionRecord(
                action_id="slow-1",
                action_type="slow_search",
                parameters={},
                success=True,
                duration_ms=5000,
            )
        )

        efficiency = await monitor.analyze_efficiency()

        assert "quick_search" in efficiency
        assert "slow_search" in efficiency
        assert (
            efficiency["quick_search"]["avg_duration"] < efficiency["slow_search"]["avg_duration"]
        )

    @pytest.mark.asyncio
    async def test_success_rate_by_action_type(self, monitor):
        """Test success rate tracking by action type."""
        # Record mixed success for different actions
        for _ in range(5):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"reliable-{_}",
                    action_type="reliable_action",
                    parameters={},
                    success=True,
                    duration_ms=100,
                )
            )

        for i in range(5):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"unreliable-{i}",
                    action_type="unreliable_action",
                    parameters={},
                    success=i < 2,  # 40% success
                    duration_ms=100,
                )
            )

        success_rates = await monitor.get_success_rates()

        assert success_rates["reliable_action"] == 1.0
        assert success_rates["unreliable_action"] == pytest.approx(0.4, rel=0.1)

    @pytest.mark.asyncio
    async def test_anomaly_detection(self, monitor):
        """Test detection of anomalous behavior."""
        # Record normal actions
        for i in range(10):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"normal-{i}",
                    action_type="normal_action",
                    parameters={},
                    success=True,
                    duration_ms=100,
                )
            )

        # Record an anomaly (very slow action)
        await monitor.record_action(
            ActionRecord(
                action_id="anomaly-1",
                action_type="normal_action",
                parameters={},
                success=True,
                duration_ms=10000,  # 100x normal
            )
        )

        anomalies = await monitor.detect_anomalies()

        assert len(anomalies) >= 1
        assert anomalies[0]["action_id"] == "anomaly-1"
        assert anomalies[0]["type"] == "duration_anomaly"

    @pytest.mark.asyncio
    async def test_self_assessment(self, monitor):
        """Test self-assessment capabilities."""
        # Record various actions to build history
        for i in range(20):
            success = i % 4 != 0  # 75% success
            await monitor.record_action(
                ActionRecord(
                    action_id=f"assess-{i}",
                    action_type="test_action",
                    parameters={},
                    success=success,
                    duration_ms=100 + (i * 10),
                )
            )

        assessment = await monitor.self_assess()

        assert "overall_success_rate" in assessment
        assert "total_actions" in assessment
        assert "recommendations" in assessment
        assert assessment["total_actions"] == 20
        assert assessment["overall_success_rate"] == pytest.approx(0.75, rel=0.1)


class TestInterventionCooldown:
    """Test intervention cooldown behavior."""

    @pytest.mark.asyncio
    async def test_intervention_cooldown(self):
        """Test that interventions respect cooldown period."""
        config = MonitorConfig(
            loop_detection_threshold=2,
            intervention_cooldown=1.0,  # 1 second cooldown
        )
        monitor = MetacognitiveMonitor(config=config)

        # Trigger first intervention
        for i in range(3):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"loop-a-{i}",
                    action_type="looping",
                    parameters={},
                    success=True,
                    duration_ms=100,
                )
            )

        result1 = await monitor.analyze()
        assert result1.intervention_needed is True

        # Clear and try again immediately
        for i in range(3):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"loop-b-{i}",
                    action_type="looping",
                    parameters={},
                    success=True,
                    duration_ms=100,
                )
            )

        result2 = await monitor.analyze()
        # Should be on cooldown
        assert result2.on_cooldown is True

    @pytest.mark.asyncio
    async def test_critical_bypasses_cooldown(self):
        """Test that critical situations bypass cooldown."""
        config = MonitorConfig(
            intervention_cooldown=10.0,  # Long cooldown
        )
        monitor = MetacognitiveMonitor(config=config)

        # Trigger initial intervention
        await monitor.set_confidence(ConfidenceLevel.LOW)
        await monitor.analyze()

        # Create critical situation
        for i in range(5):
            await monitor.record_action(
                ActionRecord(
                    action_id=f"critical-{i}",
                    action_type="failing",
                    parameters={},
                    success=False,
                    error="Critical error",
                    duration_ms=100,
                )
            )

        await monitor.set_confidence(ConfidenceLevel.CRITICAL)
        result = await monitor.analyze()

        # Critical should bypass cooldown
        assert result.intervention_needed is True
        assert result.on_cooldown is False
