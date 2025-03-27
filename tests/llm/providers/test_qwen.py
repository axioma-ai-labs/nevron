from unittest.mock import MagicMock, patch

import pytest

from src.core.config import settings
from src.core.exceptions import LLMError
from src.llm.providers.qwen import call_qwen


@pytest.mark.asyncio
async def test_call_qwen_success():
    """Test a successful call to Qwen."""
    mock_message = MagicMock()
    mock_message.content = "This is a mock response from Qwen."

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    # Mock the OpenAI client and its `chat.completions.create` method
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    # Patch the OpenAI client constructor to return the mock client
    with patch("src.llm.providers.qwen.OpenAI", return_value=mock_client):
        messages = [{"role": "user", "content": "Test message"}]
        result = await call_qwen(messages, model=settings.QWEN_MODEL, temperature=0.7)

        assert result == "This is a mock response from Qwen."
        mock_client.chat.completions.create.assert_called_once_with(
            model=settings.QWEN_MODEL,
            messages=messages,
            temperature=0.7,
        )


@pytest.mark.asyncio
async def test_call_qwen_no_content():
    """Test when Qwen returns no content in the response."""
    mock_message = MagicMock()
    mock_message.content = ""

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("src.llm.providers.qwen.OpenAI", return_value=mock_client):
        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(LLMError):
            await call_qwen(messages)


@pytest.mark.asyncio
async def test_call_qwen_no_choices():
    """Test when Qwen returns no choices in the response."""
    mock_response = MagicMock()
    mock_response.choices = []

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("src.llm.providers.qwen.OpenAI", return_value=mock_client):
        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(LLMError):
            await call_qwen(messages)


@pytest.mark.asyncio
async def test_call_qwen_exception():
    """Test when Qwen raises an exception."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = Exception("API call failed")

    with patch("src.llm.providers.qwen.OpenAI", return_value=mock_client):
        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(LLMError, match="Error during Qwen API call"):
            await call_qwen(messages)
