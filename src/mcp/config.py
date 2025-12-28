"""Configuration for MCP servers and connections."""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator


class MCPTransportType(str, Enum):
    """Transport type for MCP server connections."""

    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


class MCPServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    name: str = Field(..., description="Unique name for this server configuration")
    transport: MCPTransportType = Field(
        default=MCPTransportType.STDIO, description="Transport type for connection"
    )

    # For STDIO transport
    command: Optional[str] = Field(default=None, description="Command to start the server")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(
        default_factory=dict, description="Environment variables for the server process"
    )

    # For HTTP/SSE transport
    url: Optional[str] = Field(default=None, description="Server URL for HTTP/SSE transport")

    # Common settings
    enabled: bool = Field(default=True, description="Whether this server is enabled")
    timeout: float = Field(default=30.0, description="Connection timeout in seconds")

    @field_validator("env", mode="before")
    @classmethod
    def expand_env_vars(cls, v: Dict[str, str]) -> Dict[str, str]:
        """Expand environment variables in env dict values."""
        if not v:
            return {}
        expanded = {}
        for key, value in v.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                expanded[key] = os.environ.get(env_var, "")
            else:
                expanded[key] = value
        return expanded

    def model_post_init(self, __context: Any) -> None:
        """Validate configuration after initialization."""
        if self.transport == MCPTransportType.STDIO and not self.command:
            raise ValueError(f"STDIO transport requires 'command' for server '{self.name}'")
        if self.transport in (MCPTransportType.HTTP, MCPTransportType.SSE) and not self.url:
            raise ValueError(
                f"{self.transport.value} transport requires 'url' for server '{self.name}'"
            )


class MCPSettings(BaseModel):
    """Settings for MCP integration."""

    enabled: bool = Field(default=True, description="Whether MCP integration is enabled")
    servers: List[MCPServerConfig] = Field(
        default_factory=list, description="List of MCP server configurations"
    )
    config_file: Optional[str] = Field(
        default=None, description="Path to MCP servers configuration file"
    )
    auto_connect: bool = Field(
        default=True, description="Automatically connect to servers on startup"
    )
    reconnect_on_failure: bool = Field(
        default=True, description="Attempt to reconnect on connection failure"
    )
    max_reconnect_attempts: int = Field(default=3, description="Maximum reconnection attempts")

    @classmethod
    def from_yaml(cls, config_path: Union[str, Path]) -> "MCPSettings":
        """Load MCP settings from a YAML configuration file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            MCPSettings instance
        """
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"MCP config file not found: {config_path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f)

        if not data:
            return cls()

        # Parse servers from YAML
        servers = []
        for server_data in data.get("servers", []):
            servers.append(MCPServerConfig(**server_data))

        return cls(
            enabled=data.get("enabled", True),
            servers=servers,
            config_file=str(config_path),
            auto_connect=data.get("auto_connect", True),
            reconnect_on_failure=data.get("reconnect_on_failure", True),
            max_reconnect_attempts=data.get("max_reconnect_attempts", 3),
        )

    def get_enabled_servers(self) -> List[MCPServerConfig]:
        """Get list of enabled server configurations."""
        return [s for s in self.servers if s.enabled]


# Example configuration for common MCP servers
EXAMPLE_MCP_CONFIG = """
# MCP Servers Configuration
# Place this file at mcp_servers.yaml in your project root

enabled: true
auto_connect: true
reconnect_on_failure: true
max_reconnect_attempts: 3

servers:
  # Filesystem server for file operations
  - name: filesystem
    transport: stdio
    command: npx
    args:
      - "@modelcontextprotocol/server-filesystem"
      - "/workspace"
    enabled: true

  # GitHub server for repository operations
  - name: github
    transport: stdio
    command: npx
    args:
      - "@modelcontextprotocol/server-github"
    env:
      GITHUB_TOKEN: "${GITHUB_TOKEN}"
    enabled: true

  # Fetch server for HTTP requests
  - name: fetch
    transport: stdio
    command: npx
    args:
      - "@modelcontextprotocol/server-fetch"
    enabled: true

  # Memory server for persistent storage
  - name: memory
    transport: stdio
    command: npx
    args:
      - "@modelcontextprotocol/server-memory"
    enabled: true
"""
