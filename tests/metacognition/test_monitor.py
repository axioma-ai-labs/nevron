"""Tests for MetacognitiveMonitor module."""

import pytest

from src.core.defs import AgentAction, AgentState
from src.learning.tracker import ActionTracker
from src.metacognition.intervention import InterventionType
from src.metacognition.monitor import MetacognitiveMonitor, MonitoringState


class TestMonitoringState:
    """Tests for MonitoringState dataclass."""

    def test_state_creation(self):
        """Test creating monitoring state."""
        state = MonitoringState()

        assert not state.is_stuck
        assert state.confidence_level == 0.5
        assert state.intervention_count == 0

    def test_state_to_dict(self):
        """Test converting state to dict."""
        state = MonitoringState(
            is_stuck=True,
            confidence_level=0.3,
            failure_risk=0.7,
        )

        result = state.to_dict()

        assert result["is_stuck"] is True
        assert result["confidence_level"] == 0.3
        assert "created_at" in result


class TestMetacognitiveMonitor:
    """Tests for MetacognitiveMonitor class."""

    def test_monitor_creation(self):
        """Test creating a monitor."""
        monitor = MetacognitiveMonitor()
        assert monitor is not None

    def test_monitor_with_tracker(self):
        """Test monitor with action tracker."""
        tracker = ActionTracker()
        monitor = MetacognitiveMonitor(action_tracker=tracker)

        assert monitor._tracker is tracker

    @pytest.mark.asyncio
    async def test_monitor_normal_action(self):
        """Test monitoring a normal action."""
        monitor = MetacognitiveMonitor()

        intervention = await monitor.monitor(
            action="search_tavily",
            agent_state=AgentState.DEFAULT,
            context={"goal": "research"},
        )

        assert intervention.type == InterventionType.CONTINUE

    @pytest.mark.asyncio
    async def test_monitor_detects_loop(self):
        """Test that monitor detects loops."""
        monitor = MetacognitiveMonitor()

        # Execute same action repeatedly
        for _ in range(3):
            intervention = await monitor.monitor(
                action="idle",
                agent_state=AgentState.DEFAULT,
                context={},
            )

        # Should detect loop
        assert intervention.type == InterventionType.BREAK_LOOP

    @pytest.mark.asyncio
    async def test_monitor_agent_action(self):
        """Test monitoring AgentAction enum."""
        monitor = MetacognitiveMonitor()

        intervention = await monitor.monitor_action(
            action=AgentAction.SEARCH_TAVILY,
            agent_state=AgentState.DEFAULT,
            context={"goal": "research"},
        )

        assert intervention.type == InterventionType.CONTINUE

    @pytest.mark.asyncio
    async def test_monitor_with_low_success_rate(self):
        """Test monitoring with low historical success rate."""
        tracker = ActionTracker()

        # Record many failures
        for _ in range(10):
            tracker.record("failing_action", "ctx", -1.0, False)

        monitor = MetacognitiveMonitor(action_tracker=tracker)

        intervention = await monitor.monitor(
            action="failing_action",
            agent_state=AgentState.DEFAULT,
            context={},
        )

        # May trigger replan, fallback, or pause due to high failure prediction
        assert intervention.type in [
            InterventionType.CONTINUE,
            InterventionType.PREEMPTIVE_REPLAN,
            InterventionType.FALLBACK,
            InterventionType.PAUSE,  # Can pause when recent failures detected
        ]

    @pytest.mark.asyncio
    async def test_monitor_consecutive_failures_abort(self):
        """Test abort after consecutive failures."""
        monitor = MetacognitiveMonitor()

        # Record many consecutive failures
        for _ in range(6):
            monitor.record_action_result("action", success=False)

        intervention = await monitor.monitor(
            action="action",
            agent_state=AgentState.DEFAULT,
            context={},
        )

        assert intervention.type == InterventionType.ABORT

    def test_record_action_result_success(self):
        """Test recording successful action."""
        monitor = MetacognitiveMonitor()

        monitor.record_action_result("action", success=True)

        assert monitor._consecutive_failures == 0

    def test_record_action_result_failure(self):
        """Test recording failed action."""
        monitor = MetacognitiveMonitor()

        monitor.record_action_result("action", success=False)
        monitor.record_action_result("action", success=False)

        assert monitor._consecutive_failures == 2

    def test_record_action_result_reset_on_success(self):
        """Test failures reset on success."""
        monitor = MetacognitiveMonitor()

        monitor.record_action_result("action", success=False)
        monitor.record_action_result("action", success=False)
        monitor.record_action_result("action", success=True)

        assert monitor._consecutive_failures == 0

    def test_get_state(self):
        """Test getting monitoring state."""
        monitor = MetacognitiveMonitor()

        state = monitor.get_state()

        assert isinstance(state, MonitoringState)
        assert not state.is_stuck

    def test_get_components(self):
        """Test getting component accessors."""
        monitor = MetacognitiveMonitor()

        assert monitor.get_loop_detector() is not None
        assert monitor.get_failure_predictor() is not None
        assert monitor.get_confidence_estimator() is not None
        assert monitor.get_human_handoff() is not None

    def test_get_intervention_history(self):
        """Test getting intervention history."""
        monitor = MetacognitiveMonitor()

        history = monitor.get_intervention_history()

        assert isinstance(history, list)

    def test_clear(self):
        """Test clearing monitor."""
        monitor = MetacognitiveMonitor()

        # Add some state
        monitor._consecutive_failures = 5

        monitor.clear()

        assert monitor._consecutive_failures == 0
        assert len(monitor._intervention_history) == 0

    def test_get_statistics(self):
        """Test getting statistics."""
        monitor = MetacognitiveMonitor()

        stats = monitor.get_statistics()

        assert "state" in stats
        assert "loop_detector" in stats
        assert "failure_predictor" in stats
        assert "handoff_enabled" in stats

    def test_estimate_confidence(self):
        """Test confidence estimation."""
        monitor = MetacognitiveMonitor()

        estimate = monitor.estimate_confidence(
            goal="Test goal",
            has_memories=True,
            success_rate=0.8,
        )

        assert estimate.level > 0.5

    def test_predict_failure(self):
        """Test failure prediction."""
        monitor = MetacognitiveMonitor()

        prediction = monitor.predict_failure("action", {})

        assert prediction.action == "action"
        assert 0.0 <= prediction.probability <= 1.0


