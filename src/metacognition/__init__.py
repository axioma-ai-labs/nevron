"""Metacognitive Monitor Module.

Provides self-awareness and failure prediction for the agent.
Inspired by VIGIL framework - decoupled from task execution.

Components:
- LoopDetector: Detect repetitive behavior patterns
- FailurePredictor: Predict impending failures
- ConfidenceEstimator: Estimate confidence in current approach
- HumanHandoff: Request human assistance when needed
- MetacognitiveMonitor: Unified interface for all components
"""

from src.metacognition.confidence_estimator import (
    ConfidenceEstimate,
    ConfidenceEstimator,
    ConfidenceFactor,
)
from src.metacognition.failure_predictor import (
    FailurePredictor,
    FailurePrediction,
    FailureReason,
)
from src.metacognition.human_handoff import (
    HandoffChannel,
    HumanHandoff,
    HumanRequest,
    HumanResponse,
)
from src.metacognition.intervention import Intervention, InterventionType
from src.metacognition.loop_detector import LoopDetector, LoopPattern, LoopType
from src.metacognition.monitor import MetacognitiveMonitor

__all__ = [
    # Loop Detection
    "LoopDetector",
    "LoopPattern",
    "LoopType",
    # Failure Prediction
    "FailurePredictor",
    "FailurePrediction",
    "FailureReason",
    # Confidence Estimation
    "ConfidenceEstimator",
    "ConfidenceEstimate",
    "ConfidenceFactor",
    # Intervention
    "Intervention",
    "InterventionType",
    # Human Handoff
    "HumanHandoff",
    "HumanRequest",
    "HumanResponse",
    "HandoffChannel",
    # Main Interface
    "MetacognitiveMonitor",
]
