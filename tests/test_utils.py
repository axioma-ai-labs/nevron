from unittest.mock import MagicMock

import pytest
from loguru import logger

from src.utils import log_settings


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    # General settings
    monkeypatch.setattr("src.core.config.settings.ENVIRONMENT", "test")
    monkeypatch.setattr("src.core.config.settings.MEMORY_BACKEND_TYPE", "test_memory")
    monkeypatch.setattr("src.core.config.settings.LLM_PROVIDER", "test_llm")

    # Agent settings
    monkeypatch.setattr("src.core.config.settings.AGENT_PERSONALITY", "test_personality")
    monkeypatch.setattr("src.core.config.settings.AGENT_GOAL", "test_goal")
    monkeypatch.setattr("src.core.config.settings.AGENT_REST_TIME", 60)

    # LLM and Embedding Integrations
    monkeypatch.setattr("src.core.config.settings.OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setattr("src.core.config.settings.ANTHROPIC_API_KEY", "test_anthropic_key")
    monkeypatch.setattr("src.core.config.settings.XAI_API_KEY", "test_xai_key")
    monkeypatch.setattr("src.core.config.settings.LLAMA_API_KEY", "test_llama_key")
    monkeypatch.setattr("src.core.config.settings.DEEPSEEK_API_KEY", "test_deepseek_key")
    monkeypatch.setattr("src.core.config.settings.QWEN_API_KEY", "test_qwen_key")
    monkeypatch.setattr("src.core.config.settings.VENICE_API_KEY", "test_venice_key")

    # Search and Data Integrations
    monkeypatch.setattr("src.core.config.settings.JINA_READER_API_KEY", "test_jina_reader_key")
    monkeypatch.setattr("src.core.config.settings.JINA_SEARCH_WEBSITE", "test-site.com")
    monkeypatch.setattr("src.core.config.settings.PERPLEXITY_API_KEY", "test_perplexity_key")
    monkeypatch.setattr("src.core.config.settings.TAVILY_API_KEY", "test_tavily_key")
    monkeypatch.setattr("src.core.config.settings.COINSTATS_API_KEY", "test_coinstats_key")

    # Social Media Integrations
    monkeypatch.setattr("src.core.config.settings.TWITTER_API_KEY", "test_twitter_key")
    monkeypatch.setattr("src.core.config.settings.TELEGRAM_BOT_TOKEN", "test_telegram_token")
    monkeypatch.setattr("src.core.config.settings.DISCORD_BOT_TOKEN", "test_discord_token")
    monkeypatch.setattr("src.core.config.settings.SLACK_BOT_TOKEN", "test_slack_token")
    monkeypatch.setattr("src.core.config.settings.WHATSAPP_API_TOKEN", "test_whatsapp_token")
    monkeypatch.setattr("src.core.config.settings.LENS_API_KEY", "test_lens_key")

    # Other Platform Integrations
    monkeypatch.setattr("src.core.config.settings.YOUTUBE_API_KEY", "test_youtube_key")
    monkeypatch.setattr("src.core.config.settings.SHOPIFY_API_KEY", "test_shopify_key")
    monkeypatch.setattr("src.core.config.settings.SPOTIFY_CLIENT_ID", "test_spotify_id")
    monkeypatch.setattr("src.core.config.settings.GITHUB_TOKEN", "test_github_token")


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger for testing."""
    mock_info = MagicMock()
    monkeypatch.setattr(logger, "info", mock_info)
    return mock_info


def test_log_settings(mock_settings, mock_logger):
    """Test logging settings function."""
    # act:
    log_settings()

    # assert:
    # We expect at least 30 log calls (header + settings + footer)
    assert mock_logger.call_count >= 30

    # Verify the expected log messages
    expected_calls = [
        "=" * 40,
        "Current Settings",
        "=" * 40,
        "General Settings:",
        "  Environment: test",
        "  Agent's memory powered by: test_memory",
        "  Agent's intelligence powered by: test_llm",
        "Agent Settings:",
        "  Agent's personality: test_personality",
        "  Agent's goal: test_goal",
        "  Agent Rest Time: 60s",
        "Integration Settings:",
        "  OpenAI Integration: Configured",
        "  Anthropic Integration: Configured",
        "  XAI Integration: Configured",
        "  Llama API Integration: Configured",
        "  DeepSeek Integration: Configured",
        "  Qwen Integration: Configured",
        "  Venice Integration: Configured",
        "  Jina Reader Integration: Configured",
        "  Jina Search Integration: Configured",
        "  Perplexity Integration: Configured",
        "  Tavily Integration: Configured",
        "  Coinstats Integration: Configured",
        "  Twitter Integration: Configured",
        "  Telegram Integration: Configured",
        "  Discord Integration: Configured",
        "  Slack Integration: Configured",
        "  WhatsApp Integration: Configured",
        "  Lens Protocol Integration: Configured",
        "  YouTube Integration: Configured",
        "  Shopify Integration: Configured",
        "  Spotify Integration: Configured",
        "  GitHub Integration: Configured",
        "=" * 40,
    ]

    for expected_call in expected_calls:
        mock_logger.assert_any_call(expected_call)
