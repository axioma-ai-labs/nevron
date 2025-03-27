import unittest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import CoinstatsError, PerplexityError, TavilyError
from src.execution.research_executors import (
    CoinstatsExecutor,
    PerplexityExecutor,
    SearchTavilyExecutor,
)


class TestSearchTavilyExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Tavily client
        self.patcher = patch("src.execution.research_executors.TavilyTool")
        self.mock_tavily_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_tavily_tool.return_value = self.mock_client
        self.executor = SearchTavilyExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_initialize_client(self):
        """Test that _initialize_client returns a TavilyTool instance."""
        # Create a new instance without calling __init__
        executor = SearchTavilyExecutor.__new__(SearchTavilyExecutor)

        # Mock hasn't been called yet for this new instance
        self.mock_tavily_tool.reset_mock()

        # Call the method directly
        client = executor._initialize_client()

        # Verify the result
        self.assertEqual(client, self.mock_tavily_tool.return_value)
        self.mock_tavily_tool.assert_called_once()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["query"])

    @pytest.mark.asyncio
    async def test_execute_with_filters(self):
        """Test successful Tavily search execution with filters."""
        # Set up mock return values
        raw_results = {
            "results": [
                {
                    "title": "Test Result 1",
                    "url": "https://example.com/1",
                    "content": "Sample content 1",
                    "score": 0.95,
                }
            ]
        }
        parsed_results = [
            {
                "title": "Test Result 1",
                "url": "https://example.com/1",
                "content": "Sample content 1",
                "score": 0.95,
            }
        ]

        self.mock_client.search = AsyncMock(return_value=raw_results)
        self.mock_client.parse_results = MagicMock(return_value=parsed_results)

        # Test with filters
        context = {"query": "test query", "filters": {"time_range": "day", "domain": "example.com"}}

        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Found 1 results")
        self.mock_client.search.assert_called_once_with(
            "test query", {"time_range": "day", "domain": "example.com"}
        )
        self.mock_client.parse_results.assert_called_once_with(raw_results)

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Tavily search execution."""
        # Set up mock return values
        raw_results: Dict[str, List[Dict[str, Any]]] = {
            "results": [
                {
                    "title": "Test Result 1",
                    "url": "https://example.com/1",
                    "content": "Sample content 1",
                    "score": 0.95,
                },
                {
                    "title": "Test Result 2",
                    "url": "https://example.com/2",
                    "content": "Sample content 2",
                    "score": 0.85,
                },
            ]
        }
        parsed_results: List[Dict[str, Any]] = [
            {
                "title": "Test Result 1",
                "url": "https://example.com/1",
                "content": "Sample content 1",
                "score": 0.95,
            },
            {
                "title": "Test Result 2",
                "url": "https://example.com/2",
                "content": "Sample content 2",
                "score": 0.85,
            },
        ]

        self.mock_client.search = AsyncMock(return_value=raw_results)
        self.mock_client.parse_results = MagicMock(return_value=parsed_results)

        # Test with valid context
        context: Dict[str, Any] = {"query": "test query", "filters": {"max_results": 5}}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Found 2 results")
        self.mock_client.search.assert_called_once_with("test query", {"max_results": 5})
        self.mock_client.parse_results.assert_called_once_with(raw_results)

    @pytest.mark.asyncio
    async def test_execute_no_results(self):
        """Test when no results are found."""
        # Set up mock return values
        self.mock_client.search = AsyncMock(return_value={"results": []})
        self.mock_client.parse_results = MagicMock(return_value=[])

        # Test with valid context
        context: Dict[str, Any] = {"query": "test query", "filters": {}}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No results found")
        self.mock_client.search.assert_called_once()
        self.mock_client.parse_results.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing query
        context: Dict[str, Any] = {
            # Missing "query"
            "filters": {"max_results": 5}
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_tavily_error(self):
        """Test handling of Tavily errors."""
        # Set up mock to raise TavilyError
        error_message: str = "API rate limit exceeded"
        self.mock_client.search = AsyncMock(side_effect=TavilyError(error_message))

        # Test with valid context
        context: Dict[str, str] = {"query": "test query"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to execute Tavily search", str(message))
        self.assertIn("API rate limit exceeded", str(message))
        self.mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Connection error"
        self.mock_client.search = AsyncMock(side_effect=Exception(error_message))

        # Test with valid context
        context: Dict[str, str] = {"query": "test query"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while executing Tavily search", str(message))
        self.assertIn("Connection error", str(message))
        self.mock_client.search.assert_called_once()


class TestPerplexityExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Perplexity client
        self.patcher = patch("src.execution.research_executors.PerplexityTool")
        self.mock_perplexity_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_perplexity_tool.return_value = self.mock_client
        self.executor = PerplexityExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_initialize_client(self):
        """Test that _initialize_client returns a PerplexityTool instance."""
        # Create a new instance without calling __init__
        executor = PerplexityExecutor.__new__(PerplexityExecutor)

        # Mock hasn't been called yet for this new instance
        self.mock_perplexity_tool.reset_mock()

        # Call the method directly
        client = executor._initialize_client()

        # Verify the result
        self.assertEqual(client, self.mock_perplexity_tool.return_value)
        self.mock_perplexity_tool.assert_called_once()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["query"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Perplexity query execution."""
        # Set up mock return value
        search_results: str = 'Perplexity Search Results: { "headline": "Bitcoin price surges 10%", "category": "cryptocurrency", "timestamp": "01-01-2024" }'
        self.mock_client.search = AsyncMock(return_value=search_results)

        # Test with valid context
        context: Dict[str, str] = {"query": "latest bitcoin news"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, search_results)
        self.mock_client.search.assert_called_once_with("latest bitcoin news")

    @pytest.mark.asyncio
    async def test_execute_no_results(self):
        """Test when no results are found."""
        # Set up mock to return empty results
        self.mock_client.search = AsyncMock(return_value="")

        # Test with valid context
        context: Dict[str, str] = {"query": "nonexistent topic"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No results found from Perplexity")
        self.mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing query
        context: Dict[str, Any] = {}  # Missing "query"
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_perplexity_error(self):
        """Test handling of Perplexity errors."""
        # Set up mock to raise PerplexityError
        error_message: str = "Authentication failed"
        self.mock_client.search = AsyncMock(side_effect=PerplexityError(error_message))

        # Test with valid context
        context: Dict[str, str] = {"query": "latest bitcoin news"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to execute Perplexity query", str(message))
        self.assertIn("Authentication failed", str(message))
        self.mock_client.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Server error"
        self.mock_client.search = AsyncMock(side_effect=Exception(error_message))

        # Test with valid context
        context: Dict[str, str] = {"query": "latest bitcoin news"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while executing Perplexity query", str(message))
        self.assertIn("Server error", str(message))
        self.mock_client.search.assert_called_once()


class TestCoinstatsExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Coinstats client
        self.patcher = patch("src.execution.research_executors.CoinstatsTool")
        self.mock_coinstats_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_coinstats_tool.return_value = self.mock_client
        self.executor = CoinstatsExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_initialize_client(self):
        """Test that _initialize_client returns a CoinstatsTool instance."""
        # Create a new instance without calling __init__
        executor = CoinstatsExecutor.__new__(CoinstatsExecutor)

        # Mock hasn't been called yet for this new instance
        self.mock_coinstats_tool.reset_mock()

        # Call the method directly
        client = executor._initialize_client()

        # Verify the result
        self.assertEqual(client, self.mock_coinstats_tool.return_value)
        self.mock_coinstats_tool.assert_called_once()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, [])  # No required context for this executor

    @pytest.mark.asyncio
    async def test_execute_success_new_signal(self):
        """Test successful Coinstats signal fetch with new signal."""
        # Set up mock return value for a new signal
        signal_data: Dict[str, str] = {
            "status": "new_signal",
            "content": "Bitcoin breaks $50,000 barrier",
        }
        self.mock_client.fetch_signal = AsyncMock(return_value=signal_data)

        # Test with empty context (no requirements)
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, signal_data)
        self.mock_client.fetch_signal.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_no_data(self):
        """Test when no signal data is available."""
        # Set up mock return value for no data
        no_data_response: Dict[str, str] = {"status": "no_data"}
        self.mock_client.fetch_signal = AsyncMock(return_value=no_data_response)

        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No news found from Coinstats")
        self.mock_client.fetch_signal.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_coinstats_error(self):
        """Test handling of Coinstats errors."""
        # Set up mock to raise CoinstatsError
        error_message: str = "API connection failed"
        self.mock_client.fetch_signal = AsyncMock(side_effect=CoinstatsError(error_message))

        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to fetch from Coinstats", str(message))
        self.assertIn("API connection failed", str(message))
        self.mock_client.fetch_signal.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Unexpected network error"
        self.mock_client.fetch_signal = AsyncMock(side_effect=Exception(error_message))

        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while fetching from Coinstats", str(message))
        self.assertIn("Unexpected network error", str(message))
        self.mock_client.fetch_signal.assert_called_once()


if __name__ == "__main__":
    unittest.main()
