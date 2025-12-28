"""Strategy Adapter - Adjust planning biases based on learned patterns.

This module provides the interface between the learning system and
the planning module, translating learned experience into action biases.
"""

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.core.defs import AgentAction
from src.learning.lessons import Lesson, LessonRepository
from src.learning.tracker import ActionStats, ActionTracker


@dataclass
class ActionBias:
    """Bias modifier for an action."""

    action: str
    bias: float  # -1.0 to 1.0 (negative = avoid, positive = prefer)
    confidence: float  # How confident we are in this bias
    reason: str  # Why this bias exists
    source: str  # Where this bias came from (tracker, lesson, etc.)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "bias": self.bias,
            "confidence": self.confidence,
            "reason": self.reason,
            "source": self.source,
        }


@dataclass
class AdaptationContext:
    """Context for strategy adaptation."""

    goal: Optional[str] = None
    task_type: Optional[str] = None
    environment: Optional[str] = None
    previous_action: Optional[str] = None
    error_state: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_context_key(self) -> str:
        """Generate a context key for lookups.

        Returns:
            Hashable context key
        """
        parts = []
        if self.goal:
            parts.append(f"goal:{self.goal[:50]}")
        if self.task_type:
            parts.append(f"type:{self.task_type}")
        if self.environment:
            parts.append(f"env:{self.environment}")
        if self.error_state:
            parts.append(f"err:{self.error_state}")

        if not parts:
            return "global"

        # Create a consistent hash
        key = "|".join(sorted(parts))
        return hashlib.md5(key.encode()).hexdigest()[:12]


