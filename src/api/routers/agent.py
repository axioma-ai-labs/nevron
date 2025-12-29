"""Agent control router - endpoints for managing the AI agent.

This router reads agent state from shared storage and sends commands
to the agent process via the command queue.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from src.api.dependencies import get_commands, get_shared_state, verify_api_key
from src.api.schemas import (
    ActionRequest,
    ActionResponse,
    AgentContext,
    AgentInfo,
    AgentStatus,
    APIResponse,
)
from src.core.agent_commands import CommandQueue, CommandType
from src.core.agent_state import SharedStateManager
from src.core.defs import AgentAction


router = APIRouter()


@router.get("/status", response_model=APIResponse[AgentStatus])
async def get_agent_status(
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[AgentStatus]:
    """Get the current agent status.

    Returns agent state, personality, goal, and MCP connection status.
    """
    try:
        state = state_manager.get_state()
        is_alive = state_manager.is_agent_alive()

        agent_status = AgentStatus(
            state=state.agent_state if state.agent_state else "unknown",
            personality=state.personality if state.personality else "unknown",
            goal=state.goal if state.goal else "unknown",
            mcp_enabled=state.mcp_enabled,
            mcp_connected_servers=state.mcp_connected_servers,
            mcp_available_tools=state.mcp_available_tools,
            is_running=state.is_running and is_alive,
        )

        return APIResponse(
            success=True,
            data=agent_status,
            message="Agent status retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get agent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent status: {str(e)}",
        )


@router.get("/info", response_model=APIResponse[AgentInfo])
async def get_agent_info(
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[AgentInfo]:
    """Get detailed agent information.

    Returns full agent info including action history and statistics.
    """
    try:
        state = state_manager.get_state()
        recent_cycles = state_manager.get_recent_cycles()

        # Get available actions
        available_actions = [a.value for a in AgentAction]

        # Get last action from recent cycles
        last_action = None
        last_action_time = None
        if recent_cycles.cycles:
            last_cycle = recent_cycles.cycles[0]
            last_action = last_cycle.action
            if last_cycle.timestamp:
                try:
                    last_action_time = datetime.fromisoformat(
                        last_cycle.timestamp.replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

        agent_info = AgentInfo(
            personality=state.personality if state.personality else "unknown",
            goal=state.goal if state.goal else "unknown",
            state=state.agent_state if state.agent_state else "unknown",
            available_actions=available_actions,
            total_actions_executed=state.cycle_count,
            total_rewards=state.total_rewards,
            last_action=last_action,
            last_action_time=last_action_time,
        )

        return APIResponse(
            success=True,
            data=agent_info,
            message="Agent info retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get agent info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent info: {str(e)}",
        )


@router.get("/context", response_model=APIResponse[AgentContext])
async def get_agent_context(
    limit: int = 50,
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[AgentContext]:
    """Get the agent's context including action history.

    Args:
        limit: Maximum number of history items to return
    """
    try:
        state = state_manager.get_state()
        recent_cycles = state_manager.get_recent_cycles()

        # Convert cycles to history items
        from src.api.schemas import ActionHistoryItem

        history_items = []
        for cycle in recent_cycles.cycles[:limit]:
            try:
                timestamp = datetime.fromisoformat(cycle.timestamp.replace("Z", "+00:00"))
            except (ValueError, TypeError):
                timestamp = datetime.now(timezone.utc)

            item = ActionHistoryItem(
                timestamp=timestamp,
                action=cycle.action,
                state=cycle.state_before,
                outcome=cycle.outcome,
                reward=cycle.reward,
            )
            history_items.append(item)

        agent_context = AgentContext(
            actions_history=history_items,
            last_state=state.agent_state if state.agent_state else "unknown",
            total_actions=state.cycle_count,
            total_rewards=state.total_rewards,
        )

        return APIResponse(
            success=True,
            data=agent_context,
            message="Agent context retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get agent context: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent context: {str(e)}",
        )


@router.post("/start", response_model=APIResponse[Dict[str, Any]])
async def start_agent(
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Start the agent runtime loop.

    In decoupled mode, this checks if the agent is running.
    To start the agent, use 'make run-agent' in a separate terminal.
    """
    try:
        state = state_manager.get_state()
        is_alive = state_manager.is_agent_alive()

        if state.is_running and is_alive:
            return APIResponse(
                success=True,
                data={
                    "status": "already_running",
                    "pid": state.pid,
                },
                message="Agent is already running",
            )

        # In decoupled mode, we can't start the agent from the API
        return APIResponse(
            success=False,
            data={
                "status": "not_running",
                "instruction": "Run 'make run-agent' to start the agent process",
            },
            message="Agent not running. Start with 'make run-agent' in a separate terminal.",
        )
    except Exception as e:
        logger.error(f"Failed to start agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start agent: {str(e)}",
        )


