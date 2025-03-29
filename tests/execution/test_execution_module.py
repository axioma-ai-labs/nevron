import unittest
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.context.context import ActionContext, ContextManager
from src.core.defs import AgentAction, AgentState
from src.core.exceptions import ExecutionError
from src.execution.execution_module import ACTION_EXECUTOR_MAP, ExecutionModule


class TestExecutionModule(unittest.TestCase):
    def setUp(self):
        # Mock the context manager
        self.mock_context_manager = MagicMock(spec=ContextManager)
        self.execution_module = ExecutionModule(self.mock_context_manager)

    def test_init(self):
        """Test that ExecutionModule initializes with the correct executor map."""
        self.assertEqual(self.execution_module._executors, ACTION_EXECUTOR_MAP)

    def test_get_required_context_no_executor(self):
        """Test handling of non-existent executor."""
        # Fix: Use a value that's not in the AgentAction enum but is of the right type
        # We can make one with a fake value since it's an enum
        fake_action = MagicMock(spec=AgentAction)
        fake_action.value = "NONEXISTENT_ACTION"

        # Ensure ExecutionError is raised
        with self.assertRaises(ExecutionError) as context:
            self.execution_module._get_required_context(fake_action)

        # Fix: Convert exception message to string before using assertIn
        self.assertIn("No executor found for action", str(context.exception))

    def test_get_required_context_no_requirements(self):
        """Test retrieving context when executor has no requirements."""
        # Mock an executor class with no requirements
        mock_executor = MagicMock()
        mock_executor.return_value.get_required_context.return_value = []

        # Patch the executor map
        with patch.dict(self.execution_module._executors, {AgentAction.IDLE: mock_executor}):
            context = self.execution_module._get_required_context(AgentAction.IDLE)

            # Verify result
            self.assertEqual(context, {})
            mock_executor.return_value.get_required_context.assert_called_once()

    def test_get_required_context_with_requirements(self):
        """Test retrieving context when executor has requirements."""
        # Mock an executor with requirements
        mock_executor = MagicMock()
        mock_executor.return_value.get_required_context.return_value = ["query", "max_results"]

        # Create mock action contexts
        mock_action_contexts: List[ActionContext] = [  # Add type annotation
            ActionContext(
                action=AgentAction.SEARCH_YOUTUBE_VIDEO,
                state=AgentState.WAITING_FOR_NEWS,
                metadata={"query": "test query", "max_results": 5},
            ),
            ActionContext(action=AgentAction.IDLE, state=AgentState.IDLE, metadata={}),
        ]

        # Configure mock context manager
        mock_context = MagicMock()
        mock_context.get_recent_actions.return_value = mock_action_contexts
        self.mock_context_manager.get_context.return_value = mock_context

        # Patch the executor map
        with patch.dict(
            self.execution_module._executors, {AgentAction.SEARCH_YOUTUBE_VIDEO: mock_executor}
        ):
            context = self.execution_module._get_required_context(AgentAction.SEARCH_YOUTUBE_VIDEO)

            # Verify result
            self.assertEqual(context, {"query": "test query", "max_results": 5})
            mock_executor.return_value.get_required_context.assert_called_once()
            mock_context.get_recent_actions.assert_called_once_with(n=5)

    def test_get_required_context_partial_match(self):
        """Test retrieving context when only some requirements are found."""
        # Mock an executor with requirements
        mock_executor = MagicMock()
        mock_executor.return_value.get_required_context.return_value = [
            "query",
            "max_results",
            "filter",
        ]

        # Create mock action contexts
        mock_action_contexts: List[ActionContext] = [  # Add type annotation
            ActionContext(
                action=AgentAction.SEARCH_YOUTUBE_VIDEO,
                state=AgentState.WAITING_FOR_NEWS,
                metadata={"query": "test query"},  # Missing max_results and filter
            )
        ]

        # Configure mock context manager
        mock_context = MagicMock()
        mock_context.get_recent_actions.return_value = mock_action_contexts
        self.mock_context_manager.get_context.return_value = mock_context

        # Patch the executor map
        with patch.dict(
            self.execution_module._executors, {AgentAction.SEARCH_YOUTUBE_VIDEO: mock_executor}
        ):
            context = self.execution_module._get_required_context(AgentAction.SEARCH_YOUTUBE_VIDEO)

            # Verify result - should only contain what was found
            self.assertEqual(context, {"query": "test query"})
            mock_executor.return_value.get_required_context.assert_called_once()

    def test_get_required_context_multiple_actions(self):
        """Test retrieving context from multiple previous actions."""
        # Mock an executor with requirements
        mock_executor = MagicMock()
        mock_executor.return_value.get_required_context.return_value = ["query", "max_results"]

        # Create mock action contexts with different fields
        mock_action_contexts: List[ActionContext] = [  # Add type annotation
            ActionContext(  # Most recent
                action=AgentAction.IDLE, state=AgentState.IDLE, metadata={"irrelevant": "data"}
            ),
            ActionContext(  # Second most recent
                action=AgentAction.SEARCH_YOUTUBE_VIDEO,
                state=AgentState.WAITING_FOR_NEWS,
                metadata={"query": "test query"},
            ),
            ActionContext(  # Third most recent
                action=AgentAction.SEARCH_TAVILY,
                state=AgentState.WAITING_FOR_NEWS,
                metadata={"max_results": 5},
            ),
        ]

        # Configure mock context manager
        mock_context = MagicMock()
        mock_context.get_recent_actions.return_value = mock_action_contexts
        self.mock_context_manager.get_context.return_value = mock_context

        # Patch the executor map
        with patch.dict(
            self.execution_module._executors, {AgentAction.SEARCH_YOUTUBE_VIDEO: mock_executor}
        ):
            context = self.execution_module._get_required_context(AgentAction.SEARCH_YOUTUBE_VIDEO)

            # Verify result - should contain fields from both relevant actions
            self.assertEqual(context, {"query": "test query", "max_results": 5})
            mock_executor.return_value.get_required_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_action_success(self):
        """Test successful action execution."""
        # Mock an executor that succeeds
        mock_executor = MagicMock()
        mock_executor.return_value.get_required_context.return_value = ["query"]
        mock_executor.return_value.execute = AsyncMock(return_value=(True, "Action succeeded"))

        # Configure mock context manager with needed context
        mock_action_contexts: List[ActionContext] = [  # Add type annotation
            ActionContext(
                action=AgentAction.SEARCH_YOUTUBE_VIDEO,
                state=AgentState.WAITING_FOR_NEWS,
                metadata={"query": "test query"},
            )
        ]
        mock_context = MagicMock()
        mock_context.get_recent_actions.return_value = mock_action_contexts
        self.mock_context_manager.get_context.return_value = mock_context

        # Patch the executor map
        with patch.dict(
            self.execution_module._executors, {AgentAction.SEARCH_YOUTUBE_VIDEO: mock_executor}
        ):
            success, outcome = await self.execution_module.execute_action(
                AgentAction.SEARCH_YOUTUBE_VIDEO
            )

            # Verify result
            self.assertTrue(success)
            self.assertEqual(outcome, "Action succeeded")
            mock_executor.return_value.execute.assert_called_once_with({"query": "test query"})

    @pytest.mark.asyncio
    async def test_execute_action_failure(self):
        """Test action execution that fails but doesn't raise an exception."""
        # Mock an executor that fails
        mock_executor = MagicMock()
        mock_executor.return_value.get_required_context.return_value = ["query"]
        mock_executor.return_value.execute = AsyncMock(return_value=(False, "Action failed"))

        # Configure mock context manager with needed context
        mock_action_contexts: List[ActionContext] = [  # Add type annotation
            ActionContext(
                action=AgentAction.SEARCH_YOUTUBE_VIDEO,
                state=AgentState.WAITING_FOR_NEWS,
                metadata={"query": "test query"},
            )
        ]
        mock_context = MagicMock()
        mock_context.get_recent_actions.return_value = mock_action_contexts
        self.mock_context_manager.get_context.return_value = mock_context

        # Patch the executor map
        with patch.dict(
            self.execution_module._executors, {AgentAction.SEARCH_YOUTUBE_VIDEO: mock_executor}
        ):
            success, outcome = await self.execution_module.execute_action(
                AgentAction.SEARCH_YOUTUBE_VIDEO
            )

            # Verify result
            self.assertFalse(success)
            self.assertEqual(outcome, "Action failed")
            mock_executor.return_value.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_action_exception(self):
        """Test action execution that raises an exception."""
        # Mock an executor that raises an exception
        mock_executor = MagicMock()
        mock_executor.return_value.get_required_context.return_value = []
        error_message: str = "Execution error"  # Add type annotation
        mock_executor.return_value.execute = AsyncMock(side_effect=Exception(error_message))

        # Patch the executor map
        with patch.dict(self.execution_module._executors, {AgentAction.IDLE: mock_executor}):
            success, outcome = await self.execution_module.execute_action(AgentAction.IDLE)

            # Verify result
            self.assertFalse(success)
            self.assertEqual(outcome, "Execution error")
            mock_executor.return_value.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_action_no_executor(self):
        """Test handling of non-existent executor during execution."""
        # Fix: Use a value that's not in the AgentAction enum but is of the right type
        fake_action = MagicMock(spec=AgentAction)
        fake_action.value = "NONEXISTENT_ACTION"

        # Execute the non-existent action
        success, outcome = await self.execution_module.execute_action(fake_action)

        # Verify result
        self.assertFalse(success)
        # Fix: Convert outcome to string before using assertIn
        self.assertIn("No executor found for action", str(outcome))

    @pytest.mark.asyncio
    async def test_execute_action_context_exception(self):
        """Test handling of exception during context retrieval."""
        # Mock an executor
        mock_executor = MagicMock()
        # Make get_required_context raise an exception
        error_message: str = "Context error"  # Add type annotation
        mock_executor.return_value.get_required_context = MagicMock(
            side_effect=Exception(error_message)
        )

        # Patch the executor map
        with patch.dict(self.execution_module._executors, {AgentAction.IDLE: mock_executor}):
            success, outcome = await self.execution_module.execute_action(AgentAction.IDLE)

            # Verify result
            self.assertFalse(success)
            self.assertEqual(outcome, "Context error")
            mock_executor.return_value.get_required_context.assert_called_once()
            mock_executor.return_value.execute.assert_not_called()  # Shouldn't get this far


if __name__ == "__main__":
    unittest.main()
