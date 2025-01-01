from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import LLMError
from src.llm.providers.xai import call_xai


@pytest.mark.asyncio
async def test_call_xai_success():
    """Test a successful call to xAI."""
    # mock the message response
    mock_message = MagicMock()
    mock_message.content = "This is a mock response from xAI."

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    # mock the openai client
    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response

    # patch the openai client constructor
    with patch("src.llm.providers.xai.openai.AsyncOpenAI", return_value=mock_client):
        messages = [{"role": "user", "content": "Test message"}]
        result = await call_xai(messages, model="grok-2-latest", temperature=0.7)

        assert result == "This is a mock response from xAI."
        mock_client.chat.completions.create.assert_called_once_with(
            model="grok-2-latest",
            messages=messages,
            temperature=0.7,
        )


@pytest.mark.asyncio
async def test_call_xai_no_content():
    """Test when xAI returns no content in the response."""
    mock_message = MagicMock()
    mock_message.content = ""

    mock_choice = MagicMock()
    mock_choice.message = mock_message

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = AsyncMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch("src.llm.providers.xai.openai.AsyncOpenAI", return_value=mock_client):
        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(LLMError):
            await call_xai(messages)


@pytest.mark.asyncio
async def test_call_xai_exception():
    """Test when xAI raises an exception."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create.side_effect = Exception("API call failed")

    with patch("src.llm.providers.xai.openai.AsyncOpenAI", return_value=mock_client):
        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(LLMError, match="Error during xAI API call"):
            await call_xai(messages)
