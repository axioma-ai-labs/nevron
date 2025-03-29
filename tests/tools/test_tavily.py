from unittest.mock import AsyncMock, patch

import httpx
import pytest
from tavily import AsyncTavilyClient

from src.tools.tavily import TavilyTool


@pytest.fixture
def tavily_tool():
    """Fixture to create a TavilyTool instance."""
    return TavilyTool()


@pytest.fixture
def mock_tavily_client():
    """Fixture to create a mock Tavily client."""
    return AsyncMock(spec=AsyncTavilyClient)


@pytest.mark.asyncio
async def test_initialize_success(tavily_tool, mock_tavily_client):
    """Test successful initialization of Tavily client."""
    with patch("src.tools.tavily.AsyncTavilyClient", return_value=mock_tavily_client):
        test_api_key = "test_api_key"

        # Initialize with test API key
        await tavily_tool.initialize(api_key=test_api_key)

        assert tavily_tool.client is not None
        assert isinstance(tavily_tool.client, AsyncTavilyClient)


@pytest.mark.asyncio
async def test_initialize_failure(tavily_tool):
    """Test initialization failure with missing API key."""
    with patch("src.tools.tavily.settings.TAVILY_API_KEY", ""):
        with pytest.raises(ValueError, match="Tavily API key is required"):
            await tavily_tool.initialize()


@pytest.mark.asyncio
async def test_search_success(tavily_tool, mock_tavily_client):
    """Test successful search execution."""
    query = "test query"
    filters = {"search_depth": "advanced", "max_results": 5}
    expected_results = {"results": [{"title": "Test Result"}]}
    test_api_key = "test_api_key"

    with patch(
        "src.tools.tavily.AsyncTavilyClient", return_value=mock_tavily_client
    ) as mock_client_init:
        mock_tavily_client.search.return_value = expected_results

        # Initialize with test API key
        await tavily_tool.initialize(api_key=test_api_key)

        # Verify client was initialized with correct API key
        mock_client_init.assert_called_once_with(api_key=test_api_key)

        # Test search
        results = await tavily_tool.search(query, filters)

        assert results == expected_results
        mock_tavily_client.search.assert_called_with(
            query=query, search_depth="advanced", max_results=5
        )


@pytest.mark.asyncio
async def test_search_uninitialized(tavily_tool):
    """Test search when client is not initialized."""
    with pytest.raises(ValueError, match="Tavily client not initialized"):
        await tavily_tool.search("test query")


@pytest.mark.asyncio
async def test_close(tavily_tool, mock_tavily_client):
    """Test closing the Tavily client."""
    with patch("src.tools.tavily.AsyncTavilyClient", return_value=mock_tavily_client):
        # Create a mock for the underlying httpx client
        mock_http_client = AsyncMock(spec=httpx.AsyncClient)
        mock_tavily_client._client = mock_http_client

        test_api_key = "test_api_key"

        # Initialize with test API key
        await tavily_tool.initialize(api_key=test_api_key)

        # Close the client
        await tavily_tool.close()

        # Verify client is cleared
        assert tavily_tool.client is None

        # Verify the underlying client was closed
        mock_http_client.aclose.assert_called_once()


def test_parse_results(tavily_tool):
    """Test parsing of search results."""
    # Test complete result structure
    complete_results = {
        "results": [
            {
                "title": "Test Title",
                "url": "https://example.com",
                "content": "Test content",
                "score": 0.95,
                "published_date": "2024-03-20",
            }
        ]
    }

    parsed = tavily_tool.parse_results(complete_results)
    assert len(parsed) == 1
    assert parsed[0] == {
        "title": "Test Title",
        "url": "https://example.com",
        "content": "Test content",
        "score": 0.95,
        "published_date": "2024-03-20",
    }

    # Test empty results
    empty_results: dict[str, list] = {"results": []}
    parsed = tavily_tool.parse_results(empty_results)
    assert len(parsed) == 0
