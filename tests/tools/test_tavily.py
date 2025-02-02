# from unittest.mock import Mock, patch

# import httpx
# import pytest
# from tavily import AsyncTavilyClient

# from src.tools.tavily import execute_search, initialize_tavily_client, parse_search_results


# @pytest.fixture
# def mock_tavily_client():
#     """Fixture to create a mock Tavily client"""
#     client = Mock(spec=AsyncTavilyClient)
#     return client


# @pytest.mark.asyncio
# async def test_initialize_tavily_client():
#     """Test client initialization with API key"""
#     api_key = "test_api_key"

#     with patch("src.tools.tavily.AsyncTavilyClient") as mock_client:
#         client = await initialize_tavily_client(api_key)

#         # Verify client was created with correct API key
#         mock_client.assert_called_once_with(api_key=api_key)

#         # Verify custom client creator was set
#         http_client = client._client_creator()
#         assert isinstance(http_client, httpx.AsyncClient)
#         assert http_client.base_url == "https://api.tavily.com"
#         assert http_client.timeout == httpx.Timeout(timeout=180.0)


# @pytest.mark.asyncio
# async def test_execute_search(mock_tavily_client):
#     """Test search execution with various parameters"""
#     query = "test query"
#     filters = {"search_depth": "advanced", "include_domains": ["example.com"], "max_results": 5}

#     expected_results = {"results": [{"title": "Test Result", "url": "https://example.com"}]}

#     mock_tavily_client.search.return_value = expected_results

#     # Test search with filters
#     results = await execute_search(mock_tavily_client, query, filters)
#     mock_tavily_client.search.assert_called_with(
#         query=query, search_depth="advanced", include_domains=["example.com"], max_results=5
#     )
#     assert results == expected_results

#     # Test search without filters
#     await execute_search(mock_tavily_client, query)
#     mock_tavily_client.search.assert_called_with(query=query)


# def test_parse_search_results():
#     """Test parsing of search results with various data structures"""
#     # Test complete result structure
#     complete_results = {
#         "results": [
#             {
#                 "title": "Test Title",
#                 "url": "https://example.com",
#                 "content": "Test content",
#                 "score": 0.95,
#                 "published_date": "2024-03-20",
#             }
#         ]
#     }

#     parsed = parse_search_results(complete_results)
#     assert len(parsed) == 1
#     assert parsed[0] == {
#         "title": "Test Title",
#         "url": "https://example.com",
#         "content": "Test content",
#         "score": 0.95,
#         "published_date": "2024-03-20",
#     }

#     # Test partial result structure (missing optional fields)
#     partial_results = {
#         "results": [
#             {
#                 "title": "Test Title",
#                 "url": "https://example.com",
#                 "content": "Test content",
#                 "score": 0.95,
#             }
#         ]
#     }

#     parsed = parse_search_results(partial_results)
#     assert len(parsed) == 1
#     assert "published_date" not in parsed[0]

#     # Test empty results
#     empty_results: dict[str, list] = {"results": []}
#     parsed = parse_search_results(empty_results)
#     assert len(parsed) == 0

#     # Test missing results key
#     invalid_results: dict = {}
#     parsed = parse_search_results(invalid_results)
#     assert len(parsed) == 0
