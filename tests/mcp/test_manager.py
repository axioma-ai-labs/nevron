"""Tests for MCP Tool Manager."""

import pytest

from src.mcp.config import MCPServerConfig, MCPSettings, MCPTransportType
from src.mcp.manager import MCPServerConnection, MCPToolManager
from src.mcp.types import ToolDescription


class TestMCPServerConnection:
    """Tests for MCPServerConnection."""

    def test_connection_initialization(self):
        """Test connection initialization."""
        config = MCPServerConfig(
            name="test_server",
            transport=MCPTransportType.STDIO,
            command="test_cmd",
        )
        connection = MCPServerConnection(config)

        assert connection.config == config
        assert connection.connected is False
        assert connection.tools == []

    def test_connection_info(self):
        """Test getting connection info."""
        config = MCPServerConfig(
            name="test_server",
            transport=MCPTransportType.STDIO,
            command="test_cmd",
        )
        connection = MCPServerConnection(config)

        info = connection.get_connection_info()
        assert info.server_name == "test_server"
        assert info.connected is False
        assert info.tools_count == 0

    @pytest.mark.asyncio
    async def test_disconnect_when_not_connected(self):
        """Test disconnect when not connected."""
        config = MCPServerConfig(
            name="test_server",
            transport=MCPTransportType.STDIO,
            command="test_cmd",
        )
        connection = MCPServerConnection(config)

        # Should not raise
        await connection.disconnect()
        assert connection.connected is False

    @pytest.mark.asyncio
    async def test_call_tool_when_not_connected(self):
        """Test calling tool when not connected."""
        config = MCPServerConfig(
            name="test_server",
            transport=MCPTransportType.STDIO,
            command="test_cmd",
        )
        connection = MCPServerConnection(config)

        result = await connection.call_tool("some_tool", {"arg": "value"})

        assert result.success is False
        assert result.is_error is True
        assert result.error is not None
        assert "Not connected" in result.error


class TestMCPToolManager:
    """Tests for MCPToolManager."""

    def test_manager_initialization(self):
        """Test manager initialization."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)

        assert manager.settings == settings
        assert manager.connected_servers == []
        assert manager.available_tools == []

    def test_manager_disabled(self):
        """Test manager with MCP disabled."""
        settings = MCPSettings(enabled=False)
        manager = MCPToolManager(settings)

        assert manager.settings.enabled is False

    @pytest.mark.asyncio
    async def test_initialize_with_no_servers(self):
        """Test initialization with no servers configured."""
        settings = MCPSettings(enabled=True, servers=[])
        manager = MCPToolManager(settings)

        await manager.initialize()

        assert manager.connected_servers == []
        assert manager.available_tools == []

    @pytest.mark.asyncio
    async def test_initialize_when_disabled(self):
        """Test initialization when disabled."""
        settings = MCPSettings(enabled=False)
        manager = MCPToolManager(settings)

        await manager.initialize()

        # Should still be empty but initialized
        assert manager.connected_servers == []

    def test_has_tool_not_found(self):
        """Test checking for non-existent tool."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)

        assert manager.has_tool("nonexistent_tool") is False

    def test_get_tool_not_found(self):
        """Test getting non-existent tool."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)

        assert manager.get_tool("nonexistent_tool") is None

    @pytest.mark.asyncio
    async def test_execute_tool_not_initialized(self):
        """Test executing tool when not initialized."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)

        result = await manager.execute_tool("some_tool", {})

        assert result.success is False
        assert result.error is not None
        assert "not initialized" in result.error

    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """Test executing non-existent tool."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)
        await manager.initialize()

        result = await manager.execute_tool("nonexistent", {})

        assert result.success is False
        assert result.error is not None
        assert "not found" in result.error

    def test_get_tool_descriptions_empty(self):
        """Test getting tool descriptions when empty."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)

        descriptions = manager.get_tool_descriptions()
        assert descriptions == []

    def test_get_tool_descriptions_for_prompt_empty(self):
        """Test getting formatted tool descriptions when empty."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)

        prompt = manager.get_tool_descriptions_for_prompt()
        assert "No MCP tools available" in prompt

    def test_connection_status_empty(self):
        """Test connection status with no servers."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)

        status = manager.get_connection_status()
        assert status == []

    @pytest.mark.asyncio
    async def test_reconnect_unknown_server(self):
        """Test reconnecting to unknown server."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)
        await manager.initialize()

        result = await manager.reconnect_server("unknown_server")
        assert result is False

    @pytest.mark.asyncio
    async def test_shutdown_when_empty(self):
        """Test shutdown with no connections."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)
        await manager.initialize()

        # Should not raise
        await manager.shutdown()

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test using manager as context manager."""
        settings = MCPSettings(enabled=True)

        async with MCPToolManager(settings) as manager:
            assert manager is not None

        # After exit, should be clean
        assert manager.connected_servers == []


class TestMCPToolManagerWithMocks:
    """Tests for MCPToolManager with mocked connections."""

    @pytest.mark.asyncio
    async def test_tool_index_building(self):
        """Test that tool index is built correctly."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)

        # Manually add tools to simulate connected servers
        manager._tool_index = {
            "tool1": (
                "server1",
                ToolDescription(
                    name="tool1",
                    description="Tool 1",
                    input_schema={},
                    server_name="server1",
                ),
            ),
            "tool2": (
                "server2",
                ToolDescription(
                    name="tool2",
                    description="Tool 2",
                    input_schema={},
                    server_name="server2",
                ),
            ),
        }
        manager._initialized = True

        assert manager.has_tool("tool1")
        assert manager.has_tool("tool2")
        assert not manager.has_tool("tool3")

        tool1 = manager.get_tool("tool1")
        assert tool1 is not None
        assert tool1.name == "tool1"

    @pytest.mark.asyncio
    async def test_available_tools_property(self):
        """Test available_tools property."""
        settings = MCPSettings(enabled=True)
        manager = MCPToolManager(settings)

        tool1 = ToolDescription(
            name="tool1",
            description="Tool 1",
            input_schema={},
            server_name="server1",
        )
        tool2 = ToolDescription(
            name="tool2",
            description="Tool 2",
            input_schema={},
            server_name="server2",
        )

        manager._tool_index = {
            "tool1": ("server1", tool1),
            "tool2": ("server2", tool2),
        }

        tools = manager.available_tools
        assert len(tools) == 2
        assert tool1 in tools
        assert tool2 in tools
