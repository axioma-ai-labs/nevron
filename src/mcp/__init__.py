"""MCP (Model Context Protocol) integration module.

This module provides MCP client functionality for connecting to MCP servers
and dynamically discovering and executing tools.
"""

from src.mcp.config import MCPServerConfig, MCPSettings
from src.mcp.manager import MCPToolManager
from src.mcp.types import ToolDescription, ToolResult


__all__ = [
    "MCPServerConfig",
    "MCPSettings",
    "MCPToolManager",
    "ToolDescription",
    "ToolResult",
]
