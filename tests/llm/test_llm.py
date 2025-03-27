from unittest.mock import AsyncMock, MagicMock, patch

import openai
import pytest
from loguru import logger

from src.core.config import settings
from src.core.defs import EmbeddingProviderType, LLMProviderType
from src.core.exceptions import LLMError
from src.llm.llm import LLM, get_embedding_client, get_llama_model


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
        LLMProviderType.XAI,
        LLMProviderType.LLAMA,
        LLMProviderType.DEEPSEEK,
        LLMProviderType.VENICE,
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
        (LLMProviderType.XAI, "src.llm.llm.call_xai", "XAI response"),
        (LLMProviderType.LLAMA, "src.llm.llm.call_llama", "Llama response"),
        (LLMProviderType.DEEPSEEK, "src.llm.llm.call_deepseek", "DeepSeek response"),
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
async def test_generate_response_venice(mock_settings):
    """Test response generation with Venice provider (which is synchronous)."""
    # arrange:
    mock_settings.LLM_PROVIDER = LLMProviderType.VENICE
    messages = [{"role": "user", "content": "Hello"}]
    kwargs = {"temperature": 0.7}
    expected_response = "Venice response"

    with patch("src.llm.llm.call_venice", return_value=expected_response) as mock_call:
        llm = LLM()

        # act:
        response = await llm.generate_response(messages, **kwargs)

        # assert:
        assert response == expected_response
        mock_call.assert_called_once_with(mock_call.call_args[0][0], **kwargs)


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


@pytest.mark.parametrize(
    "provider,api_key_attr,base_url_attr",
    [
        (EmbeddingProviderType.OPENAI, "OPENAI_API_KEY", None),
        (EmbeddingProviderType.LLAMA_API, "LLAMA_API_KEY", "LLAMA_API_BASE_URL"),
    ],
)
def test_get_embedding_client(mock_settings, provider, api_key_attr, base_url_attr):
    """Test embedding client creation for different providers."""
    # arrange
    setattr(mock_settings, api_key_attr, "test-key")
    if base_url_attr:
        setattr(mock_settings, base_url_attr, "https://test-url.com")

    # act
    client = get_embedding_client(provider)

    # assert
    assert isinstance(client, openai.AsyncOpenAI)
    assert client.api_key == "test-key"
    if base_url_attr:
        assert client.base_url == "https://test-url.com"


@pytest.mark.asyncio
async def test_get_embedding_client_invalid_provider(mock_settings):
    """Test error handling for invalid embedding provider."""
    # act/assert
    with pytest.raises(ValueError, match="Unsupported provider for embedding client"):
        get_embedding_client(EmbeddingProviderType.UNSUPPORTED_PROVIDER)


@pytest.mark.asyncio
async def test_get_llama_model():
    """Test Llama model initialization."""
    # arrange
    model_path = "path/to/model.gguf"

    with patch("src.llm.llm.Llama") as mock_llama:
        # act
        get_llama_model(model_path)

        # assert
        mock_llama.assert_called_once_with(
            model_path=model_path,
            embedding=True,
            n_ctx=2048,
            pooling_type=settings.EMBEDDING_POOLING_TYPE,
        )
