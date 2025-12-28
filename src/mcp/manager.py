"""MCP Tool Manager for managing MCP server connections and tool execution."""

import asyncio
import os
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from src.mcp.config import MCPServerConfig, MCPSettings, MCPTransportType
from src.mcp.types import MCPConnectionInfo, ToolDescription, ToolResult


class MCPServerConnection:
    """Manages a single MCP server connection."""

    def __init__(self, config: MCPServerConfig):
        """Initialize the server connection.

        Args:
            config: Server configuration
        """
        self.config = config
        self.session: Optional[ClientSession] = None
        self._connected = False
        self._tools: List[ToolDescription] = []
        self._context_manager: Optional[Any] = None
        self._session_context: Optional[Any] = None

    @property
    def connected(self) -> bool:
        """Check if the server is connected."""
        return self._connected and self.session is not None

    @property
    def tools(self) -> List[ToolDescription]:
        """Get list of available tools."""
        return self._tools

    async def connect(self) -> bool:
        """Connect to the MCP server and discover tools.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.config.transport == MCPTransportType.STDIO:
                return await self._connect_stdio()
            elif self.config.transport == MCPTransportType.HTTP:
                return await self._connect_http()
            else:
                logger.error(f"Unsupported transport type: {self.config.transport}")
                return False
        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{self.config.name}': {e}")
            return False

    async def _connect_stdio(self) -> bool:
        """Connect using STDIO transport."""
        if not self.config.command:
            logger.error(f"No command specified for STDIO server '{self.config.name}'")
            return False

        # Build environment with expanded variables
        env = dict(os.environ)
        env.update(self.config.env)

        server_params = StdioServerParameters(
            command=self.config.command,
            args=self.config.args,
            env=env,
        )

        try:
            # Create the stdio client context manager
            self._context_manager = stdio_client(server_params)
            read, write = await self._context_manager.__aenter__()

            # Create and initialize the session
            self._session_context = ClientSession(read, write)
            self.session = await self._session_context.__aenter__()
            await self.session.initialize()

            # Discover available tools
            await self._discover_tools()

            self._connected = True
            logger.info(
                f"Connected to MCP server '{self.config.name}' "
                f"with {len(self._tools)} tools available"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to connect via STDIO to '{self.config.name}': {e}")
            await self.disconnect()
            return False

    async def _connect_http(self) -> bool:
        """Connect using HTTP transport."""
        # HTTP transport requires the streamablehttp_client
        # This is a simplified implementation - full HTTP support would need more work
        logger.warning(f"HTTP transport not fully implemented for '{self.config.name}'")
        return False

    async def _discover_tools(self) -> None:
        """Discover available tools from the connected server."""
        if not self.session:
            return

        try:
            tools_result = await self.session.list_tools()
            self._tools = []

            for tool in tools_result.tools:
                tool_desc = ToolDescription(
                    name=tool.name,
                    description=tool.description or "",
                    input_schema=tool.inputSchema if hasattr(tool, "inputSchema") else {},
                    server_name=self.config.name,
                )
                self._tools.append(tool_desc)

            logger.debug(
                f"Discovered {len(self._tools)} tools from '{self.config.name}': "
                f"{[t.name for t in self._tools]}"
            )

        except Exception as e:
            logger.error(f"Failed to discover tools from '{self.config.name}': {e}")

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Call a tool on this server.

        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            ToolResult with execution result
        """
        if not self.session:
            return ToolResult(
                success=False,
                error=f"Not connected to server '{self.config.name}'",
                is_error=True,
            )

        try:
            result = await self.session.call_tool(tool_name, arguments)

            # Convert MCP result to our ToolResult format
            content = []
            for item in result.content:
                if hasattr(item, "type") and hasattr(item, "text"):
                    content.append({"type": item.type, "text": item.text})
                elif hasattr(item, "type"):
                    content.append({"type": item.type, "data": str(item)})

            return ToolResult(
                success=not getattr(result, "isError", False),
                content=content,
                structured_content=getattr(result, "structuredContent", None),
                is_error=getattr(result, "isError", False),
            )

        except Exception as e:
            logger.error(f"Failed to call tool '{tool_name}' on '{self.config.name}': {e}")
            return ToolResult(
                success=False,
                error=str(e),
                is_error=True,
            )

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
            if self._context_manager:
                await self._context_manager.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"Error during disconnect from '{self.config.name}': {e}")
        finally:
            self.session = None
            self._session_context = None
            self._context_manager = None
            self._connected = False
            self._tools = []
            logger.info(f"Disconnected from MCP server '{self.config.name}'")

    def get_connection_info(self) -> MCPConnectionInfo:
        """Get information about this connection."""
        return MCPConnectionInfo(
            server_name=self.config.name,
            connected=self.connected,
            tools_count=len(self._tools),
        )


