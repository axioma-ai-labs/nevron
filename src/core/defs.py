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
    JUST_ANALYZED_NEWS = "just_analyzed_news"
    JUST_ANALYZED_SIGNAL = "just_analyzed_signal"

    @classmethod
    def from_action(cls, action: AgentAction) -> "AgentState":
        """Convert an AgentAction to the corresponding AgentState.

        Args:
            action: The AgentAction to convert

        Returns:
            The corresponding AgentState
        """
        action_to_state = {
            AgentAction.IDLE: cls.IDLE,
            AgentAction.ANALYZE_NEWS: cls.JUST_ANALYZED_NEWS,
            AgentAction.CHECK_SIGNAL: cls.JUST_ANALYZED_SIGNAL,
        }
        return action_to_state.get(action, cls.DEFAULT)


class MemoryBackendType(str, Enum):
    """Available memory backend types."""

    QDRANT = "qdrant"
    CHROMA = "chroma"


class LLMProviderType(str, Enum):
    """Available LLM provider types."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    XAI = "xai"
