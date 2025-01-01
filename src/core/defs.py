"""Here will be all the definitions of the core components of the system"""

from enum import Enum


class Environment(Enum):
    """The environment of the application."""

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
    """Available memory backend types."""

    QDRANT = "qdrant"
    CHROMA = "chroma"


class LLMProviderType(str, Enum):
    """Available LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    XAI = "xai"
