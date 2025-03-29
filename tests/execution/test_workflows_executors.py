import unittest
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, patch

import pytest

from src.execution.workflows_executors import AnalyzeNewsExecutor, CheckSignalExecutor, IdleExecutor


class TestAnalyzeNewsExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with mocked workflow function
        self.patcher = patch("src.execution.workflows_executors.analyze_news_workflow")
        self.mock_analyze_news = self.patcher.start()
        self.executor = AnalyzeNewsExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["news_text"])

    def test_validate_context_success(self):
        """Test context validation with valid context."""
        # Create a context with all required fields
        context = {"news_text": "Sample news text"}

        # Test validation
        result = self.executor.validate_context(context)

        # Verify result
        self.assertTrue(result)

    def test_validate_context_failure(self):
        """Test context validation with invalid context."""
        # Create a context missing required fields
        context = {"unrelated_field": "value"}

        # Test validation
        result = self.executor.validate_context(context)

        # Verify result
        self.assertFalse(result)

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful news analysis execution."""
        # Set up mock return value
        tweet_id: str = "1234567890"
        self.mock_analyze_news.return_value = AsyncMock(return_value=tweet_id)()

        # Test with valid context
        context = {"news_text": "Bitcoin surges to $50,000 amid growing institutional adoption."}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, f"News analyzed: {tweet_id}")
        self.mock_analyze_news.assert_called_once_with(news=context["news_text"])

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No news text provided in context")
        self.mock_analyze_news.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_workflow_error(self):
        """Test handling of workflow errors."""
        # Set up mock to raise Exception
        error_message: str = "Failed to process news"
        self.mock_analyze_news.return_value = AsyncMock(side_effect=Exception(error_message))()

        # Test with valid context
        context = {"news_text": "Bitcoin news article"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Failed to process news")
        self.mock_analyze_news.assert_called_once()


class TestCheckSignalExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with mocked workflow function
        self.patcher = patch("src.execution.workflows_executors.analyze_signal")
        self.mock_analyze_signal = self.patcher.start()
        self.executor = CheckSignalExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that get_required_context returns an empty list."""
        required = self.executor.get_required_context()
        self.assertEqual(required, [])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful signal check execution."""
        # Set up mock return value
        signal_result: str = "1234567890;9876543210"
        self.mock_analyze_signal.return_value = AsyncMock(return_value=signal_result)()

        # Test with empty context (no requirements)
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, f"Signal checked: {signal_result}")
        self.mock_analyze_signal.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_no_signal(self):
        """Test when no signal is found."""
        # Set up mock to return None (no signal)
        signal_result: Optional[str] = None
        self.mock_analyze_signal.return_value = AsyncMock(return_value=signal_result)()

        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Signal checked: None")
        self.mock_analyze_signal.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_workflow_error(self):
        """Test handling of workflow errors."""
        # Set up mock to raise Exception
        error_message: str = "Failed to fetch signal"
        self.mock_analyze_signal.return_value = AsyncMock(side_effect=Exception(error_message))()

        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Failed to fetch signal")
        self.mock_analyze_signal.assert_called_once()


class TestIdleExecutor(unittest.TestCase):
    def setUp(self):
        self.executor = IdleExecutor()

    def test_get_required_context(self):
        """Test that get_required_context returns an empty list."""
        required = self.executor.get_required_context()
        self.assertEqual(required, [])

    @pytest.mark.asyncio
    async def test_execute(self):
        """Test idle execution."""
        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Idle completed")


if __name__ == "__main__":
    unittest.main()
