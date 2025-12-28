"""Learning module for continuous improvement.

This module provides:
- ActionTracker: Track success rates per action and context
- SelfCritic: RLAIF self-critique for failures
- StrategyAdapter: Adjust planning biases based on learning
- LessonRepository: Store and retrieve learned lessons
- AdaptiveLearningModule: Unified interface for all learning
"""

from src.learning.adapter import ActionBias, AdaptationContext, StrategyAdapter
from src.learning.critic import (
    Critique,
    CritiqueLevel,
    FailedAction,
    ImprovementSuggestion,
    SelfCritic,
)
from src.learning.learning_module import (
    AdaptiveLearningModule,
    LearningConfig,
    LearningOutcome,
    get_learning_module,
)
from src.learning.lessons import Lesson, LessonRepository
from src.learning.tracker import ActionOutcome, ActionStats, ActionTracker


__all__ = [
    # Tracker
    "ActionTracker",
    "ActionOutcome",
    "ActionStats",
    # Critic
    "SelfCritic",
    "Critique",
    "CritiqueLevel",
    "FailedAction",
    "ImprovementSuggestion",
    # Adapter
    "StrategyAdapter",
    "ActionBias",
    "AdaptationContext",
    # Lessons
    "Lesson",
    "LessonRepository",
    # Main module
    "AdaptiveLearningModule",
    "LearningConfig",
    "LearningOutcome",
    "get_learning_module",
]
