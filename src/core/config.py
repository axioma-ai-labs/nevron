from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.core.defs import Environment, LLMProviderType, MemoryBackendType


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

    # --- Planning settings ---

    #: Path to the persistent Q-table file
    PERSISTENT_Q_TABLE_PATH: str = "persistent_q_table.json"

    #: PlanningModule parameters
    PLANNING_ALPHA: float = 0.1  # Default learning rate
    PLANNING_GAMMA: float = 0.95  # Default discount factor
    PLANNING_EPSILON: float = 0.1  # Default exploration rate

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

    #: Perplexity news settings
    PERPLEXITY_NEWS_PROMPT: str = "Search for the latest cryptocurrency news: Neurobro"
    PERPLEXITY_NEWS_CATEGORY_LIST: List[str] = [
        "Finance",
        "Regulatory",
        "Market capitalzation",
        "Technical analysis",
        "Price movements",
    ]

    # --- Coinstats settings ---

    #: Coinstats API key
    COINSTATS_API_KEY: str = ""

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


settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore[call-arg]
