from typing import List

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


class Settings(BaseSettings):
    """Settings for the autonomous agent."""

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

    LLM_PROVIDER: LLMProviderType = LLMProviderType.OPENAI

    #: Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-2"

    #: OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    #: xAI
    XAI_API_KEY: str = ""
    XAI_MODEL: str = "grok-2-latest"

    #: DeepSeek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_MODEL: str = "deepseek-reasoner"
    DEEPSEEK_API_BASE_URL: str = "https://api.deepseek.com"

    #: Qwen
    QWEN_API_KEY: str = ""
    QWEN_MODEL: str = "qwen-max"
    QWEN_API_BASE_URL: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    #: Venice
    VENICE_API_KEY: str = ""
    VENICE_MODEL: str = "venice-2-13b"
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
    LLAMA_MODEL_PATH: str = "/path/to/your/local/llama/model"

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


settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore[call-arg]