class TestMetacognitiveMonitorIntegration:
    """Integration tests for MetacognitiveMonitor."""

    @pytest.mark.asyncio
    async def test_full_monitoring_flow(self):
        """Test full monitoring flow."""
        tracker = ActionTracker()
        monitor = MetacognitiveMonitor(action_tracker=tracker)

        # Execute various actions
        actions = ["search", "analyze", "post", "search", "idle"]

        for action in actions:
            _intervention = await monitor.monitor(
                action=action,
                agent_state=AgentState.DEFAULT,
                context={"goal": "test"},
            )

            # Record result
            monitor.record_action_result(action, success=True)

        # Check state
        state = monitor.get_state()
        assert state.actions_since_intervention > 0

    @pytest.mark.asyncio
    async def test_loop_detection_and_recovery(self):
        """Test loop detection followed by different action."""
        monitor = MetacognitiveMonitor()

        # Create a loop
        for _ in range(3):
            intervention = await monitor.monitor(
                action="stuck_action",
                agent_state=AgentState.DEFAULT,
                context={},
            )

        assert intervention.type == InterventionType.BREAK_LOOP

        # Use suggested alternative
        if intervention.suggested_action:
            intervention = await monitor.monitor(
                action=intervention.suggested_action,
                agent_state=AgentState.DEFAULT,
                context={},
            )

            # Should now be able to continue
            assert intervention.type == InterventionType.CONTINUE

    @pytest.mark.asyncio
    async def test_intervention_history_tracking(self):
        """Test that interventions are tracked."""
        monitor = MetacognitiveMonitor()

        # Trigger an intervention (loop)
        for _ in range(3):
            await monitor.monitor(
                action="repeat_action",
                agent_state=AgentState.DEFAULT,
                context={},
            )

        history = monitor.get_intervention_history()

        # Should have at least one intervention
        assert len(history) >= 1
        assert history[-1].type == InterventionType.BREAK_LOOP

    @pytest.mark.asyncio
    async def test_state_updates(self):
        """Test that state updates correctly."""
        monitor = MetacognitiveMonitor()

        await monitor.monitor(
            action="action",
            agent_state=AgentState.DEFAULT,
            context={},
        )

        first_count = monitor.get_state().actions_since_intervention

        await monitor.monitor(
            action="different_action",  # Use different action to avoid loop detection
            agent_state=AgentState.DEFAULT,
            context={},
        )

        second_count = monitor.get_state().actions_since_intervention

        # Second count should be one more than first
        assert second_count == first_count + 1