class MCPToolManager:
    """
    Manages MCP server connections and tool execution.
    Provides dynamic tool discovery and unified tool execution interface.
    """

    def __init__(self, settings: Optional[MCPSettings] = None):
        """Initialize the MCP Tool Manager.

        Args:
            settings: MCP settings configuration. If None, creates with defaults.
        """
        self.settings = settings or MCPSettings()
        self._connections: Dict[str, MCPServerConnection] = {}
        self._tool_index: Dict[str, Tuple[str, ToolDescription]] = {}  # tool_name -> (server, desc)
        self._initialized = False

    @property
    def connected_servers(self) -> List[str]:
        """Get list of connected server names."""
        return [name for name, conn in self._connections.items() if conn.connected]

    @property
    def available_tools(self) -> List[ToolDescription]:
        """Get all available tools across all connected servers."""
        return [desc for _, desc in self._tool_index.values()]

    async def initialize(self) -> None:
        """Initialize the manager and connect to configured servers."""
        if self._initialized:
            logger.warning("MCPToolManager already initialized")
            return

        if not self.settings.enabled:
            logger.info("MCP integration is disabled")
            self._initialized = True
            return

        # Connect to all enabled servers
        enabled_servers = self.settings.get_enabled_servers()
        if not enabled_servers:
            logger.info("No MCP servers configured")
            self._initialized = True
            return

        logger.info(f"Initializing MCP connections to {len(enabled_servers)} servers...")

        # Connect to servers concurrently
        connection_tasks = []
        for server_config in enabled_servers:
            connection = MCPServerConnection(server_config)
            self._connections[server_config.name] = connection
            connection_tasks.append(self._connect_server(connection))

        await asyncio.gather(*connection_tasks, return_exceptions=True)

        # Build tool index
        self._rebuild_tool_index()

        self._initialized = True
        logger.info(
            f"MCP initialization complete: "
            f"{len(self.connected_servers)} servers connected, "
            f"{len(self._tool_index)} tools available"
        )

    async def _connect_server(self, connection: MCPServerConnection) -> bool:
        """Connect to a single server with retry logic.

        Args:
            connection: Server connection to establish

        Returns:
            True if connected successfully
        """
        max_attempts = (
            self.settings.max_reconnect_attempts if self.settings.reconnect_on_failure else 1
        )

        for attempt in range(max_attempts):
            try:
                if await connection.connect():
                    return True
                if attempt < max_attempts - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.info(
                        f"Retrying connection to '{connection.config.name}' "
                        f"in {wait_time}s (attempt {attempt + 2}/{max_attempts})"
                    )
                    await asyncio.sleep(wait_time)
            except Exception as e:
                logger.error(
                    f"Connection attempt {attempt + 1} failed for '{connection.config.name}': {e}"
                )

        return False

    def _rebuild_tool_index(self) -> None:
        """Rebuild the tool index from all connected servers."""
        self._tool_index.clear()

        for server_name, connection in self._connections.items():
            if not connection.connected:
                continue

            for tool in connection.tools:
                if tool.name in self._tool_index:
                    logger.warning(
                        f"Duplicate tool name '{tool.name}' from server '{server_name}', "
                        f"using tool from '{self._tool_index[tool.name][0]}'"
                    )
                    continue
                self._tool_index[tool.name] = (server_name, tool)

    def get_tool_descriptions(self) -> List[ToolDescription]:
        """Get descriptions of all available tools for planning.

        Returns:
            List of tool descriptions
        """
        return self.available_tools

    def get_tool_descriptions_for_prompt(self) -> str:
        """Get formatted tool descriptions for use in LLM prompts.

        Returns:
            Formatted string of tool descriptions
        """
        if not self._tool_index:
            return "No MCP tools available."

        tools_text = []
        for tool in self.available_tools:
            tools_text.append(tool.to_prompt_format())

        return "\n\n".join(tools_text)

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool is available.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is available
        """
        return tool_name in self._tool_index

    def get_tool(self, tool_name: str) -> Optional[ToolDescription]:
        """Get a tool description by name.

        Args:
            tool_name: Name of the tool

        Returns:
            Tool description or None if not found
        """
        if tool_name in self._tool_index:
            return self._tool_index[tool_name][1]
        return None

    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name.

        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments

        Returns:
            ToolResult with execution outcome
        """
        if not self._initialized:
            return ToolResult(
                success=False,
                error="MCPToolManager not initialized",
                is_error=True,
            )

        if tool_name not in self._tool_index:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found",
                is_error=True,
            )

        server_name, _ = self._tool_index[tool_name]
        connection = self._connections.get(server_name)

        if not connection or not connection.connected:
            return ToolResult(
                success=False,
                error=f"Server '{server_name}' not connected",
                is_error=True,
            )

        logger.debug(f"Executing MCP tool '{tool_name}' on server '{server_name}'")
        result = await connection.call_tool(tool_name, arguments)

        if result.success:
            logger.info(f"Tool '{tool_name}' executed successfully")
        else:
            logger.warning(f"Tool '{tool_name}' execution failed: {result.error}")

        return result

    def get_connection_status(self) -> List[MCPConnectionInfo]:
        """Get connection status for all configured servers.

        Returns:
            List of connection info for each server
        """
        return [conn.get_connection_info() for conn in self._connections.values()]

    async def reconnect_server(self, server_name: str) -> bool:
        """Attempt to reconnect to a specific server.

        Args:
            server_name: Name of the server to reconnect

        Returns:
            True if reconnection successful
        """
        connection = self._connections.get(server_name)
        if not connection:
            logger.error(f"Unknown server: {server_name}")
            return False

        if connection.connected:
            await connection.disconnect()

        success = await self._connect_server(connection)
        if success:
            self._rebuild_tool_index()

        return success

    async def shutdown(self) -> None:
        """Shutdown all connections and cleanup."""
        logger.info("Shutting down MCP Tool Manager...")

        disconnect_tasks = []
        for connection in self._connections.values():
            disconnect_tasks.append(connection.disconnect())

        await asyncio.gather(*disconnect_tasks, return_exceptions=True)

        self._connections.clear()
        self._tool_index.clear()
        self._initialized = False

        logger.info("MCP Tool Manager shutdown complete")

    async def __aenter__(self) -> "MCPToolManager":
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.shutdown()
