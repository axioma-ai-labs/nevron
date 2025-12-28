"""Metacognition router - endpoints for metacognitive monitoring."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from src.api.dependencies import get_monitor, verify_api_key
from src.api.schemas import (
    APIResponse,
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
from src.metacognition.monitor import MetacognitiveMonitor


router = APIRouter()


@router.get("/statistics", response_model=APIResponse[MetacognitionStatistics])
async def get_metacognition_statistics(
    monitor: MetacognitiveMonitor = Depends(get_monitor),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[MetacognitionStatistics]:
    """Get full metacognition statistics.

    Returns state, loop detector, failure predictor, and handoff stats.
    """
    try:
        raw_stats = monitor.get_statistics()

        # Parse state
        state_data = raw_stats.get("state", {})
        state = MonitoringState(
            is_stuck=state_data.get("is_stuck", False),
            confidence_level=state_data.get("confidence_level", 0.5),
            failure_risk=state_data.get("failure_risk", 0.0),
            intervention_count=state_data.get("intervention_count", 0),
            actions_since_intervention=state_data.get("actions_since_intervention", 0),
            consecutive_failures=raw_stats.get("consecutive_failures", 0),
        )

        # Parse loop detector stats
        loop_data = raw_stats.get("loop_detector", {})
        loop_detector = LoopDetectorStats(
            current_sequence_length=loop_data.get("current_sequence_length", 0),
            max_repetitions_seen=loop_data.get("max_repetitions_seen", 0),
            is_stuck=loop_data.get("is_stuck", False),
            loop_description=loop_data.get("loop_description"),
        )

        # Parse failure predictor stats
        fp_data = raw_stats.get("failure_predictor", {})
        failure_predictor = FailurePredictorStats(
            total_predictions=fp_data.get("total_predictions", 0),
            high_risk_predictions=fp_data.get("high_risk_predictions", 0),
            failures_prevented=fp_data.get("failures_prevented", 0),
        )

        # Parse human handoff stats
        hh_data = raw_stats.get("human_handoff", {})
        human_handoff = HumanHandoffStats(
            requests_made=hh_data.get("requests_made", 0),
            responses_received=hh_data.get("responses_received", 0),
            pending_requests=hh_data.get("pending_requests", 0),
        )

        stats = MetacognitionStatistics(
            state=state,
            loop_detector=loop_detector,
            failure_predictor=failure_predictor,
            human_handoff=human_handoff,
            total_interventions=raw_stats.get("total_interventions", 0),
            handoff_enabled=raw_stats.get("handoff_enabled", False),
        )

        return APIResponse(
            success=True,
            data=stats,
            message="Metacognition statistics retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get metacognition statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get metacognition statistics: {str(e)}",
        )


@router.get("/state", response_model=APIResponse[MonitoringState])
async def get_monitoring_state(
    monitor: MetacognitiveMonitor = Depends(get_monitor),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[MonitoringState]:
    """Get current monitoring state.

    Returns stuck status, confidence level, failure risk.
    """
    try:
        raw_state = monitor.get_state()

        state = MonitoringState(
            is_stuck=raw_state.is_stuck,
            confidence_level=raw_state.confidence_level,
            failure_risk=raw_state.failure_risk,
            intervention_count=raw_state.intervention_count,
            actions_since_intervention=raw_state.actions_since_intervention,
            consecutive_failures=0,  # Get from stats
        )

        return APIResponse(
            success=True,
            data=state,
            message="Monitoring state retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get monitoring state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get monitoring state: {str(e)}",
        )


@router.get("/interventions", response_model=APIResponse[List[Intervention]])
async def get_interventions(
    limit: int = Query(default=50, le=200),
    monitor: MetacognitiveMonitor = Depends(get_monitor),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[Intervention]]:
    """Get intervention history.

    Args:
        limit: Maximum number of interventions to return
    """
    try:
        raw_interventions = monitor.get_intervention_history(limit=limit)

        interventions = [
            Intervention(
                type=i.type.value,
                reason=i.reason,
                suggested_action=i.suggested_action,
                wait_seconds=i.wait_seconds,
                priority=i.priority,
                alternatives=i.alternatives or [],
                timestamp=i.created_at,  # Map from created_at
            )
            for i in raw_interventions
        ]

        return APIResponse(
            success=True,
            data=interventions,
            message=f"Retrieved {len(interventions)} interventions",
        )
    except Exception as e:
        logger.error(f"Failed to get interventions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get interventions: {str(e)}",
        )


@router.get("/confidence", response_model=APIResponse[ConfidenceEstimate])
async def get_confidence_estimate(
    goal: str = Query(default=None, description="Current goal"),
    success_rate: float = Query(default=0.5, ge=0.0, le=1.0),
    has_memories: bool = Query(default=False),
    error_state: bool = Query(default=False),
    monitor: MetacognitiveMonitor = Depends(get_monitor),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[ConfidenceEstimate]:
    """Get confidence estimation for current state.

    Args:
        goal: Current goal (optional)
        success_rate: Recent success rate
        has_memories: Whether relevant memories exist
        error_state: Whether in error state
    """
    try:
        estimate = monitor.estimate_confidence(
            goal=goal,
            has_memories=has_memories,
            success_rate=success_rate,
            error_state=error_state,
        )

        # Convert Optional[str] to List[str] for API schema
        would_benefit = [estimate.would_benefit_from] if estimate.would_benefit_from else []

        confidence = ConfidenceEstimate(
            level=estimate.level,
            explanation=estimate.explanation,
            should_request_help=estimate.should_request_help,
            would_benefit_from=would_benefit,
        )

        return APIResponse(
            success=True,
            data=confidence,
            message="Confidence estimate retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get confidence estimate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get confidence estimate: {str(e)}",
        )


@router.post("/predict-failure", response_model=APIResponse[FailurePrediction])
async def predict_failure(
    request: FailurePredictionRequest,
    monitor: MetacognitiveMonitor = Depends(get_monitor),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[FailurePrediction]:
    """Predict failure probability for an action.

    Args:
        request: Action and context for prediction
    """
    try:
        prediction = monitor.predict_failure(
            action=request.action,
            context=request.context,
        )

        failure_pred = FailurePrediction(
            action=prediction.action,
            probability=prediction.probability,
            is_high_risk=prediction.is_high_risk,
            reason_details=prediction.reason_details,
            suggested_alternatives=prediction.suggested_alternatives or [],
            wait_seconds=prediction.wait_seconds,
        )

        return APIResponse(
            success=True,
            data=failure_pred,
            message="Failure prediction generated",
        )
    except Exception as e:
        logger.error(f"Failed to predict failure: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to predict failure: {str(e)}",
        )


@router.get("/loop-detector", response_model=APIResponse[LoopDetectorStats])
async def get_loop_detector_stats(
    monitor: MetacognitiveMonitor = Depends(get_monitor),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[LoopDetectorStats]:
    """Get loop detector statistics.

    Returns information about detected repetitive patterns.
    """
    try:
        loop_detector = monitor.get_loop_detector()
        raw_stats = loop_detector.get_statistics()

        stats = LoopDetectorStats(
            current_sequence_length=raw_stats.get("current_sequence_length", 0),
            max_repetitions_seen=raw_stats.get("max_repetitions_seen", 0),
            is_stuck=raw_stats.get("is_stuck", False),
            loop_description=raw_stats.get("loop_description"),
        )

        return APIResponse(
            success=True,
            data=stats,
            message="Loop detector statistics retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get loop detector stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get loop detector stats: {str(e)}",
        )


@router.post("/clear", response_model=APIResponse[Dict[str, Any]])
async def clear_monitor(
    monitor: MetacognitiveMonitor = Depends(get_monitor),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Clear the metacognitive monitor state.

    Resets all monitoring state and history.
    """
    try:
        monitor.clear()

        return APIResponse(
            success=True,
            data={"status": "cleared"},
            message="Metacognitive monitor cleared",
        )
    except Exception as e:
        logger.error(f"Failed to clear monitor: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear monitor: {str(e)}",
        )
