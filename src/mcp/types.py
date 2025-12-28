"""Type definitions for MCP integration."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ToolDescription(BaseModel):
    """Description of an MCP tool for use in planning."""

    name: str = Field(..., description="Unique name of the tool")
    description: str = Field(default="", description="Human-readable description of the tool")
    input_schema: Dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for tool input parameters"
    )
    server_name: str = Field(..., description="Name of the MCP server providing this tool")

    def to_prompt_format(self) -> str:
        """Format tool description for use in LLM prompts."""
        params = []
        if "properties" in self.input_schema:
            for param_name, param_info in self.input_schema["properties"].items():
                param_type = param_info.get("type", "any")
                param_desc = param_info.get("description", "")
                required = param_name in self.input_schema.get("required", [])
                req_str = " (required)" if required else " (optional)"
                params.append(f"    - {param_name}: {param_type}{req_str} - {param_desc}")

        params_str = "\n".join(params) if params else "    (no parameters)"
        return f"- {self.name}: {self.description}\n  Parameters:\n{params_str}"


class ToolResult(BaseModel):
    """Result from executing an MCP tool."""

    success: bool = Field(..., description="Whether the tool execution succeeded")
    content: List[Dict[str, Any]] = Field(
        default_factory=list, description="Content returned by the tool"
    )
    structured_content: Optional[Dict[str, Any]] = Field(
        default=None, description="Structured content if available"
    )
    error: Optional[str] = Field(default=None, description="Error message if execution failed")
    is_error: bool = Field(default=False, description="Whether this result represents an error")

    def get_text_content(self) -> str:
        """Extract text content from the result."""
        texts = []
        for item in self.content:
            if item.get("type") == "text":
                texts.append(item.get("text", ""))
        return "\n".join(texts)

    def to_outcome_string(self) -> str:
        """Convert result to a string suitable for outcome logging."""
        if self.error:
            return f"Error: {self.error}"
        if self.structured_content:
            return str(self.structured_content)
        return self.get_text_content()


class MCPConnectionInfo(BaseModel):
    """Information about an MCP server connection."""

    server_name: str = Field(..., description="Name of the connected server")
    connected: bool = Field(default=False, description="Whether the connection is active")
    tools_count: int = Field(default=0, description="Number of tools available")
    error: Optional[str] = Field(default=None, description="Connection error if any")
