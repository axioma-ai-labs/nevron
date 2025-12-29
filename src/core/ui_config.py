"""UI Configuration module for the Nevron dashboard.

This module provides a simplified configuration system for the dashboard UI,
storing settings in a JSON file (nevron_config.json) rather than requiring
environment variables for all settings.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field
from loguru import logger


# Default config file path (relative to working directory)
CONFIG_FILE_PATH = Path("./nevron_config.json")


class UIConfig(BaseModel):
    """UI configuration model for dashboard settings.

    This contains only the core settings needed for the agent to run:
    - LLM provider, API key, and model selection
    - Agent personality and goal
    - MCP enabled flag and server configuration
    """

    # LLM Settings
    llm_provider: str = Field(default="openai", description="LLM provider (openai, anthropic, xai, deepseek, qwen, venice)")
    llm_api_key: str = Field(default="", description="API key for the selected LLM provider")
    llm_model: str = Field(default="gpt-4o-mini", description="Model name for the selected provider")

    # Agent Identity Settings
    agent_personality: str = Field(
        default="You are a helpful AI assistant.",
        description="The agent's personality description"
    )
    agent_goal: str = Field(
        default="Help users accomplish their tasks effectively.",
        description="The agent's primary goal"
    )

    # MCP Settings
    mcp_enabled: bool = Field(default=False, description="Enable MCP integration")
    mcp_servers: Dict[str, Any] = Field(default_factory=dict, description="MCP server configurations")


class UIConfigResponse(BaseModel):
    """Response model for UI config with masked API key."""

    llm_provider: str
    llm_api_key_masked: str
    llm_model: str
    agent_personality: str
    agent_goal: str
    mcp_enabled: bool
    mcp_servers: Dict[str, Any]


def mask_api_key(key: str) -> str:
    """Mask an API key, showing only the first 3 and last 4 characters.

    Args:
        key: The API key to mask

    Returns:
        Masked API key string (e.g., "sk-...abc1") or "***" if too short
    """
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    return f"{key[:3]}...{key[-4:]}"


def config_exists(config_path: Optional[Path] = None) -> bool:
    """Check if the UI config file exists.

    Args:
        config_path: Optional custom path for the config file

    Returns:
        True if config file exists, False otherwise
    """
    path = config_path or CONFIG_FILE_PATH
    return path.exists()


def load_ui_config(config_path: Optional[Path] = None) -> UIConfig:
    """Load UI configuration from JSON file.

    Args:
        config_path: Optional custom path for the config file

    Returns:
        UIConfig instance with loaded values or defaults
    """
    path = config_path or CONFIG_FILE_PATH

    if not path.exists():
        logger.info(f"Config file not found at {path}, returning defaults")
        return UIConfig()

    try:
        with open(path, "r") as f:
            data = json.load(f)
        logger.info(f"Loaded UI config from {path}")
        return UIConfig(**data)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse config file: {e}")
        return UIConfig()
    except Exception as e:
        logger.error(f"Failed to load config file: {e}")
        return UIConfig()


def save_ui_config(config: UIConfig, config_path: Optional[Path] = None) -> bool:
    """Save UI configuration to JSON file.

    Args:
        config: UIConfig instance to save
        config_path: Optional custom path for the config file

    Returns:
        True if save successful, False otherwise
    """
    path = config_path or CONFIG_FILE_PATH

    try:
        with open(path, "w") as f:
            json.dump(config.model_dump(), f, indent=2)
        logger.info(f"Saved UI config to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to save config file: {e}")
        return False


def get_config_response(config: UIConfig) -> UIConfigResponse:
    """Convert UIConfig to response format with masked API key.

    Args:
        config: UIConfig instance

    Returns:
        UIConfigResponse with masked API key
    """
    return UIConfigResponse(
        llm_provider=config.llm_provider,
        llm_api_key_masked=mask_api_key(config.llm_api_key),
        llm_model=config.llm_model,
        agent_personality=config.agent_personality,
        agent_goal=config.agent_goal,
        mcp_enabled=config.mcp_enabled,
        mcp_servers=config.mcp_servers,
    )


# Available models per provider (hardcoded list)
AVAILABLE_MODELS: Dict[str, list[str]] = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "anthropic": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
    "xai": ["grok-2-latest", "grok-beta"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "qwen": ["qwen-max", "qwen-plus", "qwen-turbo"],
    "venice": ["venice-2-13b"],
}


def get_available_models(provider: str) -> list[str]:
    """Get list of available models for a provider.

    Args:
        provider: LLM provider name

    Returns:
        List of available model names
    """
    return AVAILABLE_MODELS.get(provider.lower(), [])
