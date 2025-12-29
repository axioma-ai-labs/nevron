"""UI Configuration module for the Nevron dashboard.

This module provides a comprehensive configuration system for the dashboard UI,
storing settings in a JSON file (nevron_config.json). This allows users to
configure the agent entirely through the UI without editing environment files.

Configuration Hierarchy (priority order):
1. .env file (overrides everything) - for developer use
2. nevron_config.json (UI-configured settings)
3. Code defaults as fallback
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field
from loguru import logger


# Default config file path (relative to working directory)
CONFIG_FILE_PATH = Path("./nevron_config.json")


# ============================================================================
# Integration Credential Models
# ============================================================================


class TwitterCredentials(BaseModel):
    """Twitter API credentials."""
    api_key: str = Field(default="", description="Twitter API key")
    api_secret_key: str = Field(default="", description="Twitter API secret key")
    access_token: str = Field(default="", description="Twitter access token")
    access_token_secret: str = Field(default="", description="Twitter access token secret")


class TelegramCredentials(BaseModel):
    """Telegram bot credentials."""
    bot_token: str = Field(default="", description="Telegram bot token")
    chat_id: str = Field(default="", description="Telegram chat ID")


class DiscordCredentials(BaseModel):
    """Discord bot credentials."""
    bot_token: str = Field(default="", description="Discord bot token")
    channel_id: str = Field(default="", description="Discord channel ID")


class SlackCredentials(BaseModel):
    """Slack credentials."""
    bot_token: str = Field(default="", description="Slack bot token")
    app_token: str = Field(default="", description="Slack app token")


class WhatsAppCredentials(BaseModel):
    """WhatsApp credentials."""
    id_instance: str = Field(default="", description="WhatsApp instance ID")
    api_token: str = Field(default="", description="WhatsApp API token")


class GitHubCredentials(BaseModel):
    """GitHub credentials."""
    token: str = Field(default="", description="GitHub personal access token")


class GoogleDriveCredentials(BaseModel):
    """Google Drive credentials (simplified - full OAuth handled separately)."""
    enabled: bool = Field(default=False, description="Whether Google Drive is configured")


class TavilyCredentials(BaseModel):
    """Tavily search API credentials."""
    api_key: str = Field(default="", description="Tavily API key")


class PerplexityCredentials(BaseModel):
    """Perplexity API credentials."""
    api_key: str = Field(default="", description="Perplexity API key")
    model: str = Field(default="llama-3.1-sonar-small-128k-online", description="Perplexity model")


class ShopifyCredentials(BaseModel):
    """Shopify credentials."""
    api_key: str = Field(default="", description="Shopify API key")
    password: str = Field(default="", description="Shopify password")
    store_name: str = Field(default="", description="Shopify store name")


class YouTubeCredentials(BaseModel):
    """YouTube credentials."""
    api_key: str = Field(default="", description="YouTube API key")
    playlist_id: str = Field(default="", description="YouTube playlist ID")


class SpotifyCredentials(BaseModel):
    """Spotify credentials."""
    client_id: str = Field(default="", description="Spotify client ID")
    client_secret: str = Field(default="", description="Spotify client secret")
    redirect_uri: str = Field(default="", description="Spotify redirect URI")


class LensCredentials(BaseModel):
    """Lens Protocol credentials."""
    api_key: str = Field(default="", description="Lens API key")
    profile_id: str = Field(default="", description="Lens profile ID")


class IntegrationsConfig(BaseModel):
    """All integration credentials."""
    twitter: TwitterCredentials = Field(default_factory=TwitterCredentials)
    telegram: TelegramCredentials = Field(default_factory=TelegramCredentials)
    discord: DiscordCredentials = Field(default_factory=DiscordCredentials)
    slack: SlackCredentials = Field(default_factory=SlackCredentials)
    whatsapp: WhatsAppCredentials = Field(default_factory=WhatsAppCredentials)
    github: GitHubCredentials = Field(default_factory=GitHubCredentials)
    google_drive: GoogleDriveCredentials = Field(default_factory=GoogleDriveCredentials)
    tavily: TavilyCredentials = Field(default_factory=TavilyCredentials)
    perplexity: PerplexityCredentials = Field(default_factory=PerplexityCredentials)
    shopify: ShopifyCredentials = Field(default_factory=ShopifyCredentials)
    youtube: YouTubeCredentials = Field(default_factory=YouTubeCredentials)
    spotify: SpotifyCredentials = Field(default_factory=SpotifyCredentials)
    lens: LensCredentials = Field(default_factory=LensCredentials)


# ============================================================================
# MCP Server Configuration
# ============================================================================


class MCPServerUIConfig(BaseModel):
    """MCP server configuration for UI."""
    name: str = Field(..., description="Unique name for this server")
    transport: str = Field(default="stdio", description="Transport type (stdio, http, sse)")
    command: Optional[str] = Field(default=None, description="Command for STDIO transport")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    url: Optional[str] = Field(default=None, description="URL for HTTP/SSE transport")
    enabled: bool = Field(default=True, description="Whether server is enabled")


# ============================================================================
# Agent Behavior Configuration
# ============================================================================


class AgentBehaviorConfig(BaseModel):
    """Agent behavior settings."""
    rest_time: int = Field(default=300, description="Rest time between actions in seconds")
    max_consecutive_failures: int = Field(default=3, description="Max failures before intervention")
    verbosity: str = Field(default="normal", description="Logging verbosity (quiet, normal, verbose)")


# ============================================================================
# Main UI Configuration Model
# ============================================================================


class UIConfig(BaseModel):
    """Comprehensive UI configuration model for dashboard settings.

    This contains all settings needed to configure and run the agent:
    - LLM provider, API key, and model selection
    - Agent personality, goal, and behavior settings
    - Enabled actions and their configuration
    - Integration credentials for all services
    - MCP server configurations
    """

    # LLM Settings
    llm_provider: str = Field(default="openai", description="LLM provider (openai, anthropic, xai, deepseek, qwen, venice)")
    llm_api_key: str = Field(default="", description="API key for the selected LLM provider")
    llm_model: str = Field(default="gpt-4o-mini", description="Model name for the selected provider")

    # Agent Identity Settings
    agent_name: str = Field(default="Nevron", description="The agent's name")
    agent_personality: str = Field(
        default="You are a helpful AI assistant.",
        description="The agent's personality description"
    )
    agent_goal: str = Field(
        default="Help users accomplish their tasks effectively.",
        description="The agent's primary goal"
    )

    # Agent Behavior Settings
    agent_behavior: AgentBehaviorConfig = Field(
        default_factory=AgentBehaviorConfig,
        description="Agent behavior configuration"
    )

    # Tools/Actions Configuration
    enabled_actions: List[str] = Field(
        default_factory=lambda: ["idle", "analyze_news"],
        description="List of enabled action names from AgentAction enum"
    )

    # Integration Credentials
    integrations: IntegrationsConfig = Field(
        default_factory=IntegrationsConfig,
        description="Integration credentials for all services"
    )

    # MCP Settings
    mcp_enabled: bool = Field(default=False, description="Enable MCP integration")
    mcp_servers: List[MCPServerUIConfig] = Field(
        default_factory=list,
        description="List of MCP server configurations"
    )

    # Legacy compatibility - keep mcp_servers dict support
    def model_post_init(self, __context: Any) -> None:
        """Handle legacy mcp_servers dict format."""
        pass


class IntegrationsConfigResponse(BaseModel):
    """Response model for integrations with masked credentials."""
    twitter: Dict[str, str]
    telegram: Dict[str, str]
    discord: Dict[str, str]
    slack: Dict[str, str]
    whatsapp: Dict[str, str]
    github: Dict[str, str]
    google_drive: Dict[str, Any]
    tavily: Dict[str, str]
    perplexity: Dict[str, str]
    shopify: Dict[str, str]
    youtube: Dict[str, str]
    spotify: Dict[str, str]
    lens: Dict[str, str]


class UIConfigResponse(BaseModel):
    """Response model for UI config with masked API keys."""

    # LLM Settings
    llm_provider: str
    llm_api_key_masked: str
    llm_model: str

    # Agent Identity
    agent_name: str
    agent_personality: str
    agent_goal: str

    # Agent Behavior
    agent_behavior: AgentBehaviorConfig

    # Enabled Actions
    enabled_actions: List[str]

    # Integrations (with masked credentials)
    integrations: IntegrationsConfigResponse

    # MCP Settings
    mcp_enabled: bool
    mcp_servers: List[MCPServerUIConfig]


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


def mask_credentials(creds: BaseModel) -> Dict[str, Any]:
    """Mask all string credentials in a credentials model.

    Args:
        creds: A credentials model instance

    Returns:
        Dictionary with masked credential values
    """
    result = {}
    for field_name, field_value in creds.model_dump().items():
        if isinstance(field_value, str) and field_value:
            result[field_name] = mask_api_key(field_value)
        else:
            result[field_name] = field_value
    return result


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
    """Convert UIConfig to response format with masked API keys.

    Args:
        config: UIConfig instance

    Returns:
        UIConfigResponse with masked API keys
    """
    # Mask all integration credentials
    masked_integrations = IntegrationsConfigResponse(
        twitter=mask_credentials(config.integrations.twitter),
        telegram=mask_credentials(config.integrations.telegram),
        discord=mask_credentials(config.integrations.discord),
        slack=mask_credentials(config.integrations.slack),
        whatsapp=mask_credentials(config.integrations.whatsapp),
        github=mask_credentials(config.integrations.github),
        google_drive=config.integrations.google_drive.model_dump(),
        tavily=mask_credentials(config.integrations.tavily),
        perplexity=mask_credentials(config.integrations.perplexity),
        shopify=mask_credentials(config.integrations.shopify),
        youtube=mask_credentials(config.integrations.youtube),
        spotify=mask_credentials(config.integrations.spotify),
        lens=mask_credentials(config.integrations.lens),
    )

    return UIConfigResponse(
        llm_provider=config.llm_provider,
        llm_api_key_masked=mask_api_key(config.llm_api_key),
        llm_model=config.llm_model,
        agent_name=config.agent_name,
        agent_personality=config.agent_personality,
        agent_goal=config.agent_goal,
        agent_behavior=config.agent_behavior,
        enabled_actions=config.enabled_actions,
        integrations=masked_integrations,
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


def get_all_available_actions() -> List[Dict[str, Any]]:
    """Get all available actions from AgentAction enum with metadata.

    Returns:
        List of action dictionaries with name, value, and category
    """
    from src.core.defs import AgentAction

    # Group actions by category based on their prefix/type
    action_categories = {
        "workflows": ["analyze_news", "check_signal", "idle"],
        "social_media": [
            "post_tweet", "listen_discord_messages", "send_discord_message",
            "send_telegram_message", "post_lens", "fetch_lens",
            "listen_whatsapp_messages", "send_whatsapp_message",
            "listen_slack_messages", "send_slack_message"
        ],
        "research": ["search_tavily", "ask_perplexity", "ask_coinstats"],
        "development": [
            "create_github_issue", "create_github_pr", "process_github_memories",
            "search_google_drive", "upload_google_drive"
        ],
        "ecommerce": ["get_shopify_product", "get_shopify_orders", "update_shopify_product"],
        "media": [
            "search_youtube_video", "retrieve_youtube_playlist",
            "search_spotify_song", "retrieve_spotify_playlist"
        ],
    }

    # Create reverse mapping
    action_to_category = {}
    for category, actions in action_categories.items():
        for action in actions:
            action_to_category[action] = category

    result = []
    for action in AgentAction:
        result.append({
            "name": action.name,
            "value": action.value,
            "category": action_to_category.get(action.value, "other"),
        })

    return result


# Action to required integration mapping
ACTION_INTEGRATION_MAP: Dict[str, str] = {
    "post_tweet": "twitter",
    "send_telegram_message": "telegram",
    "listen_discord_messages": "discord",
    "send_discord_message": "discord",
    "listen_slack_messages": "slack",
    "send_slack_message": "slack",
    "listen_whatsapp_messages": "whatsapp",
    "send_whatsapp_message": "whatsapp",
    "post_lens": "lens",
    "fetch_lens": "lens",
    "search_tavily": "tavily",
    "ask_perplexity": "perplexity",
    "create_github_issue": "github",
    "create_github_pr": "github",
    "process_github_memories": "github",
    "search_google_drive": "google_drive",
    "upload_google_drive": "google_drive",
    "get_shopify_product": "shopify",
    "get_shopify_orders": "shopify",
    "update_shopify_product": "shopify",
    "search_youtube_video": "youtube",
    "retrieve_youtube_playlist": "youtube",
    "search_spotify_song": "spotify",
    "retrieve_spotify_playlist": "spotify",
}
