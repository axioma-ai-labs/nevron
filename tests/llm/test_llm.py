from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest
from loguru import logger

from src.core.config import settings
from src.core.defs import EmbeddingProviderType, LLMProviderType
from src.core.exceptions import LLMError
from src.llm.llm import LLM, get_embedding_client


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger for testing."""
    mock_debug = MagicMock()
    mock_error = MagicMock()
    monkeypatch.setattr(logger, "debug", mock_debug)
    monkeypatch.setattr(logger, "error", mock_error)
    return mock_debug, mock_error


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    monkeypatch.setattr(settings, "LLM_PROVIDER", LLMProviderType.OPENAI)
    monkeypatch.setattr(settings, "AGENT_PERSONALITY", "Test Personality")
    monkeypatch.setattr(settings, "AGENT_GOAL", "Test Goal")
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test-key")
    return settings


@pytest.fixture
def llm(mock_settings):
    """Create an LLM instance with mocked settings."""
    return LLM()


@pytest.mark.parametrize(
    "provider",
    [
        LLMProviderType.OPENAI,
        LLMProviderType.ANTHROPIC,
    ],
)
def test_init(mock_settings, mock_logger, provider):
    """Test LLM initialization with different providers."""
    # arrange:
    mock_debug, _ = mock_logger
    mock_settings.LLM_PROVIDER = provider

    # act:
    llm = LLM()

    # assert:
    assert llm.provider == provider
    mock_debug.assert_called_once_with(f"Using LLM provider: {provider}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider,call_function,expected_response",
    [
        (LLMProviderType.OPENAI, "src.llm.llm.call_openai", "OpenAI response"),
        (LLMProviderType.ANTHROPIC, "src.llm.llm.call_anthropic", "Anthropic response"),
    ],
)
async def test_generate_response(mock_settings, provider, call_function, expected_response):
    """Test response generation with different providers."""
    # arrange:
    mock_settings.LLM_PROVIDER = provider
    messages = [{"role": "user", "content": "Hello"}]
    kwargs = {"temperature": 0.7}

    with patch(call_function, AsyncMock(return_value=expected_response)):
        llm = LLM()

        # act:
        response = await llm.generate_response(messages, **kwargs)

        # assert:
        assert response == expected_response


@pytest.mark.asyncio
async def test_generate_response_with_system_message(llm):
    """Test response generation with automatic system message addition."""
    # arrange:
    messages = [{"role": "user", "content": "Hello"}]
    expected_system_message = {
        "role": "system",
        "content": f"{settings.AGENT_PERSONALITY}\n\n{settings.AGENT_GOAL}",
    }

    with patch("src.llm.llm.call_openai", AsyncMock()) as mock_call:
        # act:
        await llm.generate_response(messages)

        # assert:
        called_messages = mock_call.call_args[0][0]
        assert called_messages[0] == expected_system_message
        assert called_messages[1:] == messages


@pytest.mark.asyncio
async def test_generate_response_existing_system_message(llm):
    """Test response generation when system message already exists."""
    # arrange:
    existing_system = {"role": "system", "content": "Existing system message"}
    messages = [existing_system, {"role": "user", "content": "Hello"}]

    with patch("src.llm.llm.call_openai", AsyncMock()) as mock_call:
        # act:
        await llm.generate_response(messages)

        # assert:
        called_messages = mock_call.call_args[0][0]
        assert called_messages == messages  # Messages should remain unchanged


@pytest.mark.asyncio
async def test_generate_response_invalid_provider(mock_settings):
    """Test error handling for invalid provider."""
    # arrange:
    mock_settings.LLM_PROVIDER = "invalid_provider"
    llm = LLM()
    messages = [{"role": "user", "content": "Hello"}]

    # act/assert:
    with pytest.raises(LLMError, match="Unknown LLM provider: invalid_provider"):
        await llm.generate_response(messages)


def test_get_oai_client(mock_settings):
    """Test OpenAI client creation."""
    # act:
    client = get_embedding_client(EmbeddingProviderType.OPENAI)

    # assert:
    assert isinstance(client, openai.AsyncOpenAI)
    assert client.api_key == "test-key"


@pytest.mark.asyncio
async def test_generate_response_with_kwargs(llm):
    """Test response generation with additional kwargs."""
    # arrange:
    messages = [{"role": "user", "content": "Hello"}]
    kwargs = {"temperature": 0.7, "max_tokens": 100, "model": "gpt-4"}

    with patch("src.llm.llm.call_openai", AsyncMock()) as mock_call:
        # act:
        await llm.generate_response(messages, **kwargs)

        # assert:
        mock_call.assert_called_once_with(mock_call.call_args[0][0], **kwargs)
