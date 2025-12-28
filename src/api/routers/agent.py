"""Agent control router - endpoints for managing the AI agent."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from src.api.dependencies import get_runtime, verify_api_key
from src.api.schemas import (
    ActionRequest,
    ActionResponse,
    AgentContext,
    AgentInfo,
    AgentStatus,
    APIResponse,
)
from src.runtime.runtime import AutonomousRuntime


router = APIRouter()


def _get_agent_from_runtime(runtime: AutonomousRuntime) -> Optional[Any]:
    """Get the agent instance from the runtime if available.

    Args:
        runtime: The autonomous runtime instance

    Returns:
        Agent instance or None
    """
    # The agent may be registered as a handler or stored in the runtime
    # For now, we'll try to access it via the processor's handlers
    try:
        from src.agent import Agent

        # Create a temporary agent instance for status queries
        # In production, this would be the actual running agent
        return Agent()
    except Exception as e:
        logger.warning(f"Could not get agent instance: {e}")
        return None


@router.get("/status", response_model=APIResponse[AgentStatus])
async def get_agent_status(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[AgentStatus]:
    """Get the current agent status.

    Returns agent state, personality, goal, and MCP connection status.
    """
    try:
        agent = _get_agent_from_runtime(runtime)

        if agent:
            mcp_status = agent.get_mcp_status()
            agent_status = AgentStatus(
                state=agent.state.value,
                personality=agent.personality,
                goal=agent.goal,
                mcp_enabled=mcp_status.get("enabled", False),
                mcp_connected_servers=len(mcp_status.get("connected_servers", [])),
                mcp_available_tools=mcp_status.get("available_tools", 0),
                is_running=runtime.is_running,
            )
        else:
            # Return default status when agent is not available
            agent_status = AgentStatus(
                state="unknown",
                personality="unknown",
                goal="unknown",
                mcp_enabled=False,
                mcp_connected_servers=0,
                mcp_available_tools=0,
                is_running=runtime.is_running,
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
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[AgentInfo]:
    """Get detailed agent information.

    Returns full agent info including action history and statistics.
    """
    try:
        agent = _get_agent_from_runtime(runtime)

        if agent:
            # Get context with action history
            context = agent.context_manager.get_context()
            actions_history = context.actions_history

            # Calculate totals
            total_actions = len(actions_history)
            total_rewards = sum(h.get("reward", 0) for h in actions_history if h.get("reward"))

            # Get available actions
            from src.core.defs import AgentAction

            available_actions = [a.value for a in AgentAction]

            # Get last action
            last_action = None
            last_action_time = None
            if actions_history:
                last = actions_history[-1]
                last_action = last.get("action")
                if last.get("timestamp"):
                    last_action_time = datetime.fromisoformat(last["timestamp"])

            agent_info = AgentInfo(
                personality=agent.personality,
                goal=agent.goal,
                state=agent.state.value,
                available_actions=available_actions,
                total_actions_executed=total_actions,
                total_rewards=total_rewards,
                last_action=last_action,
                last_action_time=last_action_time,
            )
        else:
            from src.core.defs import AgentAction

            agent_info = AgentInfo(
                personality="unknown",
                goal="unknown",
                state="unknown",
                available_actions=[a.value for a in AgentAction],
                total_actions_executed=0,
                total_rewards=0.0,
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
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[AgentContext]:
    """Get the agent's context including action history.

    Args:
        limit: Maximum number of history items to return
    """
    try:
        agent = _get_agent_from_runtime(runtime)

        if agent:
            context = agent.context_manager.get_context()
            actions_history = context.actions_history[-limit:]

            # Convert to schema format
            from src.api.schemas import ActionHistoryItem

            history_items = []
            for h in actions_history:
                item = ActionHistoryItem(
                    timestamp=(
                        datetime.fromisoformat(h["timestamp"])
                        if h.get("timestamp")
                        else datetime.now(timezone.utc)
                    ),
                    action=h.get("action", "unknown"),
                    state=h.get("state", "unknown"),
                    outcome=h.get("outcome"),
                    reward=h.get("reward"),
                )
                history_items.append(item)

            total_rewards = sum(h.get("reward", 0) for h in actions_history if h.get("reward"))

            agent_context = AgentContext(
                actions_history=history_items,
                last_state=context.last_state.value if context.last_state else "unknown",
                total_actions=len(context.actions_history),
                total_rewards=total_rewards,
            )
        else:
            agent_context = AgentContext(
                actions_history=[],
                last_state="unknown",
                total_actions=0,
                total_rewards=0.0,
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
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Start the agent runtime loop.

    Starts the autonomous runtime if not already running.
    """
    try:
        if runtime.is_running:
            return APIResponse(
                success=True,
                data={"status": "already_running"},
                message="Agent is already running",
            )

        await runtime.start()
        logger.info("Agent runtime started via API")

        return APIResponse(
            success=True,
            data={"status": "started"},
            message="Agent runtime started",
        )
    except Exception as e:
        logger.error(f"Failed to start agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start agent: {str(e)}",
        )


@router.post("/stop", response_model=APIResponse[Dict[str, Any]])
async def stop_agent(
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Stop the agent runtime loop.

    Gracefully stops the autonomous runtime.
    """
    try:
        if not runtime.is_running:
            return APIResponse(
                success=True,
                data={"status": "already_stopped"},
                message="Agent is already stopped",
            )

        await runtime.stop()
        logger.info("Agent runtime stopped via API")

        return APIResponse(
            success=True,
            data={"status": "stopped"},
            message="Agent runtime stopped",
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
    runtime: AutonomousRuntime = Depends(get_runtime),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[ActionResponse]:
    """Manually trigger an agent action.

    Args:
        request: Action request with action name and optional parameters
    """
    import time

    try:
        agent = _get_agent_from_runtime(runtime)

        if not agent:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Agent not available",
            )

        # Validate action
        from src.core.defs import AgentAction

        try:
            action = AgentAction(request.action)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}. "
                f"Valid actions: {[a.value for a in AgentAction]}",
            )

        # Execute the action
        start_time = time.time()
        success, outcome = await agent.execution_module.execute_action(action)
        execution_time = time.time() - start_time

        # Collect feedback
        reward = agent._collect_feedback(action.value, outcome)

        # Update context
        agent.context_manager.add_action(
            action=action,
            state=agent.state,
            outcome=str(outcome) if outcome else None,
            reward=reward,
        )
        agent._update_state(action)

        action_response = ActionResponse(
            action=action.value,
            success=success,
            outcome=str(outcome) if outcome else None,
            reward=reward,
            execution_time=execution_time,
        )

        return APIResponse(
            success=True,
            data=action_response,
            message="Action executed",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute action: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute action: {str(e)}",
        )
