"""Intervention System - Define intervention types and data structures.

Interventions are actions taken by the metacognitive monitor to
correct or improve agent behavior.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class InterventionType(Enum):
    """Types of interventions the metacognitive monitor can trigger."""

    CONTINUE = "continue"  # No intervention needed
    BREAK_LOOP = "break_loop"  # Force different approach
    PREEMPTIVE_REPLAN = "replan"  # Replan before failure
    HUMAN_HANDOFF = "human_handoff"  # Ask for human help
    PAUSE = "pause"  # Wait before continuing
    ABORT = "abort"  # Stop current goal entirely
    THROTTLE = "throttle"  # Slow down action rate
    FALLBACK = "fallback"  # Use fallback action


@dataclass
class Intervention:
    """Represents an intervention triggered by the metacognitive monitor."""

    type: InterventionType
    reason: str
    suggested_action: Optional[str] = None
    wait_seconds: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    priority: int = 1  # 1 = low, 5 = critical
    alternatives: List[str] = field(default_factory=list)

    @property
    def requires_action(self) -> bool:
        """Check if this intervention requires action."""
        return self.type != InterventionType.CONTINUE

    @property
    def blocks_execution(self) -> bool:
        """Check if this intervention blocks normal execution."""
        return self.type in {
            InterventionType.ABORT,
            InterventionType.HUMAN_HANDOFF,
            InterventionType.PAUSE,
        }

    @property
    def is_critical(self) -> bool:
        """Check if this is a critical intervention."""
        return self.priority >= 4 or self.type == InterventionType.ABORT

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type.value,
            "reason": self.reason,
            "suggested_action": self.suggested_action,
            "wait_seconds": self.wait_seconds,
            "context": self.context,
            "created_at": self.created_at.isoformat(),
            "priority": self.priority,
            "alternatives": self.alternatives,
            "requires_action": self.requires_action,
            "blocks_execution": self.blocks_execution,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Intervention":
        """Create from dictionary."""
        return cls(
            type=InterventionType(data["type"]),
            reason=data["reason"],
            suggested_action=data.get("suggested_action"),
            wait_seconds=data.get("wait_seconds", 0.0),
            context=data.get("context", {}),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.now(timezone.utc)),
            priority=data.get("priority", 1),
            alternatives=data.get("alternatives", []),
        )

    @classmethod
    def continue_execution(cls) -> "Intervention":
        """Factory for continue intervention."""
        return cls(
            type=InterventionType.CONTINUE,
            reason="No intervention needed",
        )

    @classmethod
    def break_loop(
        cls,
        reason: str,
        suggested_action: Optional[str] = None,
        alternatives: Optional[List[str]] = None,
    ) -> "Intervention":
        """Factory for break loop intervention."""
        return cls(
            type=InterventionType.BREAK_LOOP,
            reason=reason,
            suggested_action=suggested_action,
            priority=3,
            alternatives=alternatives or [],
        )

    @classmethod
    def preemptive_replan(
        cls,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> "Intervention":
        """Factory for preemptive replan intervention."""
        return cls(
            type=InterventionType.PREEMPTIVE_REPLAN,
            reason=reason,
            priority=2,
            context=context or {},
        )

    @classmethod
    def human_handoff(
        cls,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> "Intervention":
        """Factory for human handoff intervention."""
        return cls(
            type=InterventionType.HUMAN_HANDOFF,
            reason=reason,
            priority=4,
            context=context or {},
        )

    @classmethod
    def pause(
        cls,
        reason: str,
        wait_seconds: float,
    ) -> "Intervention":
        """Factory for pause intervention."""
        return cls(
            type=InterventionType.PAUSE,
            reason=reason,
            wait_seconds=wait_seconds,
            priority=2,
        )

    @classmethod
    def abort(
        cls,
        reason: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> "Intervention":
        """Factory for abort intervention."""
        return cls(
            type=InterventionType.ABORT,
            reason=reason,
            priority=5,
            context=context or {},
        )

    @classmethod
    def throttle(
        cls,
        reason: str,
        wait_seconds: float,
    ) -> "Intervention":
        """Factory for throttle intervention."""
        return cls(
            type=InterventionType.THROTTLE,
            reason=reason,
            wait_seconds=wait_seconds,
            priority=2,
        )

    @classmethod
    def fallback(
        cls,
        reason: str,
        suggested_action: str,
        alternatives: Optional[List[str]] = None,
    ) -> "Intervention":
        """Factory for fallback intervention."""
        return cls(
            type=InterventionType.FALLBACK,
            reason=reason,
            suggested_action=suggested_action,
            priority=2,
            alternatives=alternatives or [],
        )

    def __str__(self) -> str:
        """String representation."""
        return f"Intervention({self.type.value}: {self.reason[:50]}...)"
