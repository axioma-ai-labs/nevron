"""Action Tracker - Track success rates per action and context.

This module tracks the performance of actions across different contexts
to enable adaptive decision-making.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from loguru import logger

from src.core.defs import AgentAction


@dataclass
class ActionOutcome:
    """Represents a single action outcome for tracking."""

    id: str
    action: str
    context_key: str
    reward: float
    success: bool
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "action": self.action,
            "context_key": self.context_key,
            "reward": self.reward,
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionOutcome":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            action=data["action"],
            context_key=data.get("context_key", "global"),
            reward=data.get("reward", 0.0),
            success=data.get("success", False),
            timestamp=datetime.fromisoformat(data["timestamp"])
            if isinstance(data.get("timestamp"), str)
            else data.get("timestamp", datetime.now(timezone.utc)),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ActionStats:
    """Statistics for a single action."""

    action: str
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_reward: float = 0.0
    recent_rewards: List[float] = field(default_factory=list)
    last_used: Optional[datetime] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_count == 0:
            return 0.5  # Neutral for unknown
        return self.success_count / self.total_count

    @property
    def average_reward(self) -> float:
        """Calculate average reward."""
        if self.total_count == 0:
            return 0.0
        return self.total_reward / self.total_count

    @property
    def recent_success_rate(self) -> float:
        """Calculate success rate from recent outcomes."""
        if not self.recent_rewards:
            return 0.5
        successes = sum(1 for r in self.recent_rewards if r > 0)
        return successes / len(self.recent_rewards)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "total_reward": self.total_reward,
            "success_rate": self.success_rate,
            "average_reward": self.average_reward,
            "recent_success_rate": self.recent_success_rate,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }


class ActionTracker:
    """Track success rates per action and context.

    Features:
    - Per-action success rate tracking
    - Context-aware action performance
    - Temporal decay for older outcomes
    - Best action recommendations per context
    """

    # Maximum recent outcomes to track per action
    MAX_RECENT_OUTCOMES = 100
    # Window size for recent success rate
    RECENT_WINDOW_SIZE = 20

    def __init__(self):
        """Initialize action tracker."""
        # Action-level tracking: action_name -> ActionStats
        self._action_stats: Dict[str, ActionStats] = {}

        # Context-action tracking: (context_key, action) -> List[reward]
        self._context_action_rewards: DefaultDict[Tuple[str, str], List[float]] = defaultdict(list)

        # Raw outcome history for analysis
        self._outcomes: List[ActionOutcome] = []

        logger.debug("ActionTracker initialized")

    def record(
        self,
        action: str,
        context_key: str,
        reward: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActionOutcome:
        """Record an action outcome.

        Args:
            action: Name of the action taken
            context_key: Key identifying the context
            reward: Reward received (-1 to 1)
            success: Whether the action succeeded
            metadata: Additional metadata

        Returns:
            The recorded ActionOutcome
        """
        # Create outcome
        outcome = ActionOutcome(
            id=str(uuid.uuid4()),
            action=action,
            context_key=context_key,
            reward=reward,
            success=success,
            metadata=metadata or {},
        )

        # Update action stats
        if action not in self._action_stats:
            self._action_stats[action] = ActionStats(action=action)

        stats = self._action_stats[action]
        stats.total_count += 1
        stats.total_reward += reward
        stats.last_used = outcome.timestamp

        if success:
            stats.success_count += 1
        else:
            stats.failure_count += 1

        # Maintain recent rewards window
        stats.recent_rewards.append(reward)
        if len(stats.recent_rewards) > self.RECENT_WINDOW_SIZE:
            stats.recent_rewards.pop(0)

        # Update context-action rewards
        key = (context_key, action)
        self._context_action_rewards[key].append(reward)
        if len(self._context_action_rewards[key]) > self.MAX_RECENT_OUTCOMES:
            self._context_action_rewards[key].pop(0)

        # Store outcome
        self._outcomes.append(outcome)
        if len(self._outcomes) > self.MAX_RECENT_OUTCOMES * 10:
            self._outcomes.pop(0)

        logger.debug(
            f"Recorded outcome: action={action}, context={context_key}, "
            f"reward={reward:.2f}, success={success}"
        )

        return outcome

    def record_action(
        self,
        action: AgentAction,
        context_key: str,
        reward: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ActionOutcome:
        """Record outcome for an AgentAction enum.

        Args:
            action: AgentAction enum value
            context_key: Key identifying the context
            reward: Reward received
            success: Whether succeeded
            metadata: Additional metadata

        Returns:
            The recorded ActionOutcome
        """
        return self.record(
            action=action.value,
            context_key=context_key,
            reward=reward,
            success=success,
            metadata=metadata,
        )

    def get_success_rate(self, action: str) -> float:
        """Get success rate for an action.

        Args:
            action: Action name

        Returns:
            Success rate (0 to 1), 0.5 if unknown
        """
        stats = self._action_stats.get(action)
        if stats:
            return stats.success_rate
        return 0.5  # Neutral for unknown actions

    def get_action_stats(self, action: str) -> Optional[ActionStats]:
        """Get full stats for an action.

        Args:
            action: Action name

        Returns:
            ActionStats or None if not tracked
        """
        return self._action_stats.get(action)

    def get_context_success_rate(self, context_key: str, action: str) -> float:
        """Get success rate for action in specific context.

        Args:
            context_key: Context identifier
            action: Action name

        Returns:
            Success rate for this context-action pair
        """
        key = (context_key, action)
        rewards = self._context_action_rewards.get(key, [])
        if not rewards:
            return 0.5  # Neutral if no data
        successes = sum(1 for r in rewards if r > 0)
        return successes / len(rewards)

    def get_best_action_for_context(
        self,
        context_key: str,
        available_actions: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Get the best performing action for a context.

        Args:
            context_key: Context identifier
            available_actions: Optional list to filter from

        Returns:
            Best action name or None
        """
        best_action = None
        best_rate = -1.0

        # Get all actions seen in this context
        for key, rewards in self._context_action_rewards.items():
            ctx, action = key
            if ctx != context_key:
                continue

            # Filter to available actions if specified
            if available_actions and action not in available_actions:
                continue

            # Calculate success rate
            if not rewards:
                continue

            rate = sum(1 for r in rewards if r > 0) / len(rewards)
            if rate > best_rate:
                best_rate = rate
                best_action = action

        return best_action

    def get_action_ranking(
        self,
        context_key: Optional[str] = None,
        available_actions: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """Get actions ranked by success rate.

        Args:
            context_key: Optional context filter
            available_actions: Optional action filter

        Returns:
            List of (action, success_rate) tuples sorted by rate
        """
        rankings: List[Tuple[str, float]] = []

        if context_key:
            # Context-specific ranking
            for key, rewards in self._context_action_rewards.items():
                ctx, action = key
                if ctx != context_key:
                    continue
                if available_actions and action not in available_actions:
                    continue
                if not rewards:
                    continue
                rate = sum(1 for r in rewards if r > 0) / len(rewards)
                rankings.append((action, rate))
        else:
            # Global ranking
            for action, stats in self._action_stats.items():
                if available_actions and action not in available_actions:
                    continue
                rankings.append((action, stats.success_rate))

        # Sort by rate descending
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings

    def get_all_stats(self) -> Dict[str, ActionStats]:
        """Get stats for all tracked actions.

        Returns:
            Dictionary of action name to ActionStats
        """
        return dict(self._action_stats)

    def get_recent_outcomes(
        self,
        action: Optional[str] = None,
        context_key: Optional[str] = None,
        limit: int = 50,
    ) -> List[ActionOutcome]:
        """Get recent outcomes with optional filtering.

        Args:
            action: Filter by action name
            context_key: Filter by context
            limit: Maximum outcomes to return

        Returns:
            List of ActionOutcome
        """
        outcomes = self._outcomes

        if action:
            outcomes = [o for o in outcomes if o.action == action]
        if context_key:
            outcomes = [o for o in outcomes if o.context_key == context_key]

        return outcomes[-limit:]

    def get_failing_actions(
        self,
        threshold: float = 0.3,
        min_observations: int = 5,
    ) -> List[Tuple[str, ActionStats]]:
        """Get actions that are frequently failing.

        Args:
            threshold: Success rate threshold (below = failing)
            min_observations: Minimum observations required

        Returns:
            List of (action_name, stats) for failing actions
        """
        failing = []
        for action, stats in self._action_stats.items():
            if stats.total_count >= min_observations:
                if stats.success_rate < threshold:
                    failing.append((action, stats))

        # Sort by success rate ascending (worst first)
        failing.sort(key=lambda x: x[1].success_rate)
        return failing

    def clear(self) -> None:
        """Clear all tracked data."""
        self._action_stats.clear()
        self._context_action_rewards.clear()
        self._outcomes.clear()
        logger.debug("ActionTracker cleared")

    def to_dict(self) -> Dict[str, Any]:
        """Export tracker state to dictionary.

        Returns:
            Serialized tracker state
        """
        return {
            "action_stats": {k: v.to_dict() for k, v in self._action_stats.items()},
            "context_action_rewards": {
                f"{k[0]}:{k[1]}": v for k, v in self._context_action_rewards.items()
            },
            "outcomes": [o.to_dict() for o in self._outcomes[-100:]],  # Last 100
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Import tracker state from dictionary.

        Args:
            data: Serialized tracker state
        """
        self.clear()

        # Restore action stats
        for action, stats_data in data.get("action_stats", {}).items():
            stats = ActionStats(
                action=action,
                total_count=stats_data.get("total_count", 0),
                success_count=stats_data.get("success_count", 0),
                failure_count=stats_data.get("failure_count", 0),
                total_reward=stats_data.get("total_reward", 0.0),
            )
            if stats_data.get("last_used"):
                stats.last_used = datetime.fromisoformat(stats_data["last_used"])
            self._action_stats[action] = stats

        # Restore context-action rewards
        for key_str, rewards in data.get("context_action_rewards", {}).items():
            parts = key_str.split(":", 1)
            if len(parts) == 2:
                key = (parts[0], parts[1])
                self._context_action_rewards[key] = rewards

        # Restore outcomes
        for outcome_data in data.get("outcomes", []):
            outcome = ActionOutcome.from_dict(outcome_data)
            self._outcomes.append(outcome)

        logger.debug("ActionTracker state restored")
