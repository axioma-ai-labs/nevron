"""Pydantic schemas for API responses."""

from src.api.schemas.agent import (
    ActionHistoryItem,
    ActionRequest,
    ActionResponse,
    AgentContext,
    AgentInfo,
    AgentStatus,
)
from src.api.schemas.common import APIResponse, ErrorResponse, HealthCheck, PaginatedResponse
from src.api.schemas.learning import (
    ActionStats,
    Critique,
    FailingAction,
    ImprovementSuggestion,
    LearningOutcome,
    LearningStatistics,
    Lesson,
)
from src.api.schemas.memory import (
    Concept,
    ConsolidationResult,
    Episode,
    Fact,
    MemoryRecallRequest,
    MemoryRecallResponse,
    MemoryStatistics,
    Skill,
)
from src.api.schemas.metacognition import (
    ConfidenceEstimate,
    FailurePrediction,
    FailurePredictionRequest,
    FailurePredictorStats,
    HumanHandoffStats,
    Intervention,
    LoopDetectorStats,
    MetacognitionStatistics,
    MonitoringState,
)
from src.api.schemas.runtime import (
    BackgroundProcess,
    BackgroundStatistics,
    FullRuntimeStatistics,
    QueueStatistics,
    RuntimeState,
    RuntimeStatistics,
    ScheduledTask,
    ScheduleRequest,
    SchedulerStatistics,
)
from src.api.schemas.websocket import WSMessage, WSMessageType, WSPing, WSPong, WSSubscription


__all__ = [
    # Agent schemas
    "ActionHistoryItem",
    "ActionRequest",
    "ActionResponse",
    "AgentContext",
    "AgentInfo",
    "AgentStatus",
    # Common schemas
    "APIResponse",
    "ErrorResponse",
    "HealthCheck",
    "PaginatedResponse",
    # Learning schemas
    "ActionStats",
    "Critique",
    "FailingAction",
    "ImprovementSuggestion",
    "LearningOutcome",
    "LearningStatistics",
    "Lesson",
    # Memory schemas
    "Concept",
    "ConsolidationResult",
    "Episode",
    "Fact",
    "MemoryRecallRequest",
    "MemoryRecallResponse",
    "MemoryStatistics",
    "Skill",
    # Metacognition schemas
    "ConfidenceEstimate",
    "FailurePrediction",
    "FailurePredictionRequest",
    "FailurePredictorStats",
    "HumanHandoffStats",
    "Intervention",
    "LoopDetectorStats",
    "MetacognitionStatistics",
    "MonitoringState",
    # Runtime schemas
    "BackgroundProcess",
    "BackgroundStatistics",
    "FullRuntimeStatistics",
    "QueueStatistics",
    "RuntimeState",
    "RuntimeStatistics",
    "ScheduledTask",
    "ScheduleRequest",
    "SchedulerStatistics",
    # WebSocket schemas
    "WSMessage",
    "WSMessageType",
    "WSPing",
    "WSPong",
    "WSSubscription",
]
