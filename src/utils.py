from loguru import logger

from src.core.config import settings


def log_settings():
    """Log all current settings in a structured way."""
    logger.info("=" * 40)
    logger.info("Current Settings")
    logger.info("=" * 40)

    # General settings
    logger.info("General Settings:")
    logger.info(f"  Environment: {settings.ENVIRONMENT}")
    logger.info(f"  Agent's memory powered by: {settings.MEMORY_BACKEND_TYPE}")
    logger.info(f"  Agent's intelligence powered by: {settings.LLM_PROVIDER}")

    # Agent settings
    logger.info("Agent Settings:")
    logger.info(f"  Agent's personality: {settings.AGENT_PERSONALITY}")
    logger.info(f"  Agent's goal: {settings.AGENT_GOAL}")
    logger.info(f"  Agent Rest Time: {settings.AGENT_REST_TIME}s")

    # Integration settings (only log if configured)
    if settings.TELEGRAM_BOT_TOKEN:
        logger.info("Telegram Integration: Configured")
    if settings.TWITTER_API_KEY:
        logger.info("Twitter Integration: Configured")
    if settings.PERPLEXITY_API_KEY:
        logger.info("Perplexity Integration: Configured")

    logger.info("=" * 40)
