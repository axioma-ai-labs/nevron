from unittest.mock import MagicMock

import pytest
from loguru import logger

from src.utils import log_settings


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    # arrange:
    monkeypatch.setattr("src.core.config.settings.ENVIRONMENT", "test")
    monkeypatch.setattr("src.core.config.settings.PERSISTENT_Q_TABLE_PATH", "/test/path")
    monkeypatch.setattr("src.core.config.settings.MEMORY_BACKEND_TYPE", "test_memory")
    monkeypatch.setattr("src.core.config.settings.LLM_PROVIDER", "test_llm")
    monkeypatch.setattr("src.core.config.settings.AGENT_PERSONALITY", "test_personality")
    monkeypatch.setattr("src.core.config.settings.AGENT_GOAL", "test_goal")
    monkeypatch.setattr("src.core.config.settings.AGENT_REST_TIME", 60)
    monkeypatch.setattr("src.core.config.settings.TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setattr("src.core.config.settings.TWITTER_API_KEY", "test_key")
    monkeypatch.setattr("src.core.config.settings.PERPLEXITY_API_KEY", "test_key")


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger for testing."""
    # arrange:
    mock_info = MagicMock()
    monkeypatch.setattr(logger, "info", mock_info)
    return mock_info


@pytest.mark.skip(reason="Skipping test, since we need to change the mocked settings")
def test_log_settings(mock_settings, mock_logger):
    """Test logging settings function."""
    # act:
    log_settings()

    # assert:
    assert mock_logger.call_count >= 13  # At least 13 log calls expected

    # Verify some specific log messages
    expected_calls = [
        "=" * 40,
        "Current Settings",
        "=" * 40,
        "General Settings:",
        "  Environment: test",
        "  Planning Module table path: /test/path",
        "  Agent's memory powered by: test_memory",
        "  Agent's intelligence powered by: test_llm",
        "Agent Settings:",
        "  Agent's personality: test_personality",
        "  Agent's goal: test_goal",
        "  Agent Rest Time: 60s",
        "Telegram Integration: Configured",
        "Twitter Integration: Configured",
        "Perplexity Integration: Configured",
    ]

    for expected_call in expected_calls:
        mock_logger.assert_any_call(expected_call)
