"""Metacognition-related schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MonitoringState(BaseModel):
    """Current state of the metacognitive monitor."""

    is_stuck: bool = False
    confidence_level: float = 0.5
    failure_risk: float = 0.0
    intervention_count: int = 0
    actions_since_intervention: int = 0
    consecutive_failures: int = 0


class Intervention(BaseModel):
    """Intervention triggered by the monitor."""

    type: str
    reason: str
    suggested_action: Optional[str] = None
    wait_seconds: float = 0.0
    priority: int = 1
    alternatives: List[str] = Field(default_factory=list)
    timestamp: datetime


class ConfidenceEstimate(BaseModel):
    """Confidence estimation result."""

    level: float
    explanation: str
    should_request_help: bool
    would_benefit_from: List[str] = Field(default_factory=list)


class FailurePrediction(BaseModel):
    """Failure prediction for an action."""

    action: str
    probability: float
    is_high_risk: bool
    reason_details: List[str]
    suggested_alternatives: List[str] = Field(default_factory=list)
    wait_seconds: float = 0.0


class FailurePredictionRequest(BaseModel):
    """Request for failure prediction."""

    action: str
    context: Dict[str, Any] = Field(default_factory=dict)


class LoopDetectorStats(BaseModel):
    """Loop detector statistics."""

    current_sequence_length: int
    max_repetitions_seen: int
    is_stuck: bool
    loop_description: Optional[str] = None


class FailurePredictorStats(BaseModel):
    """Failure predictor statistics."""

    total_predictions: int
    high_risk_predictions: int
    failures_prevented: int


class HumanHandoffStats(BaseModel):
    """Human handoff statistics."""

    requests_made: int
    responses_received: int
    pending_requests: int


class MetacognitionStatistics(BaseModel):
    """Full metacognition statistics."""

    state: MonitoringState
    loop_detector: LoopDetectorStats
    failure_predictor: FailurePredictorStats
    human_handoff: HumanHandoffStats
    total_interventions: int
    handoff_enabled: bool
