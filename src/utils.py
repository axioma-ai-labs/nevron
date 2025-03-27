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
    logger.info("Integration Settings:")

    # LLM and Embedding Integrations
    if settings.OPENAI_API_KEY:
        logger.info("  OpenAI Integration: Configured")
    if settings.ANTHROPIC_API_KEY:
        logger.info("  Anthropic Integration: Configured")
    if settings.XAI_API_KEY:
        logger.info("  XAI Integration: Configured")
    if settings.LLAMA_API_KEY:
        logger.info("  Llama API Integration: Configured")
    if settings.DEEPSEEK_API_KEY:
        logger.info("  DeepSeek Integration: Configured")
    if settings.QWEN_API_KEY:
        logger.info("  Qwen Integration: Configured")
    if settings.VENICE_API_KEY:
        logger.info("  Venice Integration: Configured")

    # Search and Data Integrations
    if settings.JINA_READER_API_KEY:
        logger.info("  Jina Reader Integration: Configured")
    if settings.JINA_SEARCH_WEBSITE:
        logger.info("  Jina Search Integration: Configured")
    if settings.PERPLEXITY_API_KEY:
        logger.info("  Perplexity Integration: Configured")
    if settings.TAVILY_API_KEY:
        logger.info("  Tavily Integration: Configured")
    if settings.COINSTATS_API_KEY:
        logger.info("  Coinstats Integration: Configured")

    # Social Media Integrations
    if settings.TWITTER_API_KEY:
        logger.info("  Twitter Integration: Configured")
    if settings.TELEGRAM_BOT_TOKEN:
        logger.info("  Telegram Integration: Configured")
    if settings.DISCORD_BOT_TOKEN:
        logger.info("  Discord Integration: Configured")
    if settings.SLACK_BOT_TOKEN:
        logger.info("  Slack Integration: Configured")
    if settings.WHATSAPP_API_TOKEN:
        logger.info("  WhatsApp Integration: Configured")
    if settings.LENS_API_KEY:
        logger.info("  Lens Protocol Integration: Configured")

    # Other Platform Integrations
    if settings.YOUTUBE_API_KEY:
        logger.info("  YouTube Integration: Configured")
    if settings.SHOPIFY_API_KEY:
        logger.info("  Shopify Integration: Configured")
    if settings.SPOTIFY_CLIENT_ID:
        logger.info("  Spotify Integration: Configured")
    if settings.GITHUB_TOKEN:
        logger.info("  GitHub Integration: Configured")

    logger.info("=" * 40)
