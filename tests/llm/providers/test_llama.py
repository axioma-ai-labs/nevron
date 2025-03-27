from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import settings
from src.core.defs import LlamaProviderType
from src.core.exceptions import LLMError
from src.llm.providers.llama import (
    _call_fireworks,
    _call_llama_api,
    _call_ollama,
    _call_openrouter,
    _format_messages_for_ollama,
    call_llama,
)


@pytest.fixture
def mock_messages():
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"},
    ]


@pytest.mark.asyncio
async def test_format_messages_for_ollama():
    messages = [
        {"role": "system", "content": "System message"},
        {"role": "user", "content": "User message"},
        {"role": "assistant", "content": "Assistant message"},
    ]
    expected = "System: System message\nUser: User message\nAssistant: Assistant message"
    assert _format_messages_for_ollama(messages) == expected


@pytest.mark.asyncio
async def test_call_fireworks_success(mock_messages):
    mock_response = MagicMock()
    mock_response.json.return_value = {"choices": [{"message": {"content": "Paris"}}]}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response):
        result = await _call_fireworks(mock_messages)
        assert result == "Paris"


@pytest.mark.asyncio
async def test_call_fireworks_failure(mock_messages):
    with patch("requests.post", side_effect=Exception("API Error")):
        with pytest.raises(LLMError):
            await _call_fireworks(mock_messages)


@pytest.mark.asyncio
async def test_call_ollama_success(mock_messages):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": "Paris"}
    mock_response.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_response):
        result = await _call_ollama(mock_messages)
        assert result == "Paris"


@pytest.mark.asyncio
async def test_call_ollama_failure(mock_messages):
    with patch("requests.post", side_effect=Exception("API Error")):
        with pytest.raises(LLMError):
            await _call_ollama(mock_messages)


@pytest.mark.asyncio
async def test_call_llama_api_success(mock_messages):
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Paris"))]
    mock_client.chat.completions.create.return_value = mock_response

    with patch("src.llm.providers.llama.AsyncOpenAI", return_value=mock_client):
        result = await _call_llama_api(mock_messages)
        assert result == "Paris"


@pytest.mark.asyncio
async def test_call_llama_api_failure(mock_messages):
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")

    with patch("src.llm.providers.llama.AsyncOpenAI", return_value=mock_client):
        with pytest.raises(LLMError):
            await _call_llama_api(mock_messages)


@pytest.mark.asyncio
async def test_call_openrouter_success(mock_messages):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Paris"))]
    mock_client.chat.completions.create.return_value = mock_response

    with patch("src.llm.providers.llama.OpenAI", return_value=mock_client):
        result = await _call_openrouter(mock_messages)
        assert result == "Paris"


@pytest.mark.asyncio
async def test_call_openrouter_failure(mock_messages):
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API Error")

    with patch("src.llm.providers.llama.OpenAI", return_value=mock_client):
        with pytest.raises(LLMError):
            await _call_openrouter(mock_messages)


@pytest.mark.asyncio
async def test_call_llama_success(mock_messages):
    with patch("src.llm.providers.llama._call_fireworks", return_value="Paris") as mock_call:
        settings.LLAMA_PROVIDER = LlamaProviderType.FIREWORKS
        result = await call_llama(mock_messages)
        assert result == "Paris"
        mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_call_llama_unsupported_provider(mock_messages):
    with patch("src.llm.providers.llama.settings") as mock_settings:
        # Set a provider type that doesn't exist in the provider_map
        mock_settings.LLAMA_PROVIDER = (
            LlamaProviderType.LLAMA_LOCAL
        )  # This provider isn't in the provider_map

        with pytest.raises(LLMError):
            await call_llama(mock_messages)
