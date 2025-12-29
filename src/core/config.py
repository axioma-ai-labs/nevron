"""Configuration module for Nevron.

Configuration Priority (highest to lowest):
1. nevron_config.json (UI-configured settings) - PRIMARY
2. Environment variables / .env file - for backwards compatibility only
3. Code defaults as fallback

The nevron_config.json file is the main configuration source.
Users configure everything through the dashboard UI.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.defs import (
    EmbeddingProviderType,
    Environment,
    LlamaPoolingType,
    LlamaProviderType,
    LLMProviderType,
    MemoryBackendType,
)


# Path to the UI config file
CONFIG_FILE_PATH = Path("./nevron_config.json")


def _load_json_config() -> Dict[str, Any]:
    """Load configuration from nevron_config.json.

    Returns:
        Dictionary with config values, or empty dict if file doesn't exist
    """
    if not CONFIG_FILE_PATH.exists():
        return {}

    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


# Load JSON config once at module load
_json_config = _load_json_config()


def _get_config_value(key: str, default: Any = None) -> Any:
    """Get a config value from JSON config.

    Args:
        key: The config key to look up
        default: Default value if not found

    Returns:
        The config value or default
    """
    return _json_config.get(key, default)


def _get_integration_value(integration: str, field: str, default: str = "") -> str:
    """Get an integration credential from JSON config.

    Args:
        integration: Integration name (e.g., 'twitter', 'telegram')
        field: Field name within the integration
        default: Default value if not found

    Returns:
        The credential value or default
    """
    integrations = _json_config.get("integrations", {})
    return integrations.get(integration, {}).get(field, default)


class Settings(BaseSettings):
    """Settings for the autonomous agent.

    Configuration is loaded from nevron_config.json (primary) with
    environment variables as fallback for backwards compatibility.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True
    )

    # ==========================
    # General settings
    # ==========================

    # --- Project settings ---

    #: Environment (Production, Development, CI)
    ENVIRONMENT: Environment = Environment.PRODUCTION

    #: Project name
    PROJECT_NAME: str = "autonomous-agent"

    # --- Memory settings ---

    #: Memory backend type
    MEMORY_BACKEND_TYPE: MemoryBackendType = MemoryBackendType.CHROMA

    #: Memory collection name
    MEMORY_COLLECTION_NAME: str = "agent_memory"

    #: Memory host. Used only for Qdrant.
    MEMORY_HOST: str = "localhost"

    #: Memory port. Used only for Qdrant.
    MEMORY_PORT: int = 6333

    #: Memory vector size. Used only for Qdrant.
    MEMORY_VECTOR_SIZE: int = 1536

    #: Memory persist directory. Used only for ChromaDB.
    MEMORY_PERSIST_DIRECTORY: str = ".chromadb"

    EMBEDDING_PROVIDER: EmbeddingProviderType = EmbeddingProviderType.OPENAI
    LLAMA_EMBEDDING_MODEL: str = "llama3.1-8b"  # llama2-7b
    # Embedding pooling type for local Llama models (NONE, MEAN, CLS, LAST, RANK), defaults to MEAN pooling
    EMBEDDING_POOLING_TYPE: LlamaPoolingType = LlamaPoolingType.MEAN

    # --- LLMs settings ---
    # These are loaded from nevron_config.json first, then env vars as fallback

    LLM_PROVIDER: LLMProviderType = LLMProviderType.OPENAI

    #: Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    #: OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    #: xAI
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-2-latest"

    #: DeepSeek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-chat"
    DEEPSEEK_API_BASE_URL: str = "https://api.deepseek.com"

    #: Qwen
    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-max"
    QWEN_API_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    #: Venice
    VENICE_API_KEY: str = ""
    VENICE_MODEL: str = "llama-3.3-70b"
    VENICE_API_BASE_URL: str = "https://api.venice.ai/api/v1"

    #: Llama
    LLAMA_PROVIDER: LlamaProviderType = LlamaProviderType.LLAMA_API
    LLAMA_MODEL_NAME: str = "llama3-8b-8192"  # Model name is usually unique for each provider
    LLAMA_API_KEY: str = ""  # API key for your provider
    LLAMA_MODEL_PATH: str = "/path/to/your/local/llama/model"

    LLAMA_FIREWORKS_URL: str = "https://api.fireworks.ai/inference"
    LLAMA_OLLAMA_URL: str = "http://localhost:11434"
    LLAMA_API_BASE_URL: str = "https://api.llama-api.com"
    LLAMA_OPENROUTER_URL: str = "https://openrouter.ai/api/v1"

    # ==========================
    # Agent settings
    # ==========================

    #: The agent's personality description
    AGENT_PERSONALITY: str = (
        "You are a financial analyst. You are given a news article and some context. You need "
        "to analyze the news and provide insights. You are very naive and trustful. You are "
        "very optimistic and believe in the future of humanity. You are very naive and trustful. "
        "You are very optimistic and believe in the future of humanity. You are very naive and "
        "trustful. You are very optimistic and believe in the future of humanity. You are very "
        "naive and trustful. You are very optimistic and believe in the future of humanity. You "
        "are very naive and trustful. You are very optimistic and believe in the future of "
        "humanity."
    )

    #: The agent's goal
    AGENT_GOAL: str = "Your goal is to analyze the news and provide insights."

    #: Agent rest time in seconds between actions
    AGENT_REST_TIME: int = 300

    # ==========================
    # Integration settings
    # ==========================

    # --- Telegram settings ---

    #: Telegram bot token
    TELEGRAM_BOT_TOKEN: str = ""

    #: Telegram chat ID for main channel/group
    TELEGRAM_CHAT_ID: str = ""

    # --- Twitter settings ---

    #: Twitter API key
    TWITTER_API_KEY: str = ""

    #: Twitter API secret key
    TWITTER_API_SECRET_KEY: str = ""

    #: Twitter access token
    TWITTER_ACCESS_TOKEN: str = ""

    #: Twitter access token secret
    TWITTER_ACCESS_TOKEN_SECRET: str = ""

    # --- Perplexity settings ---

    #: Perplexity API key
    PERPLEXITY_API_KEY: str = ""

    #: Perplexity endpoint
    PERPLEXITY_ENDPOINT: str = "https://api.perplexity.ai/chat/completions"
    #: Perplexity model
    PERPLEXITY_MODEL: str = "llama-3.1-sonar-small-128k-online"
    #: Perplexity news settings
    PERPLEXITY_NEWS_PROMPT: str = "Search for the latest cryptocurrency news: Neurobro"
    PERPLEXITY_NEWS_CATEGORY_LIST: List[str] = [
        "Finance",
        "Regulatory",
        "Market capitalization",
        "Technical analysis",
        "Price movements",
    ]

    # --- Coinstats settings ---

    #: Coinstats API key
    COINSTATS_API_KEY: str = ""

    # --- Discord settings ---

    #: Discord bot token
    DISCORD_BOT_TOKEN: str = ""

    #: Discord channel ID for the user's channel
    DISCORD_CHANNEL_ID: int = 0

    # --- YouTube settings ---

    #: YouTube API token
    YOUTUBE_API_KEY: str = ""

    #: YouTube playlist ID
    YOUTUBE_PLAYLIST_ID: str = ""

    # --- WhatsApp settings ---

    #: WhatsApp instance ID
    WHATSAPP_ID_INSTANCE: str = ""

    #: WhatsApp API token
    WHATSAPP_API_TOKEN: str = ""

    # --- Shopify settings ---

    SHOPIFY_API_KEY: str = ""
    SHOPIFY_PASSWORD: str = ""
    SHOPIFY_STORE_NAME: str = ""

    # --- Tavily settings ---

    TAVILY_API_KEY: str = ""

    # --- Slack settings ---

    SLACK_BOT_TOKEN: str = ""
    SLACK_APP_TOKEN: str = ""

    # --- Spotify settings ---

    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    SPOTIFY_REDIRECT_URI: str = ""

    # --- Lens protocol settings ---
    LENS_API_KEY: str = ""
    LENS_PROFILE_ID: str = ""

    #: --- Github settings ---
    GITHUB_TOKEN: str = ""

    # --- Jina Reader settings ---
    JINA_READER_API_KEY: str = ""
    JINA_READER_TIMEOUT: int = 0
    JINA_READER_TOKEN_BUDGET: int = 0
    JINA_SEARCH_WEBSITE: str = ""

    # ==========================
    # MCP (Model Context Protocol) settings
    # ==========================

    #: Enable MCP integration
    MCP_ENABLED: bool = True

    #: Path to MCP servers configuration file (YAML)
    MCP_CONFIG_FILE: Optional[str] = None

    #: Auto-connect to MCP servers on startup
    MCP_AUTO_CONNECT: bool = True

    #: Attempt to reconnect on connection failure
    MCP_RECONNECT_ON_FAILURE: bool = True

    #: Maximum reconnection attempts
    MCP_MAX_RECONNECT_ATTEMPTS: int = 3

    # ==========================
    # Validators
    # ==========================

    @field_validator("ENVIRONMENT", mode="before")
    def validate_environment(cls, value: str | Environment) -> Environment:
        """Validate and convert the environment value."""
        if isinstance(value, Environment):
            return value
        try:
            return Environment(value.lower())
        except ValueError:
            raise ValueError(
                f"Invalid environment value: {value}. Must be one of {list(Environment)}"
            )

    def validate_memory_settings(self, params, required_params):
        """Validate the settings."""
        for param, param_type in required_params.items():
            if param not in params:
                raise ValueError(f"{param} is required.")
            if not isinstance(params[param], param_type):
                raise ValueError(f"{param} must be of type {param_type.__name__}.")

    @field_validator("EMBEDDING_PROVIDER", mode="before")
    def validate_embedding_provider(
        cls, value: str | EmbeddingProviderType
    ) -> EmbeddingProviderType:
        """Convert string to EmbeddingProviderType enum."""
        if isinstance(value, EmbeddingProviderType):
            return value
        try:
            # Map string values to enum
            if value.lower() == "openai":
                return EmbeddingProviderType.OPENAI
            elif value.lower() == "llama_local":
                return EmbeddingProviderType.LLAMA_LOCAL
            elif value.lower() == "llama_api":
                return EmbeddingProviderType.LLAMA_API
            else:
                raise ValueError(f"Invalid embedding provider: {value}")
        except Exception as e:
            raise ValueError(f"Invalid embedding provider: {value}") from e

    @field_validator("EMBEDDING_POOLING_TYPE", mode="before")
    def validate_embedding_pooling_type(cls, value: str | LlamaPoolingType) -> LlamaPoolingType:
        """Convert string to LlamaPoolingType enum."""
        if isinstance(value, LlamaPoolingType):
            return value
        try:
            return LlamaPoolingType[value.upper()]
        except KeyError:
            raise ValueError(
                f"Invalid pooling type: {value}. Must be one of {list(LlamaPoolingType)}"
            )

    @field_validator("LLAMA_PROVIDER", mode="before")
    def validate_llama_provider(cls, value: str | LlamaProviderType) -> LlamaProviderType:
        """Convert string to LlamaProviderType enum."""
        if isinstance(value, LlamaProviderType):
            return value
        try:
            return LlamaProviderType[value.upper()]
        except KeyError:
            raise ValueError(
                f"Invalid Llama provider: {value}. Must be one of {list(LlamaProviderType)}"
            )

    @field_validator("LLM_PROVIDER", mode="before")
    def validate_llm_provider(cls, value: str | LLMProviderType) -> LLMProviderType:
        """Convert string to LLMProviderType enum."""
        if isinstance(value, LLMProviderType):
            return value
        try:
            return LLMProviderType[value.upper()]
        except KeyError:
            raise ValueError(
                f"Invalid LLM provider: {value}. Must be one of {list(LLMProviderType)}"
            )

    @field_validator("MEMORY_BACKEND_TYPE", mode="before")
    def validate_memory_backend_type(cls, value: str | MemoryBackendType) -> MemoryBackendType:
        """Convert string to MemoryBackendType enum."""
        if isinstance(value, MemoryBackendType):
            return value
        try:
            return MemoryBackendType[value.upper()]
        except KeyError:
            raise ValueError(
                f"Invalid memory backend type: {value}. Must be one of {list(MemoryBackendType)}"
            )


