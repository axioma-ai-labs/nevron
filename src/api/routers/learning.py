"""Learning router - endpoints for learning insights and statistics."""

from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from src.api.dependencies import verify_api_key
from src.api.schemas import (
    ActionStats,
    APIResponse,
    Critique,
    FailingAction,
    ImprovementSuggestion,
    LearningOutcome,
    LearningStatistics,
    Lesson,
)
from src.learning.learning_module import AdaptiveLearningModule


router = APIRouter()


def _is_embeddings_error(error: Exception) -> bool:
    """Check if an error is related to missing embeddings API key."""
    error_str = str(error).lower()
    return "api_key" in error_str or "api key" in error_str


def _get_learning_safe() -> Tuple[Optional[AdaptiveLearningModule], bool]:
    """Safely get learning module, returning (learning, embeddings_available).

    Returns:
        Tuple of (learning_module or None, embeddings_available bool)
    """
    try:
        from src.api.dependencies import get_learning
        learning = get_learning()
        return learning, True
    except ValueError as e:
        if _is_embeddings_error(e):
            logger.warning(f"Learning module unavailable - embeddings not configured: {e}")
            return None, False
        raise
    except Exception as e:
        if _is_embeddings_error(e):
            logger.warning(f"Learning module unavailable - embeddings error: {e}")
            return None, False
        raise