@router.post("/stop", response_model=APIResponse[Dict[str, Any]])
async def stop_agent(
    state_manager: SharedStateManager = Depends(get_shared_state),
    commands: CommandQueue = Depends(get_commands),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Stop the agent runtime loop.

    Sends a stop command to the agent process.
    """
    try:
        state = state_manager.get_state()
        is_alive = state_manager.is_agent_alive()

        if not state.is_running or not is_alive:
            return APIResponse(
                success=True,
                data={"status": "already_stopped"},
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
                message="Agent stopped",
            )
        else:
            return APIResponse(
                success=True,
                data={
                    "status": "stop_requested",
                    "command_id": command.command_id,
                },
                message="Stop command sent to agent",
            )
    except Exception as e:
        logger.error(f"Failed to stop agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop agent: {str(e)}",
        )


@router.post("/action", response_model=APIResponse[ActionResponse])
async def execute_action(
    request: ActionRequest,
    state_manager: SharedStateManager = Depends(get_shared_state),
    commands: CommandQueue = Depends(get_commands),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[ActionResponse]:
    """Manually trigger an agent action.

    Args:
        request: Action request with action name and optional parameters
    """
    try:
        state = state_manager.get_state()
        is_alive = state_manager.is_agent_alive()

        if not state.is_running or not is_alive:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Agent not running",
            )

        # Validate action
        try:
            action = AgentAction(request.action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}. "
                f"Valid actions: {[a.value for a in AgentAction]}",
            )

        # Send execute action command
        command = commands.send_command(
            CommandType.EXECUTE_ACTION,
            params={"action": action.value},
            timeout_seconds=60.0,
        )
        logger.info(f"Sent execute action command: {command.command_id}")

        # Wait for the action to complete
        result = commands.wait_for_command(command.command_id, timeout_seconds=30.0)

        if result and result.status == "completed" and result.result:
            action_result = result.result
            action_response = ActionResponse(
                action=action.value,
                success=action_result.get("success", False),
                outcome=action_result.get("outcome"),
                reward=action_result.get("reward", 0.0),
                execution_time=0.0,  # Not tracked in command response
            )
        else:
            # Command still pending or failed
            error_msg = result.error if result else "Command timed out"
            action_response = ActionResponse(
                action=action.value,
                success=False,
                outcome=error_msg,
                reward=0.0,
                execution_time=0.0,
            )

        return APIResponse(
            success=action_response.success,
            data=action_response,
            message="Action executed" if action_response.success else "Action failed",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute action: {str(e)}",
        )


@router.get("/cycles", response_model=APIResponse[Dict[str, Any]])
async def get_recent_cycles(
    limit: int = 20,
    state_manager: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Get recent agent cycles from shared state.

    This provides quick access to recent cycles stored in shared state.
    For full cycle history, use the /api/v1/cycles endpoint.
    """
    try:
        recent_cycles = state_manager.get_recent_cycles()

        cycles_data = []
        for cycle in recent_cycles.cycles[:limit]:
            cycles_data.append(cycle.to_dict())

        return APIResponse(
            success=True,
            data={
                "cycles": cycles_data,
                "count": len(cycles_data),
            },
            message=f"Retrieved {len(cycles_data)} recent cycles",
        )
    except Exception as e:
        logger.error(f"Failed to get recent cycles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent cycles: {str(e)}",
        )
