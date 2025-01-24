"""Custom exceptions for the application."""


class AgentBaseError(Exception):
    """Base exception for Agent project."""

    pass


class MemoryError(AgentBaseError):
    """Custom exception for memory errors."""

    pass


class LLMError(AgentBaseError):
    """Custom exception for LLM errors."""

    pass


class TelegramError(AgentBaseError):
    """Custom exception for Telegram posting errors."""

    pass


class TwitterError(AgentBaseError):
    """Exception raised when posting to Twitter fails."""

    pass


class DiscordError(Exception):
    """Exception raised when Discord operations fail"""

    pass


class WhatsAppError(AgentBaseError):
    """Exception raised when posting to Twitter fails."""

    pass


class APIError(AgentBaseError):
    """Exception raised when API request fails."""

    pass


class CoinstatsError(AgentBaseError):
    """Exception raised when Coinstats API request fails."""

    pass


class ShopifyError(Exception):
    """Raised when Shopify API operations fail."""

    pass


class SpotifyError(Exception):
    """Raised when Spotify API operations fail."""

    pass


class GitHubError(Exception):
    """Raised when WhatsApp operations fail"""

    pass


class ExecutionError(AgentBaseError):
    """Exception raised when execution fails."""

    pass
