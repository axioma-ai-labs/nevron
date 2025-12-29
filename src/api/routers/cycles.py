"""Cycles router - endpoints for agent cycle history and monitoring."""

from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel

from src.api.dependencies import verify_api_key
from src.api.schemas import APIResponse
from src.core.cycle_logger import (
    CycleLog,
    get_cycle_logger,
)


router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================


class CycleResponse(BaseModel):
    """Response model for a single cycle."""

    cycle_id: str
    timestamp: str
    planning_input_state: str
    planning_input_recent_actions: List[str]
    planning_output_action: str
    planning_output_reasoning: Optional[str]
    planning_duration_ms: int
    action_name: str
    action_params: Dict[str, Any]
    execution_result: Dict[str, Any]
    execution_success: bool
    execution_error: Optional[str]
    execution_duration_ms: int
    reward: float
    critique: Optional[str]
    lesson_learned: Optional[str]
    memories_stored: List[str]
    llm_provider: str
    llm_model: str
    llm_tokens_used: int
    total_duration_ms: int
    agent_state_after: str


class CycleListResponse(BaseModel):
    """Response for paginated list of cycles."""

    cycles: List[CycleResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class CycleStatsResponse(BaseModel):
    """Response for cycle statistics."""

    total_cycles: int
    successful_cycles: int
    failed_cycles: int
    success_rate: float
    avg_duration_ms: float
    total_rewards: float
    avg_reward: float
    action_counts: Dict[str, int]
    top_actions: List[str]
    cycles_per_hour: float
    last_cycle_time: Optional[str]


def cycle_to_response(cycle: CycleLog) -> CycleResponse:
    """Convert CycleLog to response model."""
    return CycleResponse(**asdict(cycle))


# ============================================================================
# Endpoints
# ============================================================================


@router.get("", response_model=APIResponse[CycleListResponse])
async def get_cycles(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    start_time: Optional[str] = Query(None, description="Filter by start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="Filter by end time (ISO format)"),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[CycleListResponse]:
    """Get paginated list of agent cycles.

    Returns cycle history with optional filtering by action, success status,
    and time range. Results are ordered by timestamp descending (newest first).
    """
    try:
        cycle_logger = get_cycle_logger()
        offset = (page - 1) * page_size

        cycles = cycle_logger.get_recent_cycles(
            limit=page_size + 1,  # Get one extra to check if more exist
            offset=offset,
            action_filter=action,
            success_filter=success,
            start_time=start_time,
            end_time=end_time,
        )

        has_more = len(cycles) > page_size
        if has_more:
            cycles = cycles[:page_size]

        # Get total count for pagination info
        stats = cycle_logger.get_stats(start_time=start_time, end_time=end_time)

        response = CycleListResponse(
            cycles=[cycle_to_response(c) for c in cycles],
            total=stats.total_cycles,
            page=page,
            page_size=page_size,
            has_more=has_more,
        )

        return APIResponse(
            success=True,
            data=response,
            message=f"Retrieved {len(cycles)} cycles",
        )

    except Exception as e:
        logger.error(f"Failed to get cycles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cycles: {str(e)}",
        )


@router.get("/stats", response_model=APIResponse[CycleStatsResponse])
async def get_cycle_stats(
    start_time: Optional[str] = Query(None, description="Filter by start time (ISO format)"),
    end_time: Optional[str] = Query(None, description="Filter by end time (ISO format)"),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[CycleStatsResponse]:
    """Get aggregate statistics for agent cycles.

    Returns success rate, action distribution, average duration,
    rewards, and cycles per hour metrics.
    """
    try:
        cycle_logger = get_cycle_logger()
        stats = cycle_logger.get_stats(start_time=start_time, end_time=end_time)

        response = CycleStatsResponse(
            total_cycles=stats.total_cycles,
            successful_cycles=stats.successful_cycles,
            failed_cycles=stats.failed_cycles,
            success_rate=stats.success_rate,
            avg_duration_ms=stats.avg_duration_ms,
            total_rewards=stats.total_rewards,
            avg_reward=stats.avg_reward,
            action_counts=stats.action_counts,
            top_actions=stats.top_actions,
            cycles_per_hour=stats.cycles_per_hour,
            last_cycle_time=stats.last_cycle_time,
        )

        return APIResponse(
            success=True,
            data=response,
            message="Cycle statistics retrieved",
        )

    except Exception as e:
        logger.error(f"Failed to get cycle stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cycle stats: {str(e)}",
        )


@router.get("/{cycle_id}", response_model=APIResponse[CycleResponse])
async def get_cycle(
    cycle_id: str,
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[CycleResponse]:
    """Get a specific cycle by ID.

    Returns full details of a single agent cycle including
    planning reasoning, execution result, and learning outcomes.
    """
    try:
        cycle_logger = get_cycle_logger()
        cycle = cycle_logger.get_cycle(cycle_id)

        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cycle not found: {cycle_id}",
            )

        return APIResponse(
            success=True,
            data=cycle_to_response(cycle),
            message="Cycle retrieved",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cycle {cycle_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cycle: {str(e)}",
        )


@router.delete("/cleanup", response_model=APIResponse[Dict[str, int]])
async def cleanup_cycles(
    keep_count: int = Query(1000, ge=100, le=10000, description="Number of cycles to keep"),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, int]]:
    """Clean up old cycles from the database.

    Removes cycles beyond the specified keep count, keeping only
    the most recent ones. Minimum keep count is 100.
    """
    try:
        cycle_logger = get_cycle_logger()
        deleted = cycle_logger.cleanup_old_cycles(keep_count=keep_count)

        return APIResponse(
            success=True,
            data={"deleted": deleted, "kept": keep_count},
            message=f"Cleaned up {deleted} old cycles",
        )

    except Exception as e:
        logger.error(f"Failed to cleanup cycles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cleanup cycles: {str(e)}",
        )
