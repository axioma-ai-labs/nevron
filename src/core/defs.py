"""Here will be all the definitions of the core components of the system"""

from enum import Enum


class Environment(str, Enum):
    """Environment type."""

    PRODUCTION = "production"
    DEVELOPMENT = "development"
    CI = "ci"


class AgentAction(Enum):
    """Available actions for the agent."""

    # === Workflows ===
    ANALYZE_NEWS = "analyze_news"
    CHECK_SIGNAL = "check_signal"
    IDLE = "idle"

    # === Social Media ===
    POST_TWEET = "post_tweet"
    SEND_DISCORD_MESSAGE = "send_discord_message"
    SEND_TELEGRAM_MESSAGE = "send_telegram_message"
    POST_LENS = "post_lens"
    SEND_WHATSAPP = "send_whatsapp"

    # === Research ===
    SEARCH_TAVILY = "search_tavily"
    ASK_PERPLEXITY = "ask_perplexity"

    # === Development ===
    CREATE_GITHUB_ISSUE = "create_github_issue"
    CREATE_GITHUB_PR = "create_github_pr"

    # === E-commerce ===
    CREATE_SHOPIFY_PRODUCT = "create_shopify_product"
    UPDATE_SHOPIFY_PRODUCT = "update_shopify_product"

    # === Media ===
    UPLOAD_YOUTUBE_VIDEO = "upload_youtube_video"
    CREATE_SPOTIFY_PLAYLIST = "create_spotify_playlist"


class AgentState(Enum):
    """The states that the agent can be in."""

    DEFAULT = "default"
    IDLE = "idle"
    WAITING_FOR_NEWS = "waiting_for_news"
    JUST_ANALYZED_NEWS = "just_analyzed_news"
    JUST_ANALYZED_SIGNAL = "just_analyzed_signal"


class MemoryBackendType(str, Enum):
    """Memory backend type."""

    CHROMA = "chroma"
    QDRANT = "qdrant"


class LLMProviderType(str, Enum):
    """LLM provider type."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    XAI = "xai"
    LLAMA = "llama"


class LlamaProviderType(str, Enum):
    """Llama provider type."""

    OLLAMA = "ollama"
    FIREWORKS = "fireworks"
    LLAMA_API = "llama-api"
    OPENROUTER = "openrouter"