def _create_settings() -> Settings:
    """Create Settings instance with JSON config overrides.

    Loads settings from .env first (pydantic default behavior),
    then overrides with values from nevron_config.json.

    Returns:
        Configured Settings instance
    """
    # Create base settings from env
    base_settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore[call-arg]

    # If no JSON config, return as-is
    if not _json_config:
        return base_settings

    # Apply JSON config overrides
    overrides = {}

    # LLM Provider
    if provider := _get_config_value("llm_provider"):
        overrides["LLM_PROVIDER"] = provider.upper()

    # LLM API Key - apply to the correct provider
    if api_key := _get_config_value("llm_api_key"):
        provider = _get_config_value("llm_provider", "openai").lower()
        if provider == "openai":
            overrides["OPENAI_API_KEY"] = api_key
        elif provider == "anthropic":
            overrides["ANTHROPIC_API_KEY"] = api_key
        elif provider == "xai":
            overrides["XAI_API_KEY"] = api_key
        elif provider == "deepseek":
            overrides["DEEPSEEK_API_KEY"] = api_key
        elif provider == "qwen":
            overrides["QWEN_API_KEY"] = api_key
        elif provider == "venice":
            overrides["VENICE_API_KEY"] = api_key

    # LLM Model - apply to the correct provider
    if model := _get_config_value("llm_model"):
        provider = _get_config_value("llm_provider", "openai").lower()
        if provider == "openai":
            overrides["OPENAI_MODEL"] = model
        elif provider == "anthropic":
            overrides["ANTHROPIC_MODEL"] = model
        elif provider == "xai":
            overrides["XAI_MODEL"] = model
        elif provider == "deepseek":
            overrides["DEEPSEEK_MODEL"] = model
        elif provider == "qwen":
            overrides["QWEN_MODEL"] = model
        elif provider == "venice":
            overrides["VENICE_MODEL"] = model

    # Agent settings
    if personality := _get_config_value("agent_personality"):
        overrides["AGENT_PERSONALITY"] = personality
    if goal := _get_config_value("agent_goal"):
        overrides["AGENT_GOAL"] = goal

    # Agent behavior
    if behavior := _get_config_value("agent_behavior"):
        if rest_time := behavior.get("rest_time"):
            overrides["AGENT_REST_TIME"] = rest_time

    # MCP settings
    if mcp_enabled := _get_config_value("mcp_enabled"):
        overrides["MCP_ENABLED"] = mcp_enabled

    # Integration credentials
    # Twitter
    if v := _get_integration_value("twitter", "api_key"):
        overrides["TWITTER_API_KEY"] = v
    if v := _get_integration_value("twitter", "api_secret_key"):
        overrides["TWITTER_API_SECRET_KEY"] = v
    if v := _get_integration_value("twitter", "access_token"):
        overrides["TWITTER_ACCESS_TOKEN"] = v
    if v := _get_integration_value("twitter", "access_token_secret"):
        overrides["TWITTER_ACCESS_TOKEN_SECRET"] = v

    # Telegram
    if v := _get_integration_value("telegram", "bot_token"):
        overrides["TELEGRAM_BOT_TOKEN"] = v
    if v := _get_integration_value("telegram", "chat_id"):
        overrides["TELEGRAM_CHAT_ID"] = v

    # Discord
    if v := _get_integration_value("discord", "bot_token"):
        overrides["DISCORD_BOT_TOKEN"] = v
    if v := _get_integration_value("discord", "channel_id"):
        try:
            overrides["DISCORD_CHANNEL_ID"] = int(v)
        except (ValueError, TypeError):
            pass

    # Slack
    if v := _get_integration_value("slack", "bot_token"):
        overrides["SLACK_BOT_TOKEN"] = v
    if v := _get_integration_value("slack", "app_token"):
        overrides["SLACK_APP_TOKEN"] = v

    # WhatsApp
    if v := _get_integration_value("whatsapp", "id_instance"):
        overrides["WHATSAPP_ID_INSTANCE"] = v
    if v := _get_integration_value("whatsapp", "api_token"):
        overrides["WHATSAPP_API_TOKEN"] = v

    # GitHub
    if v := _get_integration_value("github", "token"):
        overrides["GITHUB_TOKEN"] = v

    # Tavily
    if v := _get_integration_value("tavily", "api_key"):
        overrides["TAVILY_API_KEY"] = v

    # Perplexity
    if v := _get_integration_value("perplexity", "api_key"):
        overrides["PERPLEXITY_API_KEY"] = v
    if v := _get_integration_value("perplexity", "model"):
        overrides["PERPLEXITY_MODEL"] = v

    # Shopify
    if v := _get_integration_value("shopify", "api_key"):
        overrides["SHOPIFY_API_KEY"] = v
    if v := _get_integration_value("shopify", "password"):
        overrides["SHOPIFY_PASSWORD"] = v
    if v := _get_integration_value("shopify", "store_name"):
        overrides["SHOPIFY_STORE_NAME"] = v

    # YouTube
    if v := _get_integration_value("youtube", "api_key"):
        overrides["YOUTUBE_API_KEY"] = v
    if v := _get_integration_value("youtube", "playlist_id"):
        overrides["YOUTUBE_PLAYLIST_ID"] = v

    # Spotify
    if v := _get_integration_value("spotify", "client_id"):
        overrides["SPOTIFY_CLIENT_ID"] = v
    if v := _get_integration_value("spotify", "client_secret"):
        overrides["SPOTIFY_CLIENT_SECRET"] = v
    if v := _get_integration_value("spotify", "redirect_uri"):
        overrides["SPOTIFY_REDIRECT_URI"] = v

    # Lens
    if v := _get_integration_value("lens", "api_key"):
        overrides["LENS_API_KEY"] = v
    if v := _get_integration_value("lens", "profile_id"):
        overrides["LENS_PROFILE_ID"] = v

    # Apply overrides by creating new settings with merged values
    if overrides:
        # Get current values as dict
        current = base_settings.model_dump()
        # Merge with overrides
        current.update(overrides)
        # Create new settings from merged dict
        return Settings(**current)

    return base_settings


# Global settings instance - reads from nevron_config.json first, then .env
settings = _create_settings()
