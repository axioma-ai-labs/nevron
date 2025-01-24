"""Base classes and utilities for action execution."""

from typing import Any, Dict, List, Optional, Tuple, Type

from loguru import logger

from src.context.context import ContextManager
from src.core.defs import AgentAction
from src.core.exceptions import ExecutionError


class ActionExecutor:
    """Base class for action executors."""

    def __init__(self):
        """Initialize the executor with its tool client."""
        self.client = self._initialize_client()

    def _initialize_client(self) -> Any:
        """Initialize the tool client. Override in subclasses."""
        raise NotImplementedError

    def get_required_context(self) -> List[str]:
        """Return list of required context fields."""
        return []

    def validate_context(self, context: Dict[str, Any]) -> bool:
        """
        Validate that all required fields are present in context.

        Args:
            context: Context data to validate

        Returns:
            bool: True if context is valid
        """
        required_fields = self.get_required_context()
        return all(field in context for field in required_fields)

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Execute the action with given context.

        Args:
            context: Dictionary with context data required for execution

        Returns:
            Tuple of (success, outcome)
        """
        raise NotImplementedError


class ExecutionModuleBase:
    """Base class for execution modules."""

    def __init__(self, context_manager: ContextManager):
        """Initialize execution module."""
        self.context_manager = context_manager
        self._executors: Dict[AgentAction, Type[ActionExecutor]] = {}

    def _get_required_context(self, action: AgentAction) -> Dict[str, Any]:
        """
        Get required context for action execution.

        Args:
            action: Action to execute

        Returns:
            Dictionary with required context data
        """
        executor_cls = self._executors.get(action)
        if not executor_cls:
            raise ExecutionError(f"No executor found for action {action}")

        executor = executor_cls()
        required_fields = executor.get_required_context()

        # Get context data from recent actions
        context_data = {}
        if required_fields:
            recent_actions = self.context_manager.get_context().get_recent_actions(n=5)
            for action_context in reversed(recent_actions):
                if action_context.metadata:
                    for field in required_fields:
                        if field in action_context.metadata and field not in context_data:
                            context_data[field] = action_context.metadata[field]

        return context_data

    async def execute_action(self, action: AgentAction) -> Tuple[bool, Optional[str]]:
        """
        Execute an action with required context.

        Args:
            action: Action to execute

        Returns:
            Tuple of (success, outcome)
        """
        try:
            # Get executor
            executor_cls = self._executors.get(action)
            if not executor_cls:
                raise ExecutionError(f"No executor found for action {action}")

            # Get required context
            context = self._get_required_context(action)

            # Create executor instance and validate context
            executor = executor_cls()
            if not executor.validate_context(context):
                return False, f"Missing required context for {action.value}"

            # Execute action
            success, outcome = await executor.execute(context)

            # Log execution
            logger.info(f"Executed {action.value}: success={success}, outcome={outcome}")
            return success, outcome

        except Exception as e:
            logger.error(f"Failed to execute action {action}: {e}")
            return False, str(e)