@router.get("/statistics", response_model=APIResponse[LearningStatistics])
async def get_learning_statistics(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[LearningStatistics]:
    """Get overall learning statistics.

    Returns action tracking stats, success rates, and lesson counts.
    Returns empty stats with embeddings_available=False if embeddings not configured.
    """
    learning, embeddings_available = _get_learning_safe()

    if not embeddings_available or learning is None:
        stats = LearningStatistics(
            total_actions_tracked=0,
            total_outcomes=0,
            overall_success_rate=0.0,
            best_performing=None,
            worst_performing=None,
            lessons_count=0,
            critiques_count=0,
            embeddings_available=False,
        )
        return APIResponse(
            success=True,
            data=stats,
            message="Embeddings not configured - configure API key in Settings",
        )

    try:
        tracker_stats = learning.get_tracker_statistics()
        lesson_stats = await learning.get_lesson_statistics()

        stats = LearningStatistics(
            total_actions_tracked=tracker_stats.get("total_actions_tracked", 0),
            total_outcomes=tracker_stats.get("total_outcomes", 0),
            overall_success_rate=tracker_stats.get("overall_success_rate", 0.0),
            best_performing=tracker_stats.get("best_performing"),
            worst_performing=tracker_stats.get("worst_performing"),
            lessons_count=lesson_stats.get("total_lessons", 0),
            critiques_count=len(learning.get_recent_critiques(limit=1000)),
            embeddings_available=True,
        )

        return APIResponse(
            success=True,
            data=stats,
            message="Learning statistics retrieved",
        )
    except Exception as e:
        if _is_embeddings_error(e):
            stats = LearningStatistics(
                total_actions_tracked=0,
                total_outcomes=0,
                overall_success_rate=0.0,
                best_performing=None,
                worst_performing=None,
                lessons_count=0,
                critiques_count=0,
                embeddings_available=False,
            )
            return APIResponse(
                success=True,
                data=stats,
                message="Embeddings not configured - configure API key in Settings",
            )
        logger.error(f"Failed to get learning statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get learning statistics: {str(e)}",
        )


@router.get("/history", response_model=APIResponse[List[LearningOutcome]])
async def get_learning_history(
    limit: int = Query(default=50, le=200),
    action: Optional[str] = Query(default=None),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[LearningOutcome]]:
    """Get learning outcome history.

    Args:
        limit: Maximum number of outcomes to return
        action: Optional filter by action name

    Returns empty list if embeddings not configured.
    """
    learning, embeddings_available = _get_learning_safe()

    if not embeddings_available or learning is None:
        return APIResponse(
            success=True,
            data=[],
            message="Embeddings not configured - configure API key in Settings",
        )

    try:
        raw_outcomes = learning.get_learning_history(limit=limit, action=action)

        outcomes = [
            LearningOutcome(
                action=o.action,
                reward=o.reward,
                success=o.success,
                new_success_rate=o.new_success_rate,
                bias_change=o.bias_change,
                critique_generated=o.critique is not None,
                lesson_created=o.lesson_created is not None,
                timestamp=o.timestamp,
            )
            for o in raw_outcomes
        ]

        return APIResponse(
            success=True,
            data=outcomes,
            message=f"Retrieved {len(outcomes)} learning outcomes",
        )
    except Exception as e:
        if _is_embeddings_error(e):
            return APIResponse(
                success=True,
                data=[],
                message="Embeddings not configured - configure API key in Settings",
            )
        logger.error(f"Failed to get learning history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get learning history: {str(e)}",
        )


@router.get("/critiques", response_model=APIResponse[List[Critique]])
async def get_recent_critiques(
    limit: int = Query(default=20, le=100),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[Critique]]:
    """Get recent self-critiques.

    Returns critiques generated from failure analysis.
    Returns empty list if embeddings not configured.
    """
    learning, embeddings_available = _get_learning_safe()

    if not embeddings_available or learning is None:
        return APIResponse(
            success=True,
            data=[],
            message="Embeddings not configured - configure API key in Settings",
        )

    try:
        raw_critiques = learning.get_recent_critiques(limit=limit)

        critiques = [
            Critique(
                action=c.action,
                what_went_wrong=c.what_went_wrong,
                better_approach=c.better_approach,
                lesson_learned=c.lesson_learned,
                confidence=c.confidence,
                timestamp=c.created_at,  # Map from created_at
            )
            for c in raw_critiques
        ]

        return APIResponse(
            success=True,
            data=critiques,
            message=f"Retrieved {len(critiques)} critiques",
        )
    except Exception as e:
        if _is_embeddings_error(e):
            return APIResponse(
                success=True,
                data=[],
                message="Embeddings not configured - configure API key in Settings",
            )
        logger.error(f"Failed to get critiques: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get critiques: {str(e)}",
        )


@router.get("/failing-actions", response_model=APIResponse[List[FailingAction]])
async def get_failing_actions(
    threshold: float = Query(default=0.3, ge=0.0, le=1.0),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[FailingAction]]:
    """Get actions with low success rates.

    Args:
        threshold: Success rate threshold (default 0.3 = 30%)

    Returns empty list if embeddings not configured.
    """
    learning, embeddings_available = _get_learning_safe()

    if not embeddings_available or learning is None:
        return APIResponse(
            success=True,
            data=[],
            message="Embeddings not configured - configure API key in Settings",
        )

    try:
        raw_failing = learning.get_failing_actions(threshold=threshold)

        failing_actions = []
        for action_name, raw_stats in raw_failing:
            stats = ActionStats(
                action=raw_stats.action,
                total_count=raw_stats.total_count,
                success_count=raw_stats.success_count,
                failure_count=raw_stats.failure_count,
                success_rate=raw_stats.success_rate,
                average_reward=raw_stats.average_reward,
                recent_success_rate=raw_stats.recent_success_rate,
                last_used=raw_stats.last_used,
            )
            failing_actions.append(
                FailingAction(
                    action=action_name,
                    stats=stats,
                    recent_errors=[],  # Would need to track these separately
                )
            )

        return APIResponse(
            success=True,
            data=failing_actions,
            message=f"Retrieved {len(failing_actions)} failing actions",
        )
    except Exception as e:
        if _is_embeddings_error(e):
            return APIResponse(
                success=True,
                data=[],
                message="Embeddings not configured - configure API key in Settings",
            )
        logger.error(f"Failed to get failing actions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get failing actions: {str(e)}",
        )


@router.get("/suggestions", response_model=APIResponse[List[ImprovementSuggestion]])
async def get_improvement_suggestions(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[ImprovementSuggestion]]:
    """Get improvement suggestions from pattern analysis.

    Returns suggestions for improving agent performance.
    Returns empty list if embeddings not configured.
    """
    learning, embeddings_available = _get_learning_safe()

    if not embeddings_available or learning is None:
        return APIResponse(
            success=True,
            data=[],
            message="Embeddings not configured - configure API key in Settings",
        )

    try:
        # Get cached suggestions
        raw_suggestions = learning.get_improvement_suggestions()

        suggestions = [
            ImprovementSuggestion(
                pattern=s.pattern,
                suggestion=s.suggestion,
                affected_actions=s.affected_actions,
                confidence=s.confidence,
            )
            for s in raw_suggestions
        ]

        return APIResponse(
            success=True,
            data=suggestions,
            message=f"Retrieved {len(suggestions)} improvement suggestions",
        )
    except Exception as e:
        if _is_embeddings_error(e):
            return APIResponse(
                success=True,
                data=[],
                message="Embeddings not configured - configure API key in Settings",
            )
        logger.error(f"Failed to get improvement suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get improvement suggestions: {str(e)}",
        )


@router.get("/action/{action_name}/stats", response_model=APIResponse[ActionStats])
async def get_action_stats(
    action_name: str,
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[ActionStats]:
    """Get statistics for a specific action.

    Args:
        action_name: Name of the action

    Returns 404 if embeddings not configured or action not found.
    """
    learning, embeddings_available = _get_learning_safe()

    if not embeddings_available or learning is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Embeddings not configured - configure API key in Settings",
        )

    try:
        raw_stats = learning.get_action_stats(action_name)

        if not raw_stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No statistics found for action: {action_name}",
            )

        stats = ActionStats(
            action=raw_stats.action,
            total_count=raw_stats.total_count,
            success_count=raw_stats.success_count,
            failure_count=raw_stats.failure_count,
            success_rate=raw_stats.success_rate,
            average_reward=raw_stats.average_reward,
            recent_success_rate=raw_stats.recent_success_rate,
            last_used=raw_stats.last_used,
        )

        return APIResponse(
            success=True,
            data=stats,
            message=f"Statistics retrieved for action: {action_name}",
        )
    except HTTPException:
        raise
    except Exception as e:
        if _is_embeddings_error(e):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Embeddings not configured - configure API key in Settings",
            )
        logger.error(f"Failed to get action stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get action stats: {str(e)}",
        )


