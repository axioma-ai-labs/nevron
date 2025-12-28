"""Runtime monitoring router - endpoints for monitoring the autonomous runtime."""

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from src.api.dependencies import get_runtime, verify_api_key
from src.api.schemas import (
    APIResponse,
    BackgroundProcess,
    BackgroundStatistics,
    FullRuntimeStatistics,
    QueueStatistics,
    RuntimeState,
    RuntimeStatistics,
    ScheduledTask,
    SchedulerStatistics,
)
from src.runtime.runtime import AutonomousRuntime


router = APIRouter()


@router.get("/statistics", response_model=APIResponse[FullRuntimeStatistics])
async def get_runtime_statistics(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[FullRuntimeStatistics]:
    """Get comprehensive runtime statistics.

    Returns statistics for runtime, queue, scheduler, and background processes.
    """
    try:
        stats = runtime.get_statistics()

        # Parse runtime stats
        runtime_data = stats.get("runtime", {})
        runtime_stats = RuntimeStatistics(
            state=runtime_data.get("state", "unknown"),
            started_at=(
                datetime.fromisoformat(runtime_data["started_at"])
                if runtime_data.get("started_at")
                else None
            ),
            uptime_seconds=runtime_data.get("uptime_seconds", 0.0),
            events_processed=runtime_data.get("events_processed", 0),
            events_failed=runtime_data.get("events_failed", 0),
            current_queue_size=runtime_data.get("current_queue_size", 0),
            last_event_at=(
                datetime.fromisoformat(runtime_data["last_event_at"])
                if runtime_data.get("last_event_at")
                else None
            ),
        )

        # Parse queue stats
        queue_data = stats.get("queue", {})
        queue_inner = queue_data.get("statistics", {})
        queue_stats = QueueStatistics(
            size=queue_data.get("size", 0),
            paused=queue_data.get("paused", False),
            total_enqueued=queue_inner.get("total_enqueued", 0),
            total_dequeued=queue_inner.get("total_dequeued", 0),
            total_expired=queue_inner.get("total_expired", 0),
            by_priority=queue_inner.get("by_priority", {}),
            by_type=queue_inner.get("by_type", {}),
        )

        # Parse scheduler stats
        scheduler_data = stats.get("scheduler", {})
        scheduler_stats = SchedulerStatistics(
            tasks_scheduled=scheduler_data.get("tasks_scheduled", 0),
            tasks_executed=scheduler_data.get("tasks_executed", 0),
            next_task=scheduler_data.get("next_task"),
            next_run_at=(
                datetime.fromisoformat(scheduler_data["next_run_at"])
                if scheduler_data.get("next_run_at")
                else None
            ),
        )

        # Parse background stats
        bg_data = stats.get("background", {})
        processes = []
        for name, proc_data in bg_data.get("processes", {}).items():
            proc = BackgroundProcess(
                name=name,
                state=proc_data.get("state", "unknown"),
                iterations=proc_data.get("iterations", 0),
                errors=proc_data.get("errors", 0),
                last_run_at=(
                    datetime.fromisoformat(proc_data["last_run_at"])
                    if proc_data.get("last_run_at")
                    else None
                ),
                last_error=proc_data.get("last_error"),
            )
            processes.append(proc)

        background_stats = BackgroundStatistics(
            processes=processes,
            total_running=bg_data.get("total_running", 0),
            total_errors=bg_data.get("total_errors", 0),
        )

        full_stats = FullRuntimeStatistics(
            runtime=runtime_stats,
            queue=queue_stats,
            scheduler=scheduler_stats,
            background=background_stats,
        )

        return APIResponse(
            success=True,
            data=full_stats,
            message="Runtime statistics retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get runtime statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get runtime statistics: {str(e)}",
        )


@router.get("/state", response_model=APIResponse[RuntimeState])
async def get_runtime_state(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[RuntimeState]:
    """Get current runtime state.

    Returns whether the runtime is running, paused, etc.
    """
    try:
        state = RuntimeState(
            state=runtime.state.value,
            is_running=runtime.is_running,
            is_paused=runtime.state.value == "paused",
        )

        return APIResponse(
            success=True,
            data=state,
            message="Runtime state retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get runtime state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get runtime state: {str(e)}",
        )


@router.get("/queue", response_model=APIResponse[QueueStatistics])
async def get_queue_statistics(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[QueueStatistics]:
    """Get event queue statistics.

    Returns queue size, counts by priority and type.
    """
    try:
        queue = runtime.queue
        stats = queue.get_statistics()

        queue_stats = QueueStatistics(
            size=queue.qsize(),
            paused=queue.is_paused(),
            total_enqueued=stats.total_enqueued,
            total_dequeued=stats.total_dequeued,
            total_expired=stats.total_expired,
            by_priority=dict(stats.by_priority),
            by_type=dict(stats.by_type),
        )

        return APIResponse(
            success=True,
            data=queue_stats,
            message="Queue statistics retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get queue statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue statistics: {str(e)}",
        )


@router.get("/scheduler", response_model=APIResponse[List[ScheduledTask]])
async def get_scheduled_tasks(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[ScheduledTask]]:
    """Get list of scheduled tasks.

    Returns all scheduled tasks with their next run times.
    """
    try:
        scheduler = runtime.scheduler
        stats = scheduler.get_statistics()

        # Get scheduled tasks from the scheduler
        tasks: List[ScheduledTask] = []

        # The scheduler stores tasks internally - we'll return what we can from stats
        # In a full implementation, you'd expose the task list from the scheduler
        if stats.next_task_at:
            task = ScheduledTask(
                name="next_scheduled_task",  # Name not available in stats
                next_run=stats.next_task_at,
                run_count=0,
                is_recurring=False,
            )
            tasks.append(task)

        return APIResponse(
            success=True,
            data=tasks,
            message="Scheduled tasks retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get scheduled tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduled tasks: {str(e)}",
        )


@router.get("/background", response_model=APIResponse[BackgroundStatistics])
async def get_background_processes(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[BackgroundStatistics]:
    """Get background process statistics.

    Returns information about all background processes.
    """
    try:
        bg_manager = runtime.background
        stats = bg_manager.get_statistics()  # Returns Dict[name, process_stats]

        processes = []
        total_running = 0
        total_errors = 0
        for name, proc_data in stats.items():
            proc = BackgroundProcess(
                name=name,
                state=proc_data.get("state", "unknown"),
                iterations=proc_data.get("iterations", 0),
                errors=proc_data.get("errors", 0),
                last_run_at=(
                    datetime.fromisoformat(proc_data["last_run_at"])
                    if proc_data.get("last_run_at")
                    else None
                ),
                last_error=proc_data.get("last_error"),
            )
            processes.append(proc)
            if proc_data.get("state") == "running":
                total_running += 1
            total_errors += proc_data.get("errors", 0)

        bg_stats = BackgroundStatistics(
            processes=processes,
            total_running=total_running,
            total_errors=total_errors,
        )

        return APIResponse(
            success=True,
            data=bg_stats,
            message="Background processes retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get background processes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get background processes: {str(e)}",
        )


@router.post("/start", response_model=APIResponse[Dict[str, Any]])
async def start_runtime(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Start the autonomous runtime.

    Starts event processing, scheduler, and background processes.
    """
    try:
        if runtime.is_running:
            return APIResponse(
                success=True,
                data={"status": "already_running", "state": runtime.state.value},
                message="Runtime is already running",
            )

        await runtime.start()
        logger.info("Runtime started via API")

        return APIResponse(
            success=True,
            data={"status": "started", "state": runtime.state.value},
            message="Runtime started",
        )
    except Exception as e:
        logger.error(f"Failed to start runtime: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start runtime: {str(e)}",
        )


@router.post("/stop", response_model=APIResponse[Dict[str, Any]])
async def stop_runtime(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Stop the autonomous runtime.

    Gracefully stops all runtime components.
    """
    try:
        if not runtime.is_running:
            return APIResponse(
                success=True,
                data={"status": "already_stopped", "state": runtime.state.value},
                message="Runtime is already stopped",
            )

        await runtime.stop()
        logger.info("Runtime stopped via API")

        return APIResponse(
            success=True,
            data={"status": "stopped", "state": runtime.state.value},
            message="Runtime stopped",
        )
    except Exception as e:
        logger.error(f"Failed to stop runtime: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop runtime: {str(e)}",
        )


@router.post("/pause", response_model=APIResponse[Dict[str, Any]])
async def pause_runtime(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Pause event processing.

    Pauses the runtime without fully stopping it.
    """
    try:
        if not runtime.is_running:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Runtime is not running",
            )

        await runtime.pause()
        logger.info("Runtime paused via API")

        return APIResponse(
            success=True,
            data={"status": "paused", "state": runtime.state.value},
            message="Runtime paused",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to pause runtime: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to pause runtime: {str(e)}",
        )


@router.post("/resume", response_model=APIResponse[Dict[str, Any]])
async def resume_runtime(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Resume event processing.

    Resumes a paused runtime.
    """
    try:
        if runtime.state.value != "paused":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Runtime is not paused",
            )

        await runtime.resume()
        logger.info("Runtime resumed via API")

        return APIResponse(
            success=True,
            data={"status": "resumed", "state": runtime.state.value},
            message="Runtime resumed",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume runtime: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume runtime: {str(e)}",
        )
