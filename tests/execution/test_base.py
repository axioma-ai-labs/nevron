"""Tests for the base execution module."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.context.context import ActionContext, ContextManager
from src.core.defs import AgentAction, AgentState
from src.core.exceptions import ExecutionError
from src.execution.base import ActionExecutor, ExecutionModuleBase


class TestActionExecutor:
    """Tests for the ActionExecutor base class."""

    class DummyExecutor(ActionExecutor):
        """Dummy implementation for testing."""

        def _initialize_client(self):
            return MagicMock()

        def get_required_context(self):
            return ["test_field"]

        async def execute(self, context):
            return True, "Success"

    def test_validate_context_success(self):
        """Test context validation with valid context."""
        executor = self.DummyExecutor()
        context = {"test_field": "value"}
        assert executor.validate_context(context) is True

    def test_validate_context_failure(self):
        """Test context validation with invalid context."""
        executor = self.DummyExecutor()
        context = {"wrong_field": "value"}
        assert executor.validate_context(context) is False

    def test_get_required_context(self):
        """Test getting required context fields."""
        executor = self.DummyExecutor()
        assert executor.get_required_context() == ["test_field"]


class TestExecutionModuleBase:
    """Tests for the ExecutionModuleBase class."""

    @pytest.fixture
    def context_manager(self):
        """Create a mocked context manager."""
        cm = MagicMock(spec=ContextManager)
        context = MagicMock()

        # Set up recent actions for context testing
        action1 = ActionContext(
            action=AgentAction.IDLE, state=AgentState.IDLE, metadata={"test_field": "value1"}
        )
        action2 = ActionContext(
            action=AgentAction.CHECK_SIGNAL,
            state=AgentState.DEFAULT,
            metadata={"another_field": "value2"},
        )

        context.get_recent_actions.return_value = [action1, action2]
        cm.get_context.return_value = context
        return cm

    @pytest.fixture
    def execution_module(self, context_manager):
        """Create a test execution module."""
        module = ExecutionModuleBase(context_manager)

        # Create mock executor class
        mock_executor = MagicMock(spec=ActionExecutor)
        mock_executor_instance = mock_executor.return_value
        mock_executor_instance.get_required_context.return_value = ["test_field"]
        mock_executor_instance.validate_context.return_value = True
        mock_executor_instance.execute = AsyncMock(return_value=(True, "Success"))

        # Register mock executor
        module._executors = {AgentAction.IDLE: mock_executor}

        return module

    def test_get_required_context(self, execution_module):
        """Test getting required context from action history."""
        context = execution_module._get_required_context(AgentAction.IDLE)
        assert context == {"test_field": "value1"}

    def test_get_required_context_missing_executor(self, execution_module):
        """Test error when executor is not found."""
        with pytest.raises(ExecutionError, match="No executor found for action"):
            execution_module._get_required_context(AgentAction.POST_TWEET)

    @pytest.mark.asyncio
    async def test_execute_action_success(self, execution_module):
        """Test successful action execution."""
        success, outcome = await execution_module.execute_action(AgentAction.IDLE)
        assert success is True
        assert outcome == "Success"

    @pytest.mark.asyncio
    async def test_execute_action_missing_executor(self, execution_module):
        """Test execution with missing executor."""
        success, outcome = await execution_module.execute_action(AgentAction.POST_TWEET)
        assert success is False
        assert "No executor found for action" in outcome

    @pytest.mark.asyncio
    async def test_execute_action_invalid_context(self, execution_module):
        """Test execution with invalid context."""
        # Override validate_context to return False
        executor_cls = execution_module._executors[AgentAction.IDLE]
        executor_cls.return_value.validate_context.return_value = False

        success, outcome = await execution_module.execute_action(AgentAction.IDLE)
        assert success is False
        assert "Missing required context" in outcome

    @pytest.mark.asyncio
    async def test_execute_action_exception(self, execution_module):
        """Test execution with exception."""
        # Set execute to raise an exception
        executor_cls = execution_module._executors[AgentAction.IDLE]
        executor_cls.return_value.execute = AsyncMock(side_effect=Exception("Test error"))

        success, outcome = await execution_module.execute_action(AgentAction.IDLE)
        assert success is False
        assert "Test error" in outcome
