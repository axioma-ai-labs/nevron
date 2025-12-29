"""MCP router - endpoints for MCP server and tool management."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from pydantic import BaseModel, Field

from src.api.dependencies import get_shared_state, verify_api_key
from src.api.schemas import APIResponse
from src.core.agent_state import SharedStateManager


router = APIRouter()


# MCP-specific schemas
class MCPServerStatus(BaseModel):
    """Status of an MCP server."""

    name: str
    connected: bool
    tools_count: int
    transport: str = "stdio"


class MCPToolInfo(BaseModel):
    """Information about an MCP tool."""

    name: str
    description: str
    server: str
    input_schema: Dict[str, Any] = Field(default_factory=dict)


class MCPStatus(BaseModel):
    """Overall MCP status."""

    enabled: bool
    initialized: bool
    connected_servers: List[str]
    total_tools: int
    servers: List[MCPServerStatus]


class ToolExecuteRequest(BaseModel):
    """Request to execute a tool."""

    arguments: Dict[str, Any] = Field(default_factory=dict)


class ToolExecuteResponse(BaseModel):
    """Response from tool execution."""

    tool: str
    success: bool
    content: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    execution_time: float = 0.0


def _get_mcp_manager(state: SharedStateManager) -> Optional[Any]:
    """Get MCP manager from agent if available.

    Args:
        state: The shared state manager

    Returns:
        MCPToolManager or None
    """
    try:
        from src.agent import Agent

        agent = Agent()
        if hasattr(agent, "mcp_manager") and agent.mcp_manager:
            return agent.mcp_manager
    except Exception as e:
        logger.debug(f"Could not get MCP manager: {e}")

    return None


@router.get("/status", response_model=APIResponse[MCPStatus])
async def get_mcp_status(
    state: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[MCPStatus]:
    """Get MCP connection status.

    Returns overall MCP status including connected servers and available tools.
    """
    try:
        mcp_manager = _get_mcp_manager(state)

        if not mcp_manager:
            mcp_status = MCPStatus(
                enabled=False,
                initialized=False,
                connected_servers=[],
                total_tools=0,
                servers=[],
            )
        else:
            # Get connection info for all servers
            connection_info = mcp_manager.get_connection_status()

            servers = [
                MCPServerStatus(
                    name=info.server_name,
                    connected=info.connected,
                    tools_count=info.tools_count,
                )
                for info in connection_info
            ]

            mcp_status = MCPStatus(
                enabled=True,
                initialized=True,
                connected_servers=mcp_manager.connected_servers,
                total_tools=len(mcp_manager.available_tools),
                servers=servers,
            )

        return APIResponse(
            success=True,
            data=mcp_status,
            message="MCP status retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get MCP status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get MCP status: {str(e)}",
        )


@router.get("/servers", response_model=APIResponse[List[MCPServerStatus]])
async def get_mcp_servers(
    state: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[MCPServerStatus]]:
    """Get list of MCP servers with their status.

    Returns connection status and tool count for each configured server.
    """
    try:
        mcp_manager = _get_mcp_manager(state)

        if not mcp_manager:
            return APIResponse(
                success=True,
                data=[],
                message="MCP not initialized",
            )

        connection_info = mcp_manager.get_connection_status()

        servers = [
            MCPServerStatus(
                name=info.server_name,
                connected=info.connected,
                tools_count=info.tools_count,
            )
            for info in connection_info
        ]

        return APIResponse(
            success=True,
            data=servers,
            message=f"Retrieved {len(servers)} MCP servers",
        )
    except Exception as e:
        logger.error(f"Failed to get MCP servers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get MCP servers: {str(e)}",
        )


@router.get("/tools", response_model=APIResponse[List[MCPToolInfo]])
async def get_mcp_tools(
    server: Optional[str] = Query(default=None, description="Filter by server name"),
    state: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[MCPToolInfo]]:
    """Get list of available MCP tools.

    Args:
        server: Optional filter by server name
    """
    try:
        mcp_manager = _get_mcp_manager(state)

        if not mcp_manager:
            return APIResponse(
                success=True,
                data=[],
                message="MCP not initialized",
            )

        all_tools = mcp_manager.get_tool_descriptions()

        # Filter by server if specified
        if server:
            all_tools = [t for t in all_tools if t.server_name == server]

        tools = [
            MCPToolInfo(
                name=tool.name,
                description=tool.description,
                server=tool.server_name,
                input_schema=tool.input_schema or {},
            )
            for tool in all_tools
        ]

        return APIResponse(
            success=True,
            data=tools,
            message=f"Retrieved {len(tools)} MCP tools",
        )
    except Exception as e:
        logger.error(f"Failed to get MCP tools: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get MCP tools: {str(e)}",
        )


@router.get("/tools/{tool_name}", response_model=APIResponse[MCPToolInfo])
async def get_tool_info(
    tool_name: str,
    state: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[MCPToolInfo]:
    """Get information about a specific MCP tool.

    Args:
        tool_name: Name of the tool
    """
    try:
        mcp_manager = _get_mcp_manager(state)

        if not mcp_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MCP not initialized",
            )

        tool = mcp_manager.get_tool(tool_name)

        if not tool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {tool_name}",
            )

        tool_info = MCPToolInfo(
            name=tool.name,
            description=tool.description,
            server=tool.server_name,
            input_schema=tool.input_schema or {},
        )

        return APIResponse(
            success=True,
            data=tool_info,
            message=f"Tool info retrieved: {tool_name}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get tool info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tool info: {str(e)}",
        )


@router.post("/servers/{server_name}/reconnect", response_model=APIResponse[Dict[str, Any]])
async def reconnect_server(
    server_name: str,
    state: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Reconnect to an MCP server.

    Args:
        server_name: Name of the server to reconnect
    """
    try:
        mcp_manager = _get_mcp_manager(state)

        if not mcp_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MCP not initialized",
            )

        success = await mcp_manager.reconnect_server(server_name)

        if not success:
            return APIResponse(
                success=False,
                data={"server": server_name, "reconnected": False},
                message=f"Failed to reconnect to server: {server_name}",
            )

        # Get updated status
        connection_info = [
            info for info in mcp_manager.get_connection_status() if info.server_name == server_name
        ]

        tools_count = connection_info[0].tools_count if connection_info else 0

        return APIResponse(
            success=True,
            data={
                "server": server_name,
                "reconnected": True,
                "tools_discovered": tools_count,
            },
            message=f"Reconnected to server: {server_name}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reconnect to server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reconnect to server: {str(e)}",
        )


@router.post("/tools/{tool_name}/execute", response_model=APIResponse[ToolExecuteResponse])
async def execute_tool(
    tool_name: str,
    request: ToolExecuteRequest,
    state: SharedStateManager = Depends(get_shared_state),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[ToolExecuteResponse]:
    """Execute an MCP tool.

    Args:
        tool_name: Name of the tool to execute
        request: Tool arguments
    """
    import time

    try:
        mcp_manager = _get_mcp_manager(state)

        if not mcp_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MCP not initialized",
            )

        if not mcp_manager.has_tool(tool_name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tool not found: {tool_name}",
            )

        start_time = time.time()
        result = await mcp_manager.execute_tool(tool_name, request.arguments)
        execution_time = time.time() - start_time

        response = ToolExecuteResponse(
            tool=tool_name,
            success=result.success,
            content=result.content or [],
            error=result.error,
            execution_time=execution_time,
        )

        return APIResponse(
            success=result.success,
            data=response,
            message=f"Tool {'executed successfully' if result.success else 'execution failed'}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute tool: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute tool: {str(e)}",
        )