class StrategyAdapter:
    """Adjust planning biases based on learned patterns.

    This adapter:
    - Translates action success rates into biases
    - Applies context-specific modifiers
    - Incorporates lessons learned
    - Provides ranked action preferences

    Features:
    - Context-aware bias calculation
    - Lesson application
    - Temporal decay for old data
    - Multi-source bias aggregation
    """

    # Weight factors for different bias sources
    TRACKER_WEIGHT = 0.4
    LESSON_WEIGHT = 0.4
    RECENT_WEIGHT = 0.2

    # Bias calculation constants
    NEUTRAL_RATE = 0.5  # Success rate that maps to zero bias
    MAX_BIAS = 0.5  # Maximum absolute bias value

    def __init__(
        self,
        tracker: ActionTracker,
        lesson_repository: Optional[LessonRepository] = None,
    ):
        """Initialize strategy adapter.

        Args:
            tracker: ActionTracker for success rate data
            lesson_repository: Optional repository for learned lessons
        """
        self._tracker = tracker
        self._lessons = lesson_repository

        # Custom overrides (manually set biases)
        self._overrides: Dict[str, ActionBias] = {}

        # Context-specific modifiers
        self._context_modifiers: Dict[Tuple[str, str], float] = {}  # (context_key, action) -> mod

        logger.debug("StrategyAdapter initialized")

    def get_action_biases(
        self,
        context: AdaptationContext,
        available_actions: Optional[List[str]] = None,
    ) -> Dict[str, ActionBias]:
        """Get learned preferences for planning module.

        Successful actions get boosted, failures get penalized.

        Args:
            context: Current context for adaptation
            available_actions: Optional filter for specific actions

        Returns:
            Dictionary of action name to ActionBias
        """
        biases: Dict[str, ActionBias] = {}
        context_key = context.to_context_key()

        # Get actions to evaluate
        if available_actions:
            actions_to_check = available_actions
        else:
            # Use all known actions from tracker plus AgentAction enum
            actions_to_check = list(self._tracker.get_all_stats().keys())
            for agent_action in AgentAction:
                if agent_action.value not in actions_to_check:
                    actions_to_check.append(agent_action.value)

        for action_name in actions_to_check:
            bias = self._calculate_bias(action_name, context_key)
            if bias:
                biases[action_name] = bias

        return biases

    def _calculate_bias(
        self,
        action: str,
        context_key: str,
    ) -> Optional[ActionBias]:
        """Calculate bias for a single action.

        Args:
            action: Action name
            context_key: Context identifier

        Returns:
            ActionBias or None if no data
        """
        # Check for manual override first
        if action in self._overrides:
            return self._overrides[action]

        # Collect bias components
        components: List[Tuple[float, float, str]] = []  # (bias, weight, source)

        # 1. Global success rate from tracker
        stats = self._tracker.get_action_stats(action)
        if stats and stats.total_count > 0:
            global_bias = self._success_rate_to_bias(stats.success_rate)
            components.append((global_bias, self.TRACKER_WEIGHT, "tracker"))

        # 2. Context-specific rate
        context_rate = self._tracker.get_context_success_rate(context_key, action)
        if context_rate != 0.5:  # Has context data
            context_bias = self._success_rate_to_bias(context_rate)
            components.append((context_bias, self.TRACKER_WEIGHT, "context"))

        # 3. Recent performance
        if stats and stats.recent_rewards:
            recent_bias = self._success_rate_to_bias(stats.recent_success_rate)
            components.append((recent_bias, self.RECENT_WEIGHT, "recent"))

        # 4. Context modifier (from lessons or explicit)
        modifier = self._context_modifiers.get((context_key, action), 0.0)
        if modifier != 0:
            components.append((modifier, self.LESSON_WEIGHT, "modifier"))

        if not components:
            return None

        # Aggregate biases
        total_weight = sum(w for _, w, _ in components)
        weighted_bias = sum(b * w for b, w, _ in components) / total_weight

        # Clamp to max bias
        weighted_bias = max(-self.MAX_BIAS, min(self.MAX_BIAS, weighted_bias))

        # Determine confidence and reason
        confidence = min(1.0, total_weight)
        sources = [s for _, _, s in components]
        reason = self._generate_reason(action, stats, weighted_bias, sources)

        return ActionBias(
            action=action,
            bias=weighted_bias,
            confidence=confidence,
            reason=reason,
            source=",".join(sources),
        )

    def _success_rate_to_bias(self, rate: float) -> float:
        """Convert success rate to bias value.

        Args:
            rate: Success rate (0 to 1)

        Returns:
            Bias value (-MAX_BIAS to +MAX_BIAS)
        """
        # Center around neutral rate and scale
        deviation = rate - self.NEUTRAL_RATE
        return deviation * 2 * self.MAX_BIAS  # Scale to [-MAX_BIAS, MAX_BIAS]

    def _generate_reason(
        self,
        action: str,
        stats: Optional[ActionStats],
        bias: float,
        sources: List[str],
    ) -> str:
        """Generate human-readable reason for bias.

        Args:
            action: Action name
            stats: Action statistics
            bias: Calculated bias
            sources: Sources used

        Returns:
            Reason string
        """
        if not stats:
            return f"No historical data for {action}"

        rate = stats.success_rate
        count = stats.total_count

        if bias > 0.1:
            return f"{action} has {rate:.0%} success rate ({count} uses)"
        elif bias < -0.1:
            return f"{action} has low success ({rate:.0%} over {count} uses)"
        else:
            return f"{action} has neutral performance ({rate:.0%})"

    def update_from_lesson(self, lesson: Lesson) -> None:
        """Apply learned lesson to strategy.

        Args:
            lesson: Lesson to apply
        """
        # Update context modifiers based on lesson
        context_key = lesson.context_key or "global"

        # Penalize the action that failed
        current = self._context_modifiers.get((context_key, lesson.action), 0.0)
        # Each lesson reinforcement increases penalty
        penalty = -0.1 * (1 + lesson.reinforcement_count * 0.1)
        self._context_modifiers[(context_key, lesson.action)] = current + penalty

        # If lesson suggests better approach, boost that action
        if lesson.better_approach:
            # Try to extract action from better approach
            for agent_action in AgentAction:
                if agent_action.value in lesson.better_approach.lower():
                    alt_key = (context_key, agent_action.value)
                    alt_current = self._context_modifiers.get(alt_key, 0.0)
                    self._context_modifiers[alt_key] = alt_current + 0.1

        logger.debug(f"Applied lesson to strategy: {lesson.summary}")

    def set_override(
        self,
        action: str,
        bias: float,
        reason: str,
    ) -> None:
        """Set a manual override for an action.

        Args:
            action: Action name
            bias: Bias value (-1 to 1)
            reason: Reason for override
        """
        self._overrides[action] = ActionBias(
            action=action,
            bias=max(-1.0, min(1.0, bias)),
            confidence=1.0,
            reason=reason,
            source="override",
        )
        logger.debug(f"Set override for {action}: bias={bias}, reason={reason}")

    def remove_override(self, action: str) -> bool:
        """Remove a manual override.

        Args:
            action: Action name

        Returns:
            True if override was removed
        """
        if action in self._overrides:
            del self._overrides[action]
            return True
        return False

    def get_ranked_actions(
        self,
        context: AdaptationContext,
        available_actions: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """Get actions ranked by bias.

        Args:
            context: Current context
            available_actions: Optional filter

        Returns:
            List of (action, bias) tuples sorted by bias descending
        """
        biases = self.get_action_biases(context, available_actions)

        ranked = [(action, b.bias) for action, b in biases.items()]
        ranked.sort(key=lambda x: x[1], reverse=True)

        return ranked

    def get_preferred_action(
        self,
        context: AdaptationContext,
        available_actions: List[str],
    ) -> Optional[str]:
        """Get the most preferred action for context.

        Args:
            context: Current context
            available_actions: Actions to choose from

        Returns:
            Best action or None
        """
        ranked = self.get_ranked_actions(context, available_actions)
        if ranked:
            return ranked[0][0]
        return None

    def get_actions_to_avoid(
        self,
        context: AdaptationContext,
        threshold: float = -0.2,
    ) -> List[str]:
        """Get actions with negative bias.

        Args:
            context: Current context
            threshold: Bias threshold (below = avoid)

        Returns:
            List of action names to avoid
        """
        biases = self.get_action_biases(context)
        return [
            action for action, bias in biases.items() if bias.bias < threshold
        ]

    def extract_context_features(self, context: Dict[str, Any]) -> str:
        """Extract a context key from raw context dict.

        Args:
            context: Raw context dictionary

        Returns:
            Context key string
        """
        adaptation_context = AdaptationContext(
            goal=context.get("goal"),
            task_type=context.get("task_type") or context.get("type"),
            environment=context.get("environment") or context.get("env"),
            previous_action=context.get("previous_action"),
            error_state=context.get("error") or context.get("error_state"),
        )
        return adaptation_context.to_context_key()

    def get_context_modifier(self, context_key: str, action: str) -> float:
        """Get context-specific modifier for action.

        Args:
            context_key: Context identifier
            action: Action name

        Returns:
            Modifier value
        """
        return self._context_modifiers.get((context_key, action), 0.0)

    def reset_modifiers(self) -> None:
        """Reset all learned context modifiers."""
        self._context_modifiers.clear()
        logger.debug("Context modifiers reset")

    def to_dict(self) -> Dict[str, Any]:
        """Export adapter state.

        Returns:
            Serialized state
        """
        return {
            "overrides": {k: v.to_dict() for k, v in self._overrides.items()},
            "context_modifiers": {
                f"{k[0]}:{k[1]}": v for k, v in self._context_modifiers.items()
            },
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Import adapter state.

        Args:
            data: Serialized state
        """
        self._overrides.clear()
        self._context_modifiers.clear()

        for action, bias_data in data.get("overrides", {}).items():
            self._overrides[action] = ActionBias(
                action=action,
                bias=bias_data["bias"],
                confidence=bias_data.get("confidence", 1.0),
                reason=bias_data.get("reason", ""),
                source=bias_data.get("source", "override"),
            )

        for key_str, value in data.get("context_modifiers", {}).items():
            parts = key_str.split(":", 1)
            if len(parts) == 2:
                self._context_modifiers[(parts[0], parts[1])] = value

        logger.debug("StrategyAdapter state restored")