@router.get("/lessons", response_model=APIResponse[List[Lesson]])
async def get_lessons(
    limit: int = Query(default=50, le=200),
    action: Optional[str] = Query(default=None),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[Lesson]]:
    """Get stored lessons.

    Args:
        limit: Maximum number of lessons to return
        action: Optional filter by action name

    Returns empty list if embeddings not configured.
    """
    learning, embeddings_available = _get_learning_safe()

    if not embeddings_available or learning is None:
        return APIResponse(
            success=True,
            data=[],
            message="Embeddings not configured - configure API key in Settings",
        )

    try:
        if action:
            raw_lessons = await learning.get_relevant_lessons(
                context={"action": action},
                top_k=limit,
            )
        else:
            # Get all lessons - need to query the lesson repository
            raw_lessons = await learning.get_relevant_lessons(
                context={},
                top_k=limit,
            )

        lessons = [
            Lesson(
                id=lesson.id,
                summary=lesson.summary,
                situation=lesson.situation,
                action=lesson.action,
                what_went_wrong=lesson.what_went_wrong,
                better_approach=lesson.better_approach,
                times_reinforced=lesson.reinforcement_count,  # Map from reinforcement_count
                reliability=lesson.reliability,
                created_at=lesson.learned_at,  # Map from learned_at
            )
            for lesson in raw_lessons
        ]

        return APIResponse(
            success=True,
            data=lessons,
            message=f"Retrieved {len(lessons)} lessons",
        )
    except Exception as e:
        if _is_embeddings_error(e):
            return APIResponse(
                success=True,
                data=[],
                message="Embeddings not configured - configure API key in Settings",
            )
        logger.error(f"Failed to get lessons: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get lessons: {str(e)}",
        )


@router.post("/analyze-failures", response_model=APIResponse[List[ImprovementSuggestion]])
async def analyze_recent_failures(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[ImprovementSuggestion]]:
    """Analyze recent failures for patterns.

    Triggers pattern analysis on recent failures and returns suggestions.
    Returns empty list if embeddings not configured.
    """
    learning, embeddings_available = _get_learning_safe()

    if not embeddings_available or learning is None:
        return APIResponse(
            success=True,
            data=[],
            message="Embeddings not configured - configure API key in Settings",
        )

    try:
        raw_suggestions = await learning.analyze_recent_failures()

        suggestions = [
            ImprovementSuggestion(
                pattern=s.pattern,
                suggestion=s.suggestion,
                affected_actions=s.affected_actions,
                confidence=s.confidence,
            )
            for s in raw_suggestions
        ]

        return APIResponse(
            success=True,
            data=suggestions,
            message=f"Analysis complete: {len(suggestions)} suggestions generated",
        )
    except Exception as e:
        if _is_embeddings_error(e):
            return APIResponse(
                success=True,
                data=[],
                message="Embeddings not configured - configure API key in Settings",
            )
        logger.error(f"Failed to analyze failures: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze failures: {str(e)}",
        )
