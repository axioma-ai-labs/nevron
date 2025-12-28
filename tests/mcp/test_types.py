"""Tests for MCP types."""

from src.mcp.types import MCPConnectionInfo, ToolDescription, ToolResult


class TestToolDescription:
    """Tests for ToolDescription."""

    def test_tool_description_creation(self):
        """Test creating a tool description."""
        tool = ToolDescription(
            name="test_tool",
            description="A test tool",
            input_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First parameter"},
                    "param2": {"type": "integer", "description": "Second parameter"},
                },
                "required": ["param1"],
            },
            server_name="test_server",
        )

        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.server_name == "test_server"
        assert "param1" in tool.input_schema["properties"]

    def test_tool_description_to_prompt_format(self):
        """Test formatting tool description for prompts."""
        tool = ToolDescription(
            name="fetch",
            description="Fetch a URL",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
            server_name="fetch_server",
        )

        prompt_format = tool.to_prompt_format()
        assert "fetch" in prompt_format
        assert "Fetch a URL" in prompt_format
        assert "url" in prompt_format
        assert "(required)" in prompt_format

    def test_tool_description_with_optional_params(self):
        """Test tool description with optional parameters."""
        tool = ToolDescription(
            name="search",
            description="Search for something",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Result limit"},
                },
                "required": ["query"],
            },
            server_name="search_server",
        )

        prompt_format = tool.to_prompt_format()
        assert "query" in prompt_format
        assert "(required)" in prompt_format
        assert "limit" in prompt_format
        assert "(optional)" in prompt_format

    def test_tool_description_empty_schema(self):
        """Test tool description with empty schema."""
        tool = ToolDescription(
            name="simple_tool",
            description="A simple tool with no params",
            input_schema={},
            server_name="server",
        )

        prompt_format = tool.to_prompt_format()
        assert "simple_tool" in prompt_format
        assert "(no parameters)" in prompt_format


class TestToolResult:
    """Tests for ToolResult."""

    def test_successful_result(self):
        """Test creating a successful result."""
        result = ToolResult(
            success=True,
            content=[{"type": "text", "text": "Hello, world!"}],
        )

        assert result.success is True
        assert result.is_error is False
        assert result.error is None

    def test_error_result(self):
        """Test creating an error result."""
        result = ToolResult(
            success=False,
            error="Something went wrong",
            is_error=True,
        )

        assert result.success is False
        assert result.is_error is True
        assert result.error == "Something went wrong"

    def test_get_text_content(self):
        """Test extracting text content."""
        result = ToolResult(
            success=True,
            content=[
                {"type": "text", "text": "Line 1"},
                {"type": "text", "text": "Line 2"},
                {"type": "image", "data": "base64..."},
            ],
        )

        text = result.get_text_content()
        assert "Line 1" in text
        assert "Line 2" in text
        assert "base64" not in text

    def test_to_outcome_string_success(self):
        """Test converting successful result to outcome string."""
        result = ToolResult(
            success=True,
            content=[{"type": "text", "text": "Result text"}],
        )

        outcome = result.to_outcome_string()
        assert "Result text" in outcome

    def test_to_outcome_string_error(self):
        """Test converting error result to outcome string."""
        result = ToolResult(
            success=False,
            error="Error message",
            is_error=True,
        )

        outcome = result.to_outcome_string()
        assert "Error:" in outcome
        assert "Error message" in outcome

    def test_to_outcome_string_structured(self):
        """Test converting structured result to outcome string."""
        result = ToolResult(
            success=True,
            content=[],
            structured_content={"key": "value", "count": 42},
        )

        outcome = result.to_outcome_string()
        assert "key" in outcome
        assert "value" in outcome


class TestMCPConnectionInfo:
    """Tests for MCPConnectionInfo."""

    def test_connection_info_creation(self):
        """Test creating connection info."""
        info = MCPConnectionInfo(
            server_name="test_server",
            connected=True,
            tools_count=5,
        )

        assert info.server_name == "test_server"
        assert info.connected is True
        assert info.tools_count == 5
        assert info.error is None

    def test_connection_info_with_error(self):
        """Test connection info with error."""
        info = MCPConnectionInfo(
            server_name="failed_server",
            connected=False,
            tools_count=0,
            error="Connection refused",
        )

        assert info.connected is False
        assert info.error == "Connection refused"
