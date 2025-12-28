"""Tests for MCP configuration."""

import os
import tempfile

import pytest

from src.mcp.config import MCPServerConfig, MCPSettings, MCPTransportType


class TestMCPServerConfig:
    """Tests for MCPServerConfig."""

    def test_stdio_config_creation(self):
        """Test creating a STDIO transport config."""
        config = MCPServerConfig(
            name="test_server",
            transport=MCPTransportType.STDIO,
            command="npx",
            args=["@modelcontextprotocol/server-test"],
        )

        assert config.name == "test_server"
        assert config.transport == MCPTransportType.STDIO
        assert config.command == "npx"
        assert config.enabled is True

    def test_http_config_creation(self):
        """Test creating an HTTP transport config."""
        config = MCPServerConfig(
            name="http_server",
            transport=MCPTransportType.HTTP,
            url="http://localhost:8000/mcp",
        )

        assert config.name == "http_server"
        assert config.transport == MCPTransportType.HTTP
        assert config.url == "http://localhost:8000/mcp"

    def test_stdio_config_requires_command(self):
        """Test that STDIO config requires command."""
        with pytest.raises(ValueError, match="command"):
            MCPServerConfig(
                name="bad_config",
                transport=MCPTransportType.STDIO,
            )

    def test_http_config_requires_url(self):
        """Test that HTTP config requires URL."""
        with pytest.raises(ValueError, match="url"):
            MCPServerConfig(
                name="bad_config",
                transport=MCPTransportType.HTTP,
            )

    def test_env_var_expansion(self):
        """Test that environment variables are expanded."""
        os.environ["TEST_TOKEN"] = "secret_value"
        try:
            config = MCPServerConfig(
                name="env_test",
                transport=MCPTransportType.STDIO,
                command="test",
                env={"TOKEN": "${TEST_TOKEN}"},
            )
            assert config.env["TOKEN"] == "secret_value"
        finally:
            del os.environ["TEST_TOKEN"]

    def test_env_var_missing(self):
        """Test handling of missing environment variables."""
        config = MCPServerConfig(
            name="env_test",
            transport=MCPTransportType.STDIO,
            command="test",
            env={"TOKEN": "${NONEXISTENT_VAR}"},
        )
        assert config.env["TOKEN"] == ""

    def test_disabled_config(self):
        """Test disabled server config."""
        config = MCPServerConfig(
            name="disabled_server",
            transport=MCPTransportType.STDIO,
            command="test",
            enabled=False,
        )
        assert config.enabled is False


class TestMCPSettings:
    """Tests for MCPSettings."""

    def test_default_settings(self):
        """Test default settings creation."""
        settings = MCPSettings()

        assert settings.enabled is True
        assert settings.servers == []
        assert settings.auto_connect is True
        assert settings.max_reconnect_attempts == 3

    def test_settings_with_servers(self):
        """Test settings with server configurations."""
        settings = MCPSettings(
            servers=[
                MCPServerConfig(
                    name="server1",
                    transport=MCPTransportType.STDIO,
                    command="cmd1",
                ),
                MCPServerConfig(
                    name="server2",
                    transport=MCPTransportType.STDIO,
                    command="cmd2",
                    enabled=False,
                ),
            ]
        )

        assert len(settings.servers) == 2
        enabled = settings.get_enabled_servers()
        assert len(enabled) == 1
        assert enabled[0].name == "server1"

    def test_from_yaml(self):
        """Test loading settings from YAML file."""
        yaml_content = """
enabled: true
auto_connect: true
max_reconnect_attempts: 5

servers:
  - name: filesystem
    transport: stdio
    command: npx
    args:
      - "@modelcontextprotocol/server-filesystem"
      - "/workspace"
    enabled: true

  - name: github
    transport: stdio
    command: npx
    args:
      - "@modelcontextprotocol/server-github"
    enabled: false
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                settings = MCPSettings.from_yaml(f.name)

                assert settings.enabled is True
                assert settings.max_reconnect_attempts == 5
                assert len(settings.servers) == 2
                assert settings.servers[0].name == "filesystem"
                assert settings.servers[1].name == "github"

                enabled = settings.get_enabled_servers()
                assert len(enabled) == 1
                assert enabled[0].name == "filesystem"

            finally:
                os.unlink(f.name)

    def test_from_yaml_file_not_found(self):
        """Test error when YAML file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            MCPSettings.from_yaml("/nonexistent/path/config.yaml")

    def test_from_yaml_empty_file(self):
        """Test loading from empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()

            try:
                settings = MCPSettings.from_yaml(f.name)
                assert settings.enabled is True
                assert settings.servers == []
            finally:
                os.unlink(f.name)

    def test_get_enabled_servers_empty(self):
        """Test get_enabled_servers with no servers."""
        settings = MCPSettings()
        assert settings.get_enabled_servers() == []

    def test_get_enabled_servers_all_disabled(self):
        """Test get_enabled_servers when all are disabled."""
        settings = MCPSettings(
            servers=[
                MCPServerConfig(
                    name="server1",
                    transport=MCPTransportType.STDIO,
                    command="cmd1",
                    enabled=False,
                ),
            ]
        )
        assert settings.get_enabled_servers() == []
