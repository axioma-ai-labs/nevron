# from unittest.mock import AsyncMock, patch

# import httpx
# import pytest

# from src.core.exceptions import APIError
# from src.tools.perplexity import estimate_perplexity_cost_per_request, search_with_perplexity


# @pytest.fixture
# def mock_settings(monkeypatch):
#     """Fixture to mock settings for the tests."""
#     monkeypatch.setattr("src.tools.perplexity.settings.PERPLEXITY_API_KEY", "mock-api-key")
#     monkeypatch.setattr(
#         "src.tools.perplexity.settings.PERPLEXITY_ENDPOINT", "https://mock.endpoint"
#     )
#     monkeypatch.setattr(
#         "src.tools.perplexity.settings.PERPLEXITY_NEWS_CATEGORY_LIST",
#         ["crypto", "technology", "finance"],
#     )


# @pytest.mark.asyncio
# async def test_search_with_perplexity_success(mock_settings):
#     """Test a successful Perplexity search."""
#     # Arrange
#     mock_response_data = {
#         "choices": [{"message": {"content": "Mock Perplexity result"}}],
#         "usage": {"total_tokens": 1000},
#     }
#     with patch("src.tools.perplexity.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
#         mock_post.return_value.json.return_value = mock_response_data
#         mock_post.return_value.status_code = 200

#         # Act
#         result = await search_with_perplexity("Latest cryptocurrency news")

#     # Assert
#     assert "Perplexity search data" in result
#     mock_post.assert_called_once()
#     estimated_cost = estimate_perplexity_cost_per_request(1000)
#     assert estimated_cost == 0.0002


# @pytest.mark.skip(reason="Need to be fixed")
# @pytest.mark.asyncio
# async def test_search_with_perplexity_no_api_key():
#     """Test when Perplexity API key is not set."""
#     with patch("src.tools.perplexity.settings.PERPLEXITY_API_KEY", None):
#         with pytest.raises(APIError, match="Perplexity API key is not set"):
#             await search_with_perplexity("Latest cryptocurrency news")


# @pytest.mark.skip(reason="Need to be fixed")
# @pytest.mark.asyncio
# async def test_search_with_perplexity_no_endpoint():
#     """Test when Perplexity endpoint is not set."""
#     with patch("src.tools.perplexity.settings.PERPLEXITY_ENDPOINT", None):
#         with pytest.raises(APIError, match="Perplexity endpoint is not set"):
#             await search_with_perplexity("Latest cryptocurrency news")


# @pytest.mark.asyncio
# async def test_search_with_perplexity_timeout(mock_settings):
#     """Test handling a timeout exception during Perplexity search."""
#     with patch("src.tools.perplexity.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
#         mock_post.side_effect = httpx.TimeoutException("Request timed out")

#         # Act
#         result = await search_with_perplexity("Latest cryptocurrency news")

#     # Assert
#     assert "timeout error" in result.lower()


# @pytest.mark.asyncio
# async def test_search_with_perplexity_api_error(mock_settings):
#     """Test handling a general API error during Perplexity search."""
#     with patch("src.tools.perplexity.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
#         mock_post.side_effect = Exception("Mock API failure")

#         # Act
#         result = await search_with_perplexity("Latest cryptocurrency news")

#     # Assert
#     assert "currently unavailable" in result.lower()


# def test_estimate_perplexity_cost_per_request():
#     """Test cost estimation for Perplexity requests."""
#     # Act
#     estimated_cost = estimate_perplexity_cost_per_request(1000)

#     # Assert
#     assert estimated_cost == 0.0002  # $0.2 per 1M tokens
