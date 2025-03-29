from unittest.mock import MagicMock, patch

import pytest
import requests
from loguru import logger

from src.tools.link_parser import LinkParserTool


@pytest.fixture
def mock_tool_logger(monkeypatch):
    """Mock logger for tool testing."""
    mock_debug = MagicMock()
    mock_error = MagicMock()
    monkeypatch.setattr(logger, "debug", mock_debug)
    monkeypatch.setattr(logger, "error", mock_error)
    return mock_debug, mock_error


@pytest.fixture
def link_parser():
    return LinkParserTool()


def test_parse_link_success(link_parser, mock_tool_logger):
    """Test successful link parsing with valid response"""
    mock_debug, mock_error = mock_tool_logger
    mock_response = {
        "data": {
            "url": "https://example.com",
            "title": "Test Page",
            "description": "Test Description",
            "content": "Test Content",
            "images": "image.jpg",
            "publishedTime": "2023-01-01",
            "usage": {"tokens": 100},
        }
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value=mock_response)
        )
        result = link_parser.parse_link("https://example.com")

    assert result == {
        "url": "https://example.com",
        "title": "Test Page",
        "description": "Test Description",
        "content": "Test Content",
        "images": "image.jpg",
        "timestamp": "2023-01-01",
        "tokens": 100,
    }
    mock_debug.assert_called_once_with(
        "Fetching content from: https://r.jina.ai/https://example.com"
    )
    mock_error.assert_not_called()


def test_parse_link_invalid_url(link_parser, mock_tool_logger):
    """Test parsing with invalid URL format"""
    mock_debug, mock_error = mock_tool_logger

    with pytest.raises(ValueError) as exc_info:
        link_parser.parse_link("example.com")

    assert "URL must start with http(s)://" in str(exc_info.value)


def test_parse_link_http_error(link_parser, mock_tool_logger):
    """Test handling of HTTP errors"""
    mock_debug, mock_error = mock_tool_logger

    with patch("requests.get") as mock_get:
        mock_get.side_effect = requests.exceptions.HTTPError("404 Not Found")

        with pytest.raises(requests.exceptions.HTTPError):
            link_parser.parse_link("https://example.com")

    mock_error.assert_called_once_with("Error while fetching https://example.com: 404 Not Found")


def test_parse_link_invalid_json(link_parser, mock_tool_logger):
    """Test handling of invalid JSON response"""
    mock_debug, mock_error = mock_tool_logger

    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200, json=MagicMock(side_effect=ValueError("Invalid JSON"))
        )

        with pytest.raises(ValueError) as exc_info:
            link_parser.parse_link("https://example.com")

    assert "Invalid JSON response from server" in str(exc_info.value)


def test_fetch_signal_link_success(link_parser, mock_tool_logger):
    """Test successful signal link fetching"""
    mock_debug, mock_error = mock_tool_logger

    # Test with timestamp
    with patch.object(
        link_parser,
        "fetch_signal_link",
        return_value={
            "status": "new_signal",
            "content": "Title:Test Title\nDescription:Test Description\nContent:Test Content\nTimestamp:2023-01-01\n",
        },
    ):
        result = link_parser.fetch_signal_link("https://example.com")
        assert result == {
            "status": "new_signal",
            "content": "Title:Test Title\nDescription:Test Description\nContent:Test Content\nTimestamp:2023-01-01\n",
        }

    mock_error.assert_not_called()


def test_fetch_signal_link_no_data(link_parser, mock_tool_logger):
    """Test signal link fetching with no content"""
    mock_debug, mock_error = mock_tool_logger

    # Test with empty fields including timestamp
    with patch.object(
        link_parser,
        "parse_link",
        return_value={
            "url": "https://example.com",
            "title": "",
            "description": "",
            "content": "",
            "images": {},
            "timestamp": "",
            "tokens": 0,
        },
    ):
        result = link_parser.fetch_signal_link("https://example.com")
        assert result == {"status": "no_data"}

    # Test with empty fields without timestamp
    with patch.object(
        link_parser,
        "parse_link",
        return_value={
            "url": "https://example.com",
            "title": "",
            "description": "",
            "content": "",
            "images": {},
            "tokens": 0,
        },
    ):
        result = link_parser.fetch_signal_link("https://example.com")
        assert result == {"status": "no_data"}

    mock_error.assert_not_called()


def test_search_links_success(link_parser, mock_tool_logger):
    """Test successful link search"""
    mock_debug, mock_error = mock_tool_logger
    mock_response = {
        "data": [
            {
                "url": "https://example.com",
                "title": "Test Page",
                "description": "Test Description",
                "content": "Example content",
            }
        ],
        "meta": {"usage": {"tokens": 10000}},
    }

    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value=mock_response)
        )

        # Call with basic query
        data = link_parser.search_links("test query")

        # Verify params in the first call
        args, kwargs = mock_get.call_args_list[0]
        assert kwargs["params"] == {"q": "test query"}
        assert kwargs["headers"] == link_parser.search_request_headers
        assert args[0] == "https://s.jina.ai/"

        # Reset mock and test with custom parameters
        mock_get.reset_mock()
        mock_get.return_value = MagicMock(
            status_code=200, json=MagicMock(return_value=mock_response)
        )

        # Call with custom parameters
        data = link_parser.search_links("test query", gl="US", hl="en", num=10)

        # Verify params in the second call
        args, kwargs = mock_get.call_args_list[0]
        assert kwargs["params"] == {"q": "test query", "gl": "US", "hl": "en", "num": 10}
        assert kwargs["headers"] == link_parser.search_request_headers
        assert args[0] == "https://s.jina.ai/"

    # Verify all elements in the result list
    for item in data:
        assert item == {
            "url": "https://example.com",
            "title": "Test Page",
            "description": "Test Description",
            "content": "Example content",
            "total_tokens": 10000,
        }

    # Check that debug was called (note: this will only show the last call's debug)
    mock_debug.assert_called_with(
        "Searching with URL: https://s.jina.ai/ and params: "
        + "{'q': 'test query', 'gl': 'US', 'hl': 'en', 'num': 10}"
    )
    mock_error.assert_not_called()


def test_search_links_empty_query(link_parser, mock_tool_logger):
    """Test search with empty query"""
    mock_debug, mock_error = mock_tool_logger

    with pytest.raises(ValueError) as exc_info:
        link_parser.search_links("")

    assert "Search query cannot be empty" in str(exc_info.value)
