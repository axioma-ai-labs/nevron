"""Here will be all the definitions of the core components of the system"""

from enum import Enum

<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
import llama_cpp
=======

# import llama_cpp
>>>>>>> 74f5caf (Tools refactoring and executors implementation)
=======
import llama_cpp
>>>>>>> a287324 (Small fixes)
=======
import llama_cpp
>>>>>>> e4f134c (Integrate llama embeddings (#116))


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
    LISTEN_DISCORD_MESSAGES = "listen_discord_messages"
    SEND_DISCORD_MESSAGE = "send_discord_message"
    SEND_TELEGRAM_MESSAGE = "send_telegram_message"
    POST_LENS = "post_lens"
    FETCH_LENS = "fetch_lens"
    LISTEN_WHATSAPP_MESSAGES = "listen_whatsapp_messages"
    SEND_WHATSAPP_MESSAGE = "send_whatsapp_message"
    LISTEN_SLACK_MESSAGES = "listen_slack_messages"
    SEND_SLACK_MESSAGE = "send_slack_message"

    # === Research ===
    SEARCH_TAVILY = "search_tavily"
    ASK_PERPLEXITY = "ask_perplexity"
    ASK_COINSTATS = "ask_coinstats"

    # === Development ===
    CREATE_GITHUB_ISSUE = "create_github_issue"
    CREATE_GITHUB_PR = "create_github_pr"
    PROCESS_GITHUB_MEMORIES = "process_github_memories"
    SEARCH_GOOGLE_DRIVE = "search_google_drive"
    UPLOAD_GOOGLE_DRIVE = "upload_google_drive"

    # === E-commerce ===
    GET_SHOPIFY_PRODUCT = "get_shopify_product"
    GET_SHOPIFY_ORDERS = "get_shopify_orders"
    UPDATE_SHOPIFY_PRODUCT = "update_shopify_product"

    # === Media ===
    SEARCH_YOUTUBE_VIDEO = "search_youtube_video"
    RETRIEVE_YOUTUBE_PLAYLIST = "retrieve_youtube_playlist"
    SEARCH_SPOTIFY_SONG = "search_spotify_song"
    RETRIEVE_SPOTIFY_PLAYLIST = "retrieve_spotify_playlist"


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
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    VENICE = "venice"


class LlamaProviderType(str, Enum):
    """Llama provider type."""

    OLLAMA = "ollama"
    FIREWORKS = "fireworks"
    LLAMA_API = "llama-api"
    LLAMA_LOCAL = "llama_local"
    OPENROUTER = "openrouter"


<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
class LlamaPoolingType(int, Enum):
=======
class LlamaPoolingType(str, Enum):  # change to int when using llama_cpp
>>>>>>> 74f5caf (Tools refactoring and executors implementation)
=======
class LlamaPoolingType(int, Enum):  # change to int when using llama_cpp
>>>>>>> a287324 (Small fixes)
=======
class LlamaPoolingType(int, Enum):
>>>>>>> e4f134c (Integrate llama embeddings (#116))
    """local Llama model pooling type."""

    NONE = llama_cpp.LLAMA_POOLING_TYPE_NONE
    MEAN = llama_cpp.LLAMA_POOLING_TYPE_MEAN
    CLS = llama_cpp.LLAMA_POOLING_TYPE_CLS
    LAST = llama_cpp.LLAMA_POOLING_TYPE_LAST
    RANK = llama_cpp.LLAMA_POOLING_TYPE_RANK


class EmbeddingProviderType(str, Enum):
    """Embedding provider type."""

    OPENAI = LLMProviderType.OPENAI
    LLAMA_LOCAL = LlamaProviderType.LLAMA_LOCAL
    LLAMA_API = LlamaProviderType.LLAMA_API
