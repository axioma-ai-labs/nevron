"""Loop Detector - Detect when agent is stuck in repetitive behavior.

Patterns detected:
- Same action repeated N times
- Alternating between two actions
- Cyclic patterns (A -> B -> C -> A -> B -> C)
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

from loguru import logger


class LoopType(Enum):
    """Types of detected loops."""

    NONE = "none"
    REPETITION = "repetition"  # Same action repeated
    ALTERNATION = "alternation"  # Two actions alternating
    CYCLE = "cycle"  # N actions in a repeating cycle


@dataclass
class LoopPattern:
    """Represents a detected loop pattern."""

    loop_type: LoopType
    pattern: List[str]  # Actions in the pattern
    repetitions: int  # How many times pattern repeated
    confidence: float  # How confident we are this is a loop
    first_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "loop_type": self.loop_type.value,
            "pattern": self.pattern,
            "repetitions": self.repetitions,
            "confidence": self.confidence,
            "first_seen": self.first_seen.isoformat(),
        }

    @property
    def description(self) -> str:
        """Get human-readable description of the loop."""
        if self.loop_type == LoopType.REPETITION:
            return f"Action '{self.pattern[0]}' repeated {self.repetitions} times"
        elif self.loop_type == LoopType.ALTERNATION:
            return f"Alternating between '{self.pattern[0]}' and '{self.pattern[1]}'"
        elif self.loop_type == LoopType.CYCLE:
            cycle = " -> ".join(self.pattern)
            return f"Cyclic pattern: {cycle} (repeated {self.repetitions}x)"
        return "No loop detected"


class LoopDetector:
    """Detect when agent is stuck in repetitive behavior.

    Uses sliding window analysis to detect:
    - Repetition: Same action repeated consecutively
    - Alternation: Two actions alternating (A-B-A-B)
    - Cycles: N actions repeating (A-B-C-A-B-C)
    """

    # Default detection thresholds
    DEFAULT_WINDOW_SIZE = 20
    DEFAULT_REPETITION_THRESHOLD = 3
    DEFAULT_ALTERNATION_THRESHOLD = 4  # At least 4 alternations (ABAB)
    DEFAULT_CYCLE_THRESHOLD = 2  # At least 2 full cycles

    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        repetition_threshold: int = DEFAULT_REPETITION_THRESHOLD,
        alternation_threshold: int = DEFAULT_ALTERNATION_THRESHOLD,
        cycle_threshold: int = DEFAULT_CYCLE_THRESHOLD,
    ):
        """Initialize loop detector.

        Args:
            window_size: Number of recent actions to analyze
            repetition_threshold: Min repetitions to detect loop
            alternation_threshold: Min alternations to detect
            cycle_threshold: Min full cycles to detect
        """
        self._window_size = window_size
        self._repetition_threshold = repetition_threshold
        self._alternation_threshold = alternation_threshold
        self._cycle_threshold = cycle_threshold

        # Track recent actions with context hashes
        self._recent_actions: Deque[Tuple[str, str]] = deque(maxlen=window_size)

        # Cache last detected loop
        self._last_detected: Optional[LoopPattern] = None

        logger.debug(
            f"LoopDetector initialized: window={window_size}, rep_thresh={repetition_threshold}"
        )

    def record_action(self, action: str, context_hash: str = "") -> None:
        """Record an action for loop detection.

        Args:
            action: Action name
            context_hash: Optional hash of action context
        """
        self._recent_actions.append((action, context_hash))

    def is_stuck(
        self,
        action: str,
        context_hash: str = "",
    ) -> bool:
        """Check if agent appears stuck in a loop.

        Args:
            action: Current/planned action
            context_hash: Context hash for similarity

        Returns:
            True if stuck in a loop
        """
        # Add current action to history
        self.record_action(action, context_hash)

        # Check for patterns
        pattern = self._detect_pattern()
        self._last_detected = pattern

        if pattern.loop_type != LoopType.NONE:
            logger.warning(f"Loop detected: {pattern.description}")
            return True

        return False

    def _detect_pattern(self) -> LoopPattern:
        """Detect any loop pattern in recent actions.

        Returns:
            LoopPattern describing the detected pattern
        """
        if len(self._recent_actions) < 3:
            return LoopPattern(
                loop_type=LoopType.NONE,
                pattern=[],
                repetitions=0,
                confidence=0.0,
            )

        # Get just the action names
        actions = [a[0] for a in self._recent_actions]

        # Check for simple repetition first (most common)
        rep_pattern = self._detect_repetition(actions)
        if rep_pattern.loop_type != LoopType.NONE:
            return rep_pattern

        # Check for alternation
        alt_pattern = self._detect_alternation(actions)
        if alt_pattern.loop_type != LoopType.NONE:
            return alt_pattern

        # Check for cycles
        cycle_pattern = self._detect_cycle(actions)
        if cycle_pattern.loop_type != LoopType.NONE:
            return cycle_pattern

        return LoopPattern(
            loop_type=LoopType.NONE,
            pattern=[],
            repetitions=0,
            confidence=0.0,
        )

    def _detect_repetition(self, actions: List[str]) -> LoopPattern:
        """Detect simple repetition pattern.

        Args:
            actions: List of action names

        Returns:
            LoopPattern if repetition detected
        """
        if not actions:
            return LoopPattern(LoopType.NONE, [], 0, 0.0)

        # Count consecutive repetitions from the end
        last_action = actions[-1]
        count = 0

        for action in reversed(actions):
            if action == last_action:
                count += 1
            else:
                break

        if count >= self._repetition_threshold:
            confidence = min(1.0, count / (self._repetition_threshold * 2))
            return LoopPattern(
                loop_type=LoopType.REPETITION,
                pattern=[last_action],
                repetitions=count,
                confidence=confidence,
            )

        return LoopPattern(LoopType.NONE, [], 0, 0.0)

    def _detect_alternation(self, actions: List[str]) -> LoopPattern:
        """Detect alternation pattern (A-B-A-B).

        Args:
            actions: List of action names

        Returns:
            LoopPattern if alternation detected
        """
        if len(actions) < 4:
            return LoopPattern(LoopType.NONE, [], 0, 0.0)

        # Check last 4+ actions for alternation
        recent = list(actions)[-min(len(actions), 10) :]

        # Look for A-B-A-B pattern
        if len(recent) >= 4:
            action_a = recent[-1]
            action_b = recent[-2]

            if action_a == action_b:
                return LoopPattern(LoopType.NONE, [], 0, 0.0)

            # Count alternations
            alternations = 0
            expected = action_a

            for action in reversed(recent):
                if action == expected:
                    alternations += 1
                    expected = action_b if expected == action_a else action_a
                else:
                    break

            if alternations >= self._alternation_threshold:
                confidence = min(1.0, alternations / (self._alternation_threshold * 2))
                return LoopPattern(
                    loop_type=LoopType.ALTERNATION,
                    pattern=[action_a, action_b],
                    repetitions=alternations // 2,
                    confidence=confidence,
                )

        return LoopPattern(LoopType.NONE, [], 0, 0.0)

    def _detect_cycle(self, actions: List[str]) -> LoopPattern:
        """Detect cyclic pattern (A-B-C-A-B-C).

        Args:
            actions: List of action names

        Returns:
            LoopPattern if cycle detected
        """
        if len(actions) < 6:
            return LoopPattern(LoopType.NONE, [], 0, 0.0)

        # Try different cycle lengths (3 to 5)
        for cycle_len in range(3, 6):
            pattern = self._find_cycle(actions, cycle_len)
            if pattern.loop_type != LoopType.NONE:
                return pattern

        return LoopPattern(LoopType.NONE, [], 0, 0.0)

    def _find_cycle(self, actions: List[str], cycle_len: int) -> LoopPattern:
        """Find a cycle of specific length.

        Args:
            actions: List of action names
            cycle_len: Length of cycle to look for

        Returns:
            LoopPattern if cycle found
        """
        if len(actions) < cycle_len * self._cycle_threshold:
            return LoopPattern(LoopType.NONE, [], 0, 0.0)

        # Get the potential cycle pattern from the end
        potential_cycle = list(actions)[-cycle_len:]

        # Check if this pattern repeats
        repetitions = 0
        idx = len(actions) - cycle_len

        while idx >= 0:
            # Check if cycle matches at this position
            window = actions[max(0, idx - cycle_len + 1) : idx + 1]
            if len(window) == cycle_len:
                if all(window[i] == potential_cycle[i] for i in range(cycle_len)):
                    repetitions += 1
                    idx -= cycle_len
                else:
                    break
            else:
                break

        if repetitions >= self._cycle_threshold:
            confidence = min(1.0, repetitions / (self._cycle_threshold * 2))
            return LoopPattern(
                loop_type=LoopType.CYCLE,
                pattern=potential_cycle,
                repetitions=repetitions,
                confidence=confidence,
            )

        return LoopPattern(LoopType.NONE, [], 0, 0.0)

    def get_last_pattern(self) -> Optional[LoopPattern]:
        """Get the last detected loop pattern.

        Returns:
            Last LoopPattern or None
        """
        return self._last_detected

    def get_loop_description(self) -> str:
        """Get description of current loop state.

        Returns:
            Human-readable description
        """
        if self._last_detected and self._last_detected.loop_type != LoopType.NONE:
            return self._last_detected.description
        return "No loop detected"

    def suggest_break_action(
        self,
        available_actions: List[str],
    ) -> Optional[str]:
        """Suggest an action to break out of detected loop.

        Args:
            available_actions: List of available action names

        Returns:
            Suggested action to break loop or None
        """
        if not self._last_detected or self._last_detected.loop_type == LoopType.NONE:
            return None

        # Get actions in the loop pattern
        loop_actions = set(self._last_detected.pattern)

        # Find actions not in the loop
        alternatives = [a for a in available_actions if a not in loop_actions]

        if alternatives:
            return alternatives[0]

        return None

    def clear(self) -> None:
        """Clear action history."""
        self._recent_actions.clear()
        self._last_detected = None
        logger.debug("LoopDetector cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics.

        Returns:
            Statistics dictionary
        """
        actions = [a[0] for a in self._recent_actions]
        unique_actions = set(actions)

        return {
            "window_size": self._window_size,
            "actions_tracked": len(self._recent_actions),
            "unique_actions": len(unique_actions),
            "last_pattern": (self._last_detected.to_dict() if self._last_detected else None),
            "is_stuck": (
                self._last_detected.loop_type != LoopType.NONE if self._last_detected else False
            ),
        }
