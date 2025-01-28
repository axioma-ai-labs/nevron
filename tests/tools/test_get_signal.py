# from typing import Any, Dict
# from unittest.mock import AsyncMock, MagicMock, patch

# import pytest
# from httpx import Response
# from loguru import logger

# from src.core.exceptions import CoinstatsError
# from src.tools.get_signal import fetch_signal, get_coinstats_news


# @pytest.fixture
# def mock_tool_logger(monkeypatch):
#     """Mock logger for tool testing."""
#     mock_debug = MagicMock()
#     mock_error = MagicMock()
#     monkeypatch.setattr(logger, "debug", mock_debug)
#     monkeypatch.setattr(logger, "error", mock_error)
#     return mock_debug, mock_error


# @pytest.fixture
# def mock_httpx_client():
#     """Create a mock httpx client."""
#     mock_client = AsyncMock()
#     mock_client.get = AsyncMock()
#     return mock_client


# @pytest.mark.skip(reason="Something is wrong with mocking the Coinstats API")
# @pytest.mark.asyncio
# async def test_get_coinstats_news_success(mock_tool_logger, mock_httpx_client):
#     """Test successful news retrieval from Coinstats."""
#     # arrange:
#     mock_debug, mock_error = mock_tool_logger
#     mock_response = Response(200, json={"result": [{"title": "Test News"}]})
#     mock_httpx_client.get.return_value = mock_response

#     with patch("httpx.AsyncClient", return_value=mock_httpx_client):
#         # act:
#         result = await get_coinstats_news()

#     # assert:
#     assert result == {"result": [{"title": "Test News"}]}
#     mock_debug.assert_any_call("RETRIEVING NEWS")
#     mock_debug.assert_any_call("COINSTATS NEWS | SUCCESSFULLY RETRIEVED 1 ARTICLES")
#     mock_error.assert_not_called()

#     # Verify API call
#     mock_httpx_client.get.assert_called_once()
#     args, kwargs = mock_httpx_client.get.call_args
#     assert "openapiv1.coinstats.app/news" in args[0]
#     assert kwargs["headers"]["accept"] == "application/json"


# @pytest.mark.asyncio
# async def test_get_coinstats_news_http_error(mock_tool_logger, mock_httpx_client):
#     """Test error handling when Coinstats API returns an error."""
#     # arrange:
#     mock_debug, mock_error = mock_tool_logger
#     mock_response = MagicMock(spec=Response)
#     mock_response.status_code = 500
#     mock_response.raise_for_status.side_effect = Exception("HTTP Error")
#     mock_httpx_client.get.return_value = mock_response

#     with (
#         patch("httpx.AsyncClient", return_value=mock_httpx_client),
#         pytest.raises(CoinstatsError) as exc_info,
#     ):
#         # act:
#         await get_coinstats_news()

#     # assert:
#     assert str(exc_info.value) == "News data currently unavailable"
#     mock_debug.assert_called_once_with("RETRIEVING NEWS")
#     mock_error.assert_called_once()
#     assert "ERROR RETRIEVING NEWS" in mock_error.call_args[0][0]


# @pytest.mark.asyncio
# async def test_fetch_signal_success(mock_tool_logger):
#     """Test successful signal fetching."""
#     # arrange:
#     mock_debug, mock_error = mock_tool_logger
#     news_data = {"result": [{"title": "Bitcoin reaches new high"}]}

#     with patch("src.tools.get_signal.get_coinstats_news", return_value=news_data):
#         # act:
#         result = await fetch_signal()

#     # assert:
#     assert result == {"status": "new_signal", "content": "Bitcoin reaches new high"}
#     mock_debug.assert_any_call("Signal fetched: {'title': 'Bitcoin reaches new high'}")
#     mock_error.assert_not_called()


# @pytest.mark.asyncio
# async def test_fetch_signal_no_news(mock_tool_logger):
#     """Test signal fetching when no news is available."""
#     # arrange:
#     mock_debug, mock_error = mock_tool_logger
#     news_data: Dict[str, Any] = {"result": []}
#     mock_get_news = AsyncMock(return_value=news_data)

#     with patch("src.tools.get_signal.get_coinstats_news", new=mock_get_news):
#         # act:
#         result = await fetch_signal()

#     # assert:
#     assert result == {"status": "no_data"}
#     mock_error.assert_called_once_with("No news data available in the response")


# @pytest.mark.asyncio
# async def test_fetch_signal_no_title(mock_tool_logger):
#     """Test signal fetching when news item has no title."""
#     # arrange:
#     mock_debug, mock_error = mock_tool_logger
#     news_data = {"result": [{"content": "Some content but no title"}]}

#     with patch("src.tools.get_signal.get_coinstats_news", return_value=news_data):
#         # act:
#         result = await fetch_signal()

#     # assert:
#     assert result == {"status": "no_data"}


# @pytest.mark.asyncio
# async def test_fetch_signal_api_error(mock_tool_logger):
#     """Test signal fetching when API call fails."""
#     # arrange:
#     mock_debug, mock_error = mock_tool_logger

#     with patch("src.tools.get_signal.get_coinstats_news", side_effect=CoinstatsError("Test error")):
#         # act:
#         result = await fetch_signal()

#     # assert:
#     assert result == {"status": "error"}
#     mock_error.assert_called_once_with("Error fetching signal from Coinstats: Test error")
