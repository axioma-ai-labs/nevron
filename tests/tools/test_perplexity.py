from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.core.exceptions import APIError
from src.tools.perplexity import PerplexityTool


@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to mock settings for the tests."""
    monkeypatch.setattr("src.tools.perplexity.settings.PERPLEXITY_API_KEY", "mock-api-key")
    monkeypatch.setattr(
        "src.tools.perplexity.settings.PERPLEXITY_ENDPOINT", "https://mock.endpoint"
    )
    monkeypatch.setattr("src.tools.perplexity.settings.PERPLEXITY_MODEL", "mock-model")
    monkeypatch.setattr(
        "src.tools.perplexity.settings.PERPLEXITY_NEWS_CATEGORY_LIST",
        ["crypto", "technology", "finance"],
    )


@pytest.fixture
def perplexity_tool(mock_settings):
    """Fixture to create a PerplexityTool instance."""
    return PerplexityTool()


@pytest.mark.asyncio
async def test_initialization_success(perplexity_tool):
    """Test successful initialization of PerplexityTool."""
    assert perplexity_tool is not None
    assert perplexity_tool.client is not None
    assert perplexity_tool.headers == {
        "Authorization": "Bearer mock-api-key",
        "Content-Type": "application/json",
    }


@pytest.mark.asyncio
async def test_initialization_failure():
    """Test initialization failure with missing API key."""
    with patch("src.tools.perplexity.settings.PERPLEXITY_API_KEY", None):
        with pytest.raises(APIError, match="Perplexity API key is not set"):
            PerplexityTool()


@pytest.mark.asyncio
async def test_search_success(perplexity_tool):
    """Test a successful Perplexity search."""
    # Define the mock response data
    mock_response_data = {
        "choices": [{"message": {"content": "Perplexity search data"}}],
        "usage": {"total_tokens": 1000},
    }

    # Instead of patching the client, let's directly patch the post method
    with patch.object(perplexity_tool.client, "post", autospec=True) as mock_post:
        # Configure the mock to return a proper response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_post.return_value = mock_response

        # Call the method
        result = await perplexity_tool.search("Latest cryptocurrency news")

        assert "Perplexity search data" in result

        # Verify the post was called with correct parameters
        mock_post.assert_called_once()


@pytest.mark.asyncio
async def test_search_timeout(perplexity_tool):
    """Test handling a timeout exception during Perplexity search."""
    with patch.object(perplexity_tool.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Request timed out")
        result = await perplexity_tool.search("Latest cryptocurrency news")
        assert "timeout error" in result.lower()
        # assert "content" in result
        # mock_client.post.assert_called_once_with(
        #     "https://mock.endpoint",
        #     json={
        #         "model": "mock-model",
        #         "messages": [
        #             {
        #                 "role": "system",
        #                 "content": (
        #                     "You are a capable and efficient search assistant. "
        #                     "Your job is to find relevant and concise information about "
        #                     "cryptocurrencies based on the query provided."
        #                     "Validate the results for relevance and clarity. "
        #                     "Return the results ONLY in the following string - dictionary format "
        #                     "(include curly brackets): "
        #                     '{ "headline": "all news texts here ", "category": "choose relevant news '
        #                     "category from ['crypto', 'technology', 'finance'] \", \"timestamp\": "
        #                     '"dd-mm-yyyy" }'
        #                 ),
        #             },
        #             {
        #                 "role": "user",
        #                 "content": "Latest cryptocurrency news",
        #             },
        #         ],
        #         "temperature": 0.3,
        #         "top_p": 0.8,
        #         "search_domain_filter": ["perplexity.ai"],
        #         "return_images": False,
        #         "return_related_questions": False,
        #         "stream": False,
        #     },
        #     headers={"Authorization": "Bearer mock-api-key", "Content-Type": "application/json"},
        # )


@pytest.mark.asyncio
async def test_search_api_error(perplexity_tool):
    """Test handling a general API error during Perplexity search."""
    with patch.object(perplexity_tool.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = Exception("Mock API failure")
        result = await perplexity_tool.search("Latest cryptocurrency news")
        assert "currently unavailable" in result.lower()


@pytest.mark.asyncio
async def test_close(perplexity_tool):
    """Test closing the Perplexity client."""
    with patch.object(perplexity_tool.client, "aclose", new_callable=AsyncMock) as mock_close:
        await perplexity_tool.close()
        mock_close.assert_called_once()


def test_estimate_cost(perplexity_tool):
    """Test cost estimation for Perplexity requests."""
    # Test with 1000 tokens
    assert perplexity_tool.estimate_cost(1000) == 0.0002

    # Test with 0 tokens
    assert perplexity_tool.estimate_cost(0) == 0.0

    # Test with 1,000,000 tokens
    assert perplexity_tool.estimate_cost(1_000_000) == 0.2
