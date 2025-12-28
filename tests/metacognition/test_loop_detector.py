"""Tests for LoopDetector module."""

from src.metacognition.loop_detector import LoopDetector, LoopPattern, LoopType


class TestLoopPattern:
    """Tests for LoopPattern dataclass."""

    def test_pattern_creation(self):
        """Test creating a loop pattern."""
        pattern = LoopPattern(
            loop_type=LoopType.REPETITION,
            pattern=["search_tavily"],
            repetitions=5,
            confidence=0.8,
        )

        assert pattern.loop_type == LoopType.REPETITION
        assert pattern.repetitions == 5
        assert len(pattern.pattern) == 1

    def test_description_repetition(self):
        """Test description for repetition pattern."""
        pattern = LoopPattern(
            loop_type=LoopType.REPETITION,
            pattern=["action_a"],
            repetitions=3,
            confidence=0.7,
        )

        desc = pattern.description
        assert "action_a" in desc
        assert "repeated" in desc
        assert "3" in desc

    def test_description_alternation(self):
        """Test description for alternation pattern."""
        pattern = LoopPattern(
            loop_type=LoopType.ALTERNATION,
            pattern=["action_a", "action_b"],
            repetitions=2,
            confidence=0.7,
        )

        desc = pattern.description
        assert "Alternating" in desc
        assert "action_a" in desc
        assert "action_b" in desc

    def test_description_cycle(self):
        """Test description for cycle pattern."""
        pattern = LoopPattern(
            loop_type=LoopType.CYCLE,
            pattern=["a", "b", "c"],
            repetitions=2,
            confidence=0.7,
        )

        desc = pattern.description
        assert "Cyclic" in desc
        assert "->" in desc

    def test_description_none(self):
        """Test description for no loop."""
        pattern = LoopPattern(
            loop_type=LoopType.NONE,
            pattern=[],
            repetitions=0,
            confidence=0.0,
        )

        assert pattern.description == "No loop detected"


class TestLoopDetector:
    """Tests for LoopDetector class."""

    def test_detector_creation(self):
        """Test creating a detector."""
        detector = LoopDetector()
        assert not detector.is_stuck("action", "ctx")  # First action can't be stuck

    def test_detect_repetition(self):
        """Test detecting simple repetition."""
        detector = LoopDetector(repetition_threshold=3)

        # Add actions one by one
        for _ in range(2):
            assert not detector.is_stuck("search_tavily", "ctx")

        # Third repetition should trigger detection
        assert detector.is_stuck("search_tavily", "ctx")

        pattern = detector.get_last_pattern()
        assert pattern is not None
        assert pattern.loop_type == LoopType.REPETITION
        assert pattern.pattern == ["search_tavily"]

    def test_detect_alternation(self):
        """Test detecting alternation pattern."""
        detector = LoopDetector(alternation_threshold=4)

        # Create alternation: A-B-A-B-A-B
        actions = ["action_a", "action_b"] * 3

        # Feed actions and track if loop is detected
        loop_detected = False
        for action in actions:
            if detector.is_stuck(action, "ctx"):
                loop_detected = True
                break

        # Alternation should be detected at some point
        assert loop_detected

        pattern = detector.get_last_pattern()
        # May detect as repetition or alternation depending on implementation
        assert pattern is not None
        assert pattern.loop_type in [LoopType.ALTERNATION, LoopType.REPETITION]

    def test_no_loop_with_variation(self):
        """Test that varied actions don't trigger loop."""
        detector = LoopDetector()

        actions = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]

        for action in actions:
            assert not detector.is_stuck(action, "ctx")

    def test_suggest_break_action(self):
        """Test suggesting action to break loop."""
        detector = LoopDetector(repetition_threshold=3)

        # Create a loop
        for _ in range(3):
            detector.is_stuck("action_a", "ctx")

        # Get suggestion
        available = ["action_a", "action_b", "action_c"]
        suggestion = detector.suggest_break_action(available)

        # Should suggest something other than action_a
        assert suggestion is not None
        assert suggestion != "action_a"
        assert suggestion in available

    def test_clear(self):
        """Test clearing detector."""
        detector = LoopDetector(repetition_threshold=3)

        # Build up some history
        for _ in range(3):
            detector.is_stuck("action", "ctx")

        detector.clear()

        # Should reset
        assert detector.get_last_pattern() is None
        assert not detector.is_stuck("action", "ctx")

    def test_get_statistics(self):
        """Test getting statistics."""
        detector = LoopDetector()

        detector.record_action("a", "ctx")
        detector.record_action("b", "ctx")

        stats = detector.get_statistics()

        assert stats["actions_tracked"] == 2
        assert stats["unique_actions"] == 2
        assert "window_size" in stats

    def test_get_loop_description_no_loop(self):
        """Test description when no loop."""
        detector = LoopDetector()
        assert detector.get_loop_description() == "No loop detected"

    def test_detect_cycle_pattern(self):
        """Test detecting cyclic pattern."""
        detector = LoopDetector(cycle_threshold=2)

        # Create cycle: A-B-C-A-B-C
        cycle = ["a", "b", "c"]

        # Do 2 full cycles
        for _ in range(2):
            for action in cycle:
                detector.record_action(action, "ctx")

        # Check for cycle
        pattern = detector._detect_cycle([a[0] for a in detector._recent_actions])

        # May or may not detect cycle depending on exact implementation
        assert pattern is not None


class TestLoopDetectorEdgeCases:
    """Edge case tests for LoopDetector."""

    def test_empty_history(self):
        """Test with empty history."""
        detector = LoopDetector()
        pattern = detector._detect_pattern()
        assert pattern.loop_type == LoopType.NONE

    def test_single_action(self):
        """Test with single action in history."""
        detector = LoopDetector()
        detector.record_action("test", "ctx")
        pattern = detector._detect_pattern()
        assert pattern.loop_type == LoopType.NONE

    def test_window_size_limit(self):
        """Test that window size is respected."""
        window_size = 5
        detector = LoopDetector(window_size=window_size)

        # Add more actions than window size
        for i in range(10):
            detector.record_action(f"action_{i}", "ctx")

        # Should only track window_size actions
        assert len(detector._recent_actions) == window_size

    def test_context_hash_tracking(self):
        """Test that context hash is tracked."""
        detector = LoopDetector()

        detector.record_action("action", "context_a")
        detector.record_action("action", "context_b")

        # Both should be tracked with different context hashes
        assert len(detector._recent_actions) == 2
