"""Runtime monitoring router - endpoints for monitoring the autonomous runtime.

This router reads state from shared storage and sends commands to the agent
process via the command queue. It does NOT own the runtime directly.
"""

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from src.api.dependencies import get_commands, get_shared_state, verify_api_key
from src.api.schemas import (
    APIResponse,
    BackgroundStatistics,
    FullRuntimeStatistics,
    QueueStatistics,
    RuntimeState,
    RuntimeStatistics,
    ScheduledTask,
    SchedulerStatistics,
)
from src.core.agent_commands import CommandQueue, CommandType
from src.core.agent_state import SharedStateManager


router = APIRouter()


@router.get("/statistics", response_model=APIResponse[FullRuntimeStatistics])
async def get_runtime_statistics(
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[FullRuntimeStatistics]:
    """Get comprehensive runtime statistics.

    Returns statistics from the shared state. Note: Some statistics
    (queue, scheduler, background) are only available when the agent
    is running and writing to shared state.
    """
    try:
        state = state_manager.get_state()

        # Build runtime stats from shared state
        runtime_stats = RuntimeStatistics(
            state=state.status,
            started_at=(
                datetime.fromisoformat(state.started_at.replace("Z", "+00:00"))
                if state.started_at
                else None
            ),
            uptime_seconds=0.0,  # Calculate if needed
            events_processed=state.cycle_count,
            events_failed=state.failed_actions,
            current_queue_size=0,  # Not tracked in shared state
            last_event_at=(
                datetime.fromisoformat(state.last_action_time.replace("Z", "+00:00"))
                if state.last_action_time
                else None
            ),
        )

        # Calculate uptime if running
        if state.started_at and state.is_running:
            try:
                started = datetime.fromisoformat(state.started_at.replace("Z", "+00:00"))
                from datetime import timezone

                now = datetime.now(timezone.utc)
                runtime_stats.uptime_seconds = (now - started).total_seconds()
            except (ValueError, TypeError):
                pass

        # Queue stats (limited info from shared state)
        queue_stats = QueueStatistics(
            size=0,
            paused=state.status == "paused",
            total_enqueued=state.cycle_count,
            total_dequeued=state.cycle_count,
            total_expired=0,
            by_priority={},
            by_type={},
        )

        # Scheduler stats (not available in decoupled mode)
        scheduler_stats = SchedulerStatistics(
            tasks_scheduled=0,
            tasks_executed=0,
            next_task=None,
            next_run_at=None,
        )

        # Background stats (not available in decoupled mode)
        background_stats = BackgroundStatistics(
            processes=[],
            total_running=0,
            total_errors=0,
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
            message="Runtime statistics retrieved from shared state",
        )
    except Exception as e:
        logger.error(f"Failed to get runtime statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get runtime statistics: {str(e)}",
        )


@router.get("/state", response_model=APIResponse[RuntimeState])
async def get_runtime_state(
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[RuntimeState]:
    """Get current runtime state.

    Returns whether the runtime is running, paused, etc.
    """
    try:
        agent_state = state_manager.get_state()
        is_alive = state_manager.is_agent_alive()

        # Determine effective state
        effective_state = agent_state.status
        if agent_state.is_running and not is_alive:
            effective_state = "stale"  # Agent claims running but no recent heartbeat

        state = RuntimeState(
            state=effective_state,
            is_running=agent_state.is_running and is_alive,
            is_paused=agent_state.status == "paused",
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
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[QueueStatistics]:
    """Get event queue statistics.

    Note: In decoupled mode, detailed queue statistics are not available.
    Only basic counts from shared state are returned.
    """
    try:
        agent_state = state_manager.get_state()

        queue_stats = QueueStatistics(
            size=0,  # Not tracked
            paused=agent_state.status == "paused",
            total_enqueued=agent_state.cycle_count,
            total_dequeued=agent_state.cycle_count,
            total_expired=0,
            by_priority={},
            by_type={},
        )

        return APIResponse(
            success=True,
            data=queue_stats,
            message="Queue statistics retrieved (limited in decoupled mode)",
        )
    except Exception as e:
        logger.error(f"Failed to get queue statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get queue statistics: {str(e)}",
        )


@router.get("/scheduler", response_model=APIResponse[List[ScheduledTask]])
async def get_scheduled_tasks(
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[ScheduledTask]]:
    """Get list of scheduled tasks.

    Note: In decoupled mode, scheduler information is not available.
    """
    try:
        # No scheduler info in decoupled mode
        return APIResponse(
            success=True,
            data=[],
            message="Scheduler not available in decoupled mode",
        )
    except Exception as e:
        logger.error(f"Failed to get scheduled tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get scheduled tasks: {str(e)}",
        )


@router.get("/background", response_model=APIResponse[BackgroundStatistics])
async def get_background_processes(
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[BackgroundStatistics]:
    """Get background process statistics.

    Note: In decoupled mode, background process information is not available.
    """
    try:
        bg_stats = BackgroundStatistics(
            processes=[],
            total_running=0,
            total_errors=0,
        )

        return APIResponse(
            success=True,
            data=bg_stats,
            message="Background processes not available in decoupled mode",
        )
    except Exception as e:
        logger.error(f"Failed to get background processes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get background processes: {str(e)}",
        )


@router.post("/start", response_model=APIResponse[Dict[str, Any]])
async def start_runtime(
    state_manager: SharedStateManager = Depends(get_shared_state),
    commands: CommandQueue = Depends(get_commands),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Start the autonomous runtime.

    In decoupled mode, this checks if the agent is already running.
    To start the agent, use 'make run-agent' in a separate terminal.
    """
    try:
        agent_state = state_manager.get_state()
        is_alive = state_manager.is_agent_alive()

        if agent_state.is_running and is_alive:
            return APIResponse(
                success=True,
                data={
                    "status": "already_running",
                    "state": agent_state.status,
                    "pid": agent_state.pid,
                },
                message="Agent is already running",
            )

        # In decoupled mode, we can't start the agent from the API
        # The user needs to run 'make run-agent' separately
        return APIResponse(
            success=False,
            data={
                "status": "not_running",
                "state": agent_state.status,
                "instruction": "Run 'make run-agent' to start the agent process",
            },
            message="Agent not running. Start with 'make run-agent' in a separate terminal.",
        )
    except Exception as e:
        logger.error(f"Failed to check runtime status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check runtime status: {str(e)}",
        )


@router.post("/stop", response_model=APIResponse[Dict[str, Any]])
async def stop_runtime(
    state_manager: SharedStateManager = Depends(get_shared_state),
    commands: CommandQueue = Depends(get_commands),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Stop the autonomous runtime.

    Sends a stop command to the agent process via the command queue.
    """
    try:
        agent_state = state_manager.get_state()
        is_alive = state_manager.is_agent_alive()

        if not agent_state.is_running or not is_alive:
            return APIResponse(
                success=True,
                data={"status": "already_stopped", "state": agent_state.status},
                message="Agent is already stopped",
            )

        # Send stop command
        command = commands.send_command(CommandType.STOP, timeout_seconds=30.0)
        logger.info(f"Sent stop command: {command.command_id}")

        # Wait briefly for acknowledgment
        result = commands.wait_for_command(command.command_id, timeout_seconds=5.0)

        if result and result.status == "completed":
            return APIResponse(
                success=True,
                data={"status": "stopped", "command_id": command.command_id},
                message="Stop command sent and acknowledged",
            )
        else:
            return APIResponse(
                success=True,
                data={
                    "status": "stop_requested",
                    "command_id": command.command_id,
                    "note": "Command sent, agent will stop shortly",
                },
                message="Stop command sent to agent",
            )
    except Exception as e:
        logger.error(f"Failed to stop runtime: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop runtime: {str(e)}",
        )


@router.post("/pause", response_model=APIResponse[Dict[str, Any]])
async def pause_runtime(
    state_manager: SharedStateManager = Depends(get_shared_state),
    commands: CommandQueue = Depends(get_commands),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Pause event processing.

    Sends a pause command to the agent process.
    """
    try:
        agent_state = state_manager.get_state()
        is_alive = state_manager.is_agent_alive()

        if not agent_state.is_running or not is_alive:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent is not running",
            )

        if agent_state.status == "paused":
            return APIResponse(
                success=True,
                data={"status": "already_paused"},
                message="Agent is already paused",
            )

        # Send pause command
        command = commands.send_command(CommandType.PAUSE, timeout_seconds=30.0)
        logger.info(f"Sent pause command: {command.command_id}")

        # Wait briefly for acknowledgment
        result = commands.wait_for_command(command.command_id, timeout_seconds=5.0)

        if result and result.status == "completed":
            return APIResponse(
                success=True,
                data={"status": "paused", "command_id": command.command_id},
                message="Agent paused",
            )
        else:
            return APIResponse(
                success=True,
                data={
                    "status": "pause_requested",
                    "command_id": command.command_id,
                },
                message="Pause command sent to agent",
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
    state_manager: SharedStateManager = Depends(get_shared_state),
    commands: CommandQueue = Depends(get_commands),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Resume event processing.

    Sends a resume command to the agent process.
    """
    try:
        agent_state = state_manager.get_state()
        is_alive = state_manager.is_agent_alive()

        if not is_alive:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Agent is not running",
            )

        if agent_state.status != "paused":
            return APIResponse(
                success=True,
                data={"status": "not_paused", "state": agent_state.status},
                message="Agent is not paused",
            )

        # Send resume command
        command = commands.send_command(CommandType.RESUME, timeout_seconds=30.0)
        logger.info(f"Sent resume command: {command.command_id}")

        # Wait briefly for acknowledgment
        result = commands.wait_for_command(command.command_id, timeout_seconds=5.0)

        if result and result.status == "completed":
            return APIResponse(
                success=True,
                data={"status": "resumed", "command_id": command.command_id},
                message="Agent resumed",
            )
        else:
            return APIResponse(
                success=True,
                data={
                    "status": "resume_requested",
                    "command_id": command.command_id,
                },
                message="Resume command sent to agent",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resume runtime: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume runtime: {str(e)}",
        )


@router.get("/health", response_model=APIResponse[Dict[str, Any]])
async def get_health(
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Get health status of the agent process.

    Returns detailed health information including:
    - Whether the agent process exists
    - Whether it's sending heartbeats
    - Last heartbeat time
    """
    try:
        full_status = state_manager.get_full_status()
        state = full_status["state"]

        health = {
            "agent_running": state["is_running"],
            "agent_alive": full_status["is_alive"],
            "process_exists": full_status["is_process_running"],
            "pid": state.get("pid"),
            "status": state["status"],
            "last_heartbeat": state.get("last_heartbeat"),
            "cycle_count": state.get("cycle_count", 0),
            "error_count": state.get("error_count", 0),
            "last_error": state.get("last_error"),
        }

        # Determine overall health
        if health["agent_alive"] and health["process_exists"]:
            health["overall"] = "healthy"
        elif health["agent_running"] and not health["agent_alive"]:
            health["overall"] = "stale"  # No recent heartbeat
        elif health["agent_running"] and not health["process_exists"]:
            health["overall"] = "zombie"  # Process died but state not updated
        else:
            health["overall"] = "stopped"

        return APIResponse(
            success=True,
            data=health,
            message=f"Agent health: {health['overall']}",
        )
    except Exception as e:
        logger.error(f"Failed to get health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get health: {str(e)}",
        )
