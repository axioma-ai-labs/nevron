from unittest.mock import MagicMock, patch

import pytest

from src.core.config import settings
from src.core.exceptions import LLMError
from src.llm.providers.venice import call_venice


def test_call_venice_success():
    """Test a successful call to Venice AI."""
    # Mock the response data
    mock_response_data = {
        "id": "1234567890",
        "object": "chat.completion",
        "created": 1716460800,
        "model": "qwen-2.5-vl",
        "choices": [{"message": {"content": "This is a mock response from Venice AI."}}],
    }

    # Mock the requests response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_response_data

    # Patch the requests.post to return our mock response
    with patch("requests.post", return_value=mock_response) as mock_post:
        messages = [{"role": "user", "content": "Test message"}]
        result = call_venice(messages, model="claude-3-sonnet-20240229")

        assert result == "This is a mock response from Venice AI."

        # Verify the url is valid
        call_args = mock_post.call_args
        url = call_args[0][0]
        assert url == f"{settings.VENICE_API_BASE_URL}/chat/completions"


def test_call_venice_http_error():
    """Test when Venice AI API returns an HTTP error."""
    # Mock the requests response with an error status
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad request"

    # Patch requests.post to return our mock response
    with patch("requests.post", return_value=mock_response):
        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(LLMError, match="Venice API returned status 400"):
            call_venice(messages)


def test_call_venice_empty_response():
    """Test when Venice AI returns an empty response."""
    # Case 1: No choices in the response
    mock_response_no_choices = MagicMock()
    mock_response_no_choices.status_code = 200
    mock_response_no_choices.json.return_value = {"choices": []}
    mock_response_no_choices.text = "Empty response"

    with patch("requests.post", return_value=mock_response_no_choices):
        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(LLMError, match="Venice AI returned empty response"):
            call_venice(messages)

    # Case 2: No content in the message
    mock_response_no_content = MagicMock()
    mock_response_no_content.status_code = 200
    mock_response_no_content.json.return_value = {"choices": [{"message": {"content": ""}}]}
    mock_response_no_content.text = "Empty content"

    with patch("requests.post", return_value=mock_response_no_content):
        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(LLMError, match="Venice AI returned empty response"):
            call_venice(messages)

    # Case 3: Missing message field
    mock_response_no_message = MagicMock()
    mock_response_no_message.status_code = 200
    mock_response_no_message.json.return_value = {"choices": [{"something_else": "value"}]}
    mock_response_no_message.text = "No message field"

    with patch("requests.post", return_value=mock_response_no_message):
        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(LLMError, match="Venice AI returned empty response"):
            call_venice(messages)


def test_call_venice_exception():
    """Test when Venice AI raises an exception."""
    # Mock requests.post to raise an exception
    with patch("requests.post", side_effect=Exception("API call failed")):
        messages = [{"role": "user", "content": "Test message"}]

        with pytest.raises(LLMError, match="Venice AI API call failed"):
            call_venice(messages)
