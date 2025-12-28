"""Adaptive Learning Module - Learn from every action.

This module provides a unified interface for the continuous learning system.
It coordinates action tracking, self-critique, strategy adaptation, and
lesson storage to enable the agent to improve over time.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.defs import AgentAction
from src.learning.adapter import ActionBias, AdaptationContext, StrategyAdapter
from src.learning.critic import Critique, FailedAction, ImprovementSuggestion, SelfCritic
from src.learning.lessons import Lesson, LessonRepository
from src.learning.tracker import ActionStats, ActionTracker


@dataclass
class LearningOutcome:
    """Result of learning from an action outcome."""

    action: str
    reward: float
    success: bool

    # What was learned
    critique: Optional[Critique] = None
    lesson_created: Optional[Lesson] = None
    lesson_reinforced: Optional[str] = None  # Lesson ID if reinforced

    # Updated understanding
    new_success_rate: float = 0.5
    bias_change: float = 0.0

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "reward": self.reward,
            "success": self.success,
            "critique": self.critique.to_dict() if self.critique else None,
            "lesson_created": self.lesson_created.to_dict() if self.lesson_created else None,
            "lesson_reinforced": self.lesson_reinforced,
            "new_success_rate": self.new_success_rate,
            "bias_change": self.bias_change,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class LearningConfig:
    """Configuration for the learning module."""

    # When to trigger self-critique
    critique_on_failure: bool = True
    critique_threshold: float = 0.3  # Critique when reward below this

    # Lesson creation
    auto_create_lessons: bool = True
    min_confidence_for_lesson: float = 0.5

    # Bias adaptation
    enable_bias_adaptation: bool = True
    max_bias_change: float = 0.1  # Maximum bias change per outcome

    # Improvement suggestions
    analyze_patterns_threshold: int = 5  # Failures before pattern analysis

    # Persistence
    persist_lessons: bool = True


class AdaptiveLearningModule:
    """Learn from every action without retraining the base LLM.

    Uses RLAIF (AI feedback) when human feedback unavailable.

    Features:
    - Action success rate tracking
    - Self-critique on failures (RLAIF)
    - Lesson creation and storage
    - Strategy adaptation
    - Improvement suggestions
    """

    def __init__(
        self,
        config: Optional[LearningConfig] = None,
        llm_provider: Optional[Any] = None,
    ):
        """Initialize learning module.

        Args:
            config: Learning configuration
            llm_provider: Optional LLM for RLAIF critiques
        """
        self.config = config or LearningConfig()

        # Core components
        self._tracker = ActionTracker()
        self._critic = SelfCritic(llm_provider=llm_provider)
        self._lessons = LessonRepository() if self.config.persist_lessons else None
        self._adapter = StrategyAdapter(
            tracker=self._tracker,
            lesson_repository=self._lessons,
        )

        # Recent failures for pattern analysis
        self._recent_failures: List[FailedAction] = []
        self._max_recent_failures = 50

        # Learning history
        self._learning_outcomes: List[LearningOutcome] = []

        logger.info("AdaptiveLearningModule initialized")

    async def learn_from_outcome(
        self,
        action: str,
        context: Dict[str, Any],
        outcome: Any,
        reward: float,
        error_message: Optional[str] = None,
    ) -> LearningOutcome:
        """Learn from an action outcome.

        This is the main entry point for the learning system.

        Args:
            action: Name of the action performed
            context: Context in which action was taken
            outcome: Result of the action
            reward: Reward received (-1 to 1)
            error_message: Optional error message if failed

        Returns:
            LearningOutcome with what was learned
        """
        success = reward > 0
        context_key = self._adapter.extract_context_features(context)

        # 1. Record in tracker
        self._tracker.record(
            action=action,
            context_key=context_key,
            reward=reward,
            success=success,
            metadata={"context": context, "outcome": str(outcome)[:500]},
        )

        # Initialize learning result
        learning = LearningOutcome(
            action=action,
            reward=reward,
            success=success,
            new_success_rate=self._tracker.get_success_rate(action),
        )

        # 2. Self-critique if failed
        if not success and self.config.critique_on_failure:
            if reward < self.config.critique_threshold:
                critique = await self._critic.critique(
                    action=action,
                    context=context,
                    outcome=outcome,
                    error_message=error_message,
                )
                learning.critique = critique

                # Track failure for pattern analysis
                self._recent_failures.append(
                    FailedAction(
                        action=action,
                        context=context,
                        outcome=outcome,
                        error_message=error_message,
                    )
                )
                if len(self._recent_failures) > self._max_recent_failures:
                    self._recent_failures.pop(0)

                # 3. Create lesson from critique
                if self.config.auto_create_lessons and self._lessons:
                    if critique.confidence >= self.config.min_confidence_for_lesson:
                        lesson = await self._create_lesson_from_critique(critique, context_key)
                        learning.lesson_created = lesson

                        # Apply lesson to adapter
                        self._adapter.update_from_lesson(lesson)

        # 4. Check for existing lessons to reinforce
        if success and self._lessons:
            reinforced = await self._check_lesson_reinforcement(action, context)
            if reinforced:
                learning.lesson_reinforced = reinforced

        # 5. Record learning outcome
        self._learning_outcomes.append(learning)
        if len(self._learning_outcomes) > 1000:
            self._learning_outcomes.pop(0)

        logger.debug(
            f"Learned from {action}: reward={reward:.2f}, "
            f"success_rate={learning.new_success_rate:.2f}"
        )

        return learning

    async def learn_from_agent_action(
        self,
        action: AgentAction,
        context: Dict[str, Any],
        outcome: Any,
        reward: float,
        error_message: Optional[str] = None,
    ) -> LearningOutcome:
        """Learn from an AgentAction enum outcome.

        Args:
            action: AgentAction enum value
            context: Context dictionary
            outcome: Action result
            reward: Reward value
            error_message: Optional error

        Returns:
            LearningOutcome
        """
        return await self.learn_from_outcome(
            action=action.value,
            context=context,
            outcome=outcome,
            reward=reward,
            error_message=error_message,
        )

    async def _create_lesson_from_critique(
        self,
        critique: Critique,
        context_key: str,
    ) -> Lesson:
        """Create a lesson from a critique.

        Args:
            critique: Self-critique result
            context_key: Context fingerprint

        Returns:
            Created Lesson
        """
        lesson = Lesson.create(
            summary=critique.lesson_learned,
            situation=critique.context_summary,
            action=critique.action,
            what_went_wrong=critique.what_went_wrong,
            better_approach=critique.better_approach,
            context_key=context_key,
            confidence=critique.confidence,
        )

        if self._lessons:
            await self._lessons.store(lesson)

        logger.debug(f"Created lesson: {lesson.summary}")
        return lesson

    async def _check_lesson_reinforcement(
        self,
        action: str,
        context: Dict[str, Any],
    ) -> Optional[str]:
        """Check if a successful action reinforces existing lessons.

        Args:
            action: Action that succeeded
            context: Current context

        Returns:
            Reinforced lesson ID or None
        """
        if not self._lessons:
            return None

        # Find lessons for this action
        lessons = await self._lessons.find_by_action(action, top_k=3)

        for lesson in lessons:
            # If we followed the better approach, reinforce
            if lesson.better_approach:
                # Simple check - could be more sophisticated
                context_str = str(context).lower()
                if any(word in context_str for word in lesson.better_approach.lower().split()[:3]):
                    await self._lessons.reinforce_lesson(lesson.id)
                    return lesson.id

        return None

    def get_action_biases(
        self,
        context: Dict[str, Any],
        available_actions: Optional[List[str]] = None,
    ) -> Dict[str, ActionBias]:
        """Get learned biases for planning module.

        Args:
            context: Current context
            available_actions: Optional filter

        Returns:
            Dictionary of action to ActionBias
        """
        adaptation_context = AdaptationContext(
            goal=context.get("goal"),
            task_type=context.get("task_type"),
            environment=context.get("environment"),
            previous_action=context.get("previous_action"),
            error_state=context.get("error"),
        )

        return self._adapter.get_action_biases(adaptation_context, available_actions)

    async def get_relevant_lessons(
        self,
        context: Dict[str, Any],
        top_k: int = 3,
    ) -> List[Lesson]:
        """Get lessons relevant to current situation.

        Args:
            context: Current context
            top_k: Maximum lessons

        Returns:
            List of relevant Lessons
        """
        if not self._lessons:
            return []

        return await self._lessons.find_relevant(context, top_k=top_k)

    async def analyze_recent_failures(self) -> List[ImprovementSuggestion]:
        """Analyze recent failures for patterns.

        Returns:
            List of improvement suggestions
        """
        if len(self._recent_failures) < self.config.analyze_patterns_threshold:
            return []

        return await self._critic.generate_improvement_suggestions(self._recent_failures)

    def get_action_stats(self, action: str) -> Optional[ActionStats]:
        """Get statistics for an action.

        Args:
            action: Action name

        Returns:
            ActionStats or None
        """
        return self._tracker.get_action_stats(action)

    def get_success_rate(self, action: str) -> float:
        """Get success rate for an action.

        Args:
            action: Action name

        Returns:
            Success rate (0 to 1)
        """
        return self._tracker.get_success_rate(action)

    def get_best_action_for_context(
        self,
        context: Dict[str, Any],
        available_actions: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Get the best action for current context.

        Args:
            context: Current context
            available_actions: Actions to choose from

        Returns:
            Best action name or None
        """
        adaptation_context = AdaptationContext(
            goal=context.get("goal"),
            task_type=context.get("task_type"),
            environment=context.get("environment"),
        )

        return self._adapter.get_preferred_action(adaptation_context, available_actions or [])

    def get_actions_to_avoid(
        self,
        context: Dict[str, Any],
    ) -> List[str]:
        """Get actions that should be avoided.

        Args:
            context: Current context

        Returns:
            List of action names to avoid
        """
        adaptation_context = AdaptationContext(
            goal=context.get("goal"),
            task_type=context.get("task_type"),
            environment=context.get("environment"),
        )

        return self._adapter.get_actions_to_avoid(adaptation_context)

    def get_learning_history(
        self,
        limit: int = 50,
        action: Optional[str] = None,
    ) -> List[LearningOutcome]:
        """Get recent learning outcomes.

        Args:
            limit: Maximum outcomes to return
            action: Optional filter by action

        Returns:
            List of LearningOutcome
        """
        outcomes = self._learning_outcomes

        if action:
            outcomes = [o for o in outcomes if o.action == action]

        return outcomes[-limit:]

    def get_failing_actions(
        self,
        threshold: float = 0.3,
    ) -> List[tuple[str, ActionStats]]:
        """Get actions that are frequently failing.

        Args:
            threshold: Success rate threshold

        Returns:
            List of (action, stats) tuples
        """
        return self._tracker.get_failing_actions(threshold=threshold)

    def get_improvement_suggestions(self) -> List[ImprovementSuggestion]:
        """Get cached improvement suggestions.

        Returns:
            List of suggestions
        """
        return self._critic.get_suggestions()

    def get_recent_critiques(self, limit: int = 10) -> List[Critique]:
        """Get recent self-critiques.

        Args:
            limit: Maximum critiques

        Returns:
            List of Critiques
        """
        return self._critic.get_recent_critiques(limit)

    async def get_lesson_statistics(self) -> Dict[str, Any]:
        """Get statistics about stored lessons.

        Returns:
            Statistics dictionary
        """
        if not self._lessons:
            return {"enabled": False}

        stats = self._lessons.get_statistics()
        stats["enabled"] = True
        return stats

    def get_tracker_statistics(self) -> Dict[str, Any]:
        """Get action tracking statistics.

        Returns:
            Statistics dictionary
        """
        all_stats = self._tracker.get_all_stats()

        if not all_stats:
            return {
                "total_actions_tracked": 0,
                "total_outcomes": 0,
            }

        total_outcomes = sum(s.total_count for s in all_stats.values())
        total_success = sum(s.success_count for s in all_stats.values())

        return {
            "total_actions_tracked": len(all_stats),
            "total_outcomes": total_outcomes,
            "overall_success_rate": total_success / total_outcomes if total_outcomes else 0,
            "best_performing": max(all_stats.items(), key=lambda x: x[1].success_rate)[0]
            if all_stats
            else None,
            "worst_performing": min(all_stats.items(), key=lambda x: x[1].success_rate)[0]
            if all_stats
            else None,
        }

    def reset(self) -> None:
        """Reset all learning state."""
        self._tracker.clear()
        self._critic.clear()
        self._adapter.reset_modifiers()
        self._recent_failures.clear()
        self._learning_outcomes.clear()

        if self._lessons:
            self._lessons.clear_cache()

        logger.info("AdaptiveLearningModule reset")

    def to_dict(self) -> Dict[str, Any]:
        """Export module state.

        Returns:
            Serialized state
        """
        return {
            "tracker": self._tracker.to_dict(),
            "adapter": self._adapter.to_dict(),
            "recent_outcomes": [o.to_dict() for o in self._learning_outcomes[-100:]],
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Import module state.

        Args:
            data: Serialized state
        """
        if "tracker" in data:
            self._tracker.from_dict(data["tracker"])

        if "adapter" in data:
            self._adapter.from_dict(data["adapter"])

        logger.debug("AdaptiveLearningModule state restored")


# Singleton instance
_learning_module: Optional[AdaptiveLearningModule] = None


def get_learning_module(
    config: Optional[LearningConfig] = None,
    llm_provider: Optional[Any] = None,
) -> AdaptiveLearningModule:
    """Get or create the learning module singleton.

    Args:
        config: Optional configuration
        llm_provider: Optional LLM provider

    Returns:
        AdaptiveLearningModule instance
    """
    global _learning_module
    if _learning_module is None:
        _learning_module = AdaptiveLearningModule(config=config, llm_provider=llm_provider)
    return _learning_module
