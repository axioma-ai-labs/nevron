"""Tests for Intervention module."""

from src.metacognition.intervention import Intervention, InterventionType


class TestInterventionType:
    """Tests for InterventionType enum."""

    def test_all_types_defined(self):
        """Test all intervention types are defined."""
        expected_types = [
            "CONTINUE",
            "BREAK_LOOP",
            "PREEMPTIVE_REPLAN",
            "HUMAN_HANDOFF",
            "PAUSE",
            "ABORT",
            "THROTTLE",
            "FALLBACK",
        ]

        for type_name in expected_types:
            assert hasattr(InterventionType, type_name)


class TestIntervention:
    """Tests for Intervention dataclass."""

    def test_continue_factory(self):
        """Test creating continue intervention."""
        intervention = Intervention.continue_execution()

        assert intervention.type == InterventionType.CONTINUE
        assert not intervention.requires_action
        assert not intervention.blocks_execution

    def test_break_loop_factory(self):
        """Test creating break loop intervention."""
        intervention = Intervention.break_loop(
            reason="Same action repeated 5 times",
            suggested_action="ask_perplexity",
            alternatives=["search_tavily", "idle"],
        )

        assert intervention.type == InterventionType.BREAK_LOOP
        assert intervention.requires_action
        assert intervention.suggested_action == "ask_perplexity"
        assert len(intervention.alternatives) == 2

    def test_human_handoff_factory(self):
        """Test creating human handoff intervention."""
        intervention = Intervention.human_handoff(
            reason="Low confidence on goal",
            context={"goal": "unclear task"},
        )

        assert intervention.type == InterventionType.HUMAN_HANDOFF
        assert intervention.blocks_execution
        assert intervention.priority == 4

    def test_pause_factory(self):
        """Test creating pause intervention."""
        intervention = Intervention.pause(
            reason="Rate limit approaching",
            wait_seconds=60.0,
        )

        assert intervention.type == InterventionType.PAUSE
        assert intervention.wait_seconds == 60.0
        assert intervention.blocks_execution

    def test_abort_factory(self):
        """Test creating abort intervention."""
        intervention = Intervention.abort(
            reason="Too many failures",
            context={"failure_count": 10},
        )

        assert intervention.type == InterventionType.ABORT
        assert intervention.is_critical
        assert intervention.priority == 5

    def test_throttle_factory(self):
        """Test creating throttle intervention."""
        intervention = Intervention.throttle(
            reason="Slow down API calls",
            wait_seconds=5.0,
        )

        assert intervention.type == InterventionType.THROTTLE
        assert intervention.wait_seconds == 5.0

    def test_fallback_factory(self):
        """Test creating fallback intervention."""
        intervention = Intervention.fallback(
            reason="Primary action unavailable",
            suggested_action="backup_action",
            alternatives=["alt1", "alt2"],
        )

        assert intervention.type == InterventionType.FALLBACK
        assert intervention.suggested_action == "backup_action"

    def test_to_dict(self):
        """Test converting intervention to dict."""
        intervention = Intervention.break_loop(
            reason="Test reason",
            suggested_action="test_action",
        )

        result = intervention.to_dict()

        assert result["type"] == "break_loop"
        assert result["reason"] == "Test reason"
        assert result["suggested_action"] == "test_action"
        assert "created_at" in result

    def test_from_dict(self):
        """Test creating intervention from dict."""
        data = {
            "type": "break_loop",
            "reason": "Test reason",
            "suggested_action": "test",
            "priority": 3,
            "created_at": "2025-01-01T00:00:00+00:00",
        }

        intervention = Intervention.from_dict(data)

        assert intervention.type == InterventionType.BREAK_LOOP
        assert intervention.reason == "Test reason"

    def test_requires_action_property(self):
        """Test requires_action property."""
        assert not Intervention.continue_execution().requires_action
        assert Intervention.break_loop("test").requires_action
        assert Intervention.abort("test").requires_action

    def test_blocks_execution_property(self):
        """Test blocks_execution property."""
        assert not Intervention.continue_execution().blocks_execution
        assert not Intervention.break_loop("test").blocks_execution
        assert Intervention.abort("test").blocks_execution
        assert Intervention.pause("test", 10).blocks_execution
        assert Intervention.human_handoff("test").blocks_execution
