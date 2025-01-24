"""Here will be all the definitions of the core components of the system"""

from enum import Enum


class Environment(str, Enum):
    """Environment type."""

    PRODUCTION = "production"
    DEVELOPMENT = "development"
    CI = "ci"


class AgentAction(Enum):
    """The actions that the agent can take."""

    IDLE = "idle"
    ANALYZE_NEWS = "analyze_news"
    CHECK_SIGNAL = "check_signal"


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
