"""Learning-related schemas."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ActionStats(BaseModel):
    """Statistics for a single action."""

    action: str
    total_count: int
    success_count: int
    failure_count: int
    success_rate: float
    average_reward: float
    recent_success_rate: float
    last_used: Optional[datetime] = None


class LearningOutcome(BaseModel):
    """Result of learning from an action."""

    action: str
    reward: float
    success: bool
    new_success_rate: float
    bias_change: float
    critique_generated: bool = False
    lesson_created: bool = False
    timestamp: datetime


class Critique(BaseModel):
    """Self-critique from failure analysis."""

    action: str
    what_went_wrong: str
    better_approach: str
    lesson_learned: str
    confidence: float
    timestamp: datetime


class Lesson(BaseModel):
    """Learned lesson."""

    id: str
    summary: str
    situation: str
    action: str
    what_went_wrong: str
    better_approach: str
    times_reinforced: int = 0
    reliability: float
    created_at: datetime


class ImprovementSuggestion(BaseModel):
    """Improvement suggestion from pattern analysis."""

    pattern: str
    suggestion: str
    affected_actions: List[str]
    confidence: float


class LearningStatistics(BaseModel):
    """Overall learning statistics."""

    total_actions_tracked: int
    total_outcomes: int
    overall_success_rate: float
    best_performing: Optional[str] = None
    worst_performing: Optional[str] = None
    lessons_count: int = 0
    critiques_count: int = 0


class FailingAction(BaseModel):
    """Action with low success rate."""

    action: str
    stats: ActionStats
    recent_errors: List[str] = Field(default_factory=list)
