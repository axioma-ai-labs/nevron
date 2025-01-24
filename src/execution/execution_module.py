"""Execution module for handling agent actions."""

from typing import Any, Dict, List, Optional, Tuple, Type

from loguru import logger

from src.context.context import ContextManager
from src.core.defs import AgentAction
from src.core.exceptions import ExecutionError
from src.execution.base import ActionExecutor, ExecutionModuleBase
from src.tools import post_summary_to_telegram, post_twitter_thread
from src.workflows.analyze_signal import analyze_signal
from src.workflows.research_news import analyze_news_workflow


class AnalyzeNewsExecutor(ActionExecutor):
    """Executor for news analysis action."""

    def _initialize_client(self) -> None:
        """No client needed for workflow."""
        return None

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["news_text"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        try:
            news_text = context.get("news_text")
            if not news_text:
                return False, "No news text provided in context"
                
            result = await analyze_news_workflow(news=news_text)
            return True, f"News analyzed: {result}"
        except Exception as e:
            logger.error(f"Failed to analyze news: {e}")
            return False, str(e)


class CheckSignalExecutor(ActionExecutor):
    """Executor for signal checking action."""

    def _initialize_client(self) -> None:
        """No client needed for workflow."""
        return None

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        try:
            result = await analyze_signal()
            return True, f"Signal checked: {result}"
        except Exception as e:
            logger.error(f"Failed to check signal: {e}")
            return False, str(e)


class PostTweetExecutor(ActionExecutor):
    """Executor for posting tweets."""

    def get_required_context(self) -> List[str]:
        return ["tweet_text"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        tweet_text = context.get("tweet_text")
        twitter_thread = {"tweet1": tweet_text}
        if not tweet_text:
            return False, "No tweet text provided in context"
        try:
            await post_twitter_thread(twitter_thread)
            return True, f"Tweet posted: {tweet_text[:50]}..."
        except Exception as e:
            return False, f"Failed to post tweet: {str(e)}"


class SendTelegramMessageExecutor(ActionExecutor):
    """Executor for sending Telegram messages."""

    def get_required_context(self) -> List[str]:
        return ["message_text"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        message = context.get("message_text")
        if not message:
            return False, "No message text provided"
        try:
            await post_summary_to_telegram(message)
            return True, f"Telegram message sent: {message[:50]}..."
        except Exception as e:
            return False, f"Failed to send Telegram message: {str(e)}"


class IdleExecutor(ActionExecutor):
    """Executor for idle action."""

    def _initialize_client(self) -> None:
        """No client needed for idle."""
        return None

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, "Idle completed"


ACTION_EXECUTOR_MAP: Dict[AgentAction, Type[ActionExecutor]] = {
    # Workflows
    AgentAction.ANALYZE_NEWS: AnalyzeNewsExecutor,
    AgentAction.CHECK_SIGNAL: CheckSignalExecutor,
    AgentAction.IDLE: IdleExecutor,
    # Social Media
    AgentAction.POST_TWEET: PostTweetExecutor,
    AgentAction.SEND_DISCORD_MESSAGE: IdleExecutor,  # TODO: Implement
    AgentAction.SEND_TELEGRAM_MESSAGE: SendTelegramMessageExecutor,
    AgentAction.POST_LENS: IdleExecutor,  # TODO: Implement
    AgentAction.SEND_WHATSAPP: IdleExecutor,  # TODO: Implement
    # Research
    AgentAction.SEARCH_TAVILY: IdleExecutor,  # TODO: Implement
    AgentAction.ASK_PERPLEXITY: IdleExecutor,  # TODO: Implement
    # Development
    AgentAction.CREATE_GITHUB_ISSUE: IdleExecutor,  # TODO: Implement
    AgentAction.CREATE_GITHUB_PR: IdleExecutor,  # TODO: Implement
    # E-commerce
    AgentAction.CREATE_SHOPIFY_PRODUCT: IdleExecutor,  # TODO: Implement
    AgentAction.UPDATE_SHOPIFY_PRODUCT: IdleExecutor,  # TODO: Implement
    # Media
    AgentAction.UPLOAD_YOUTUBE_VIDEO: IdleExecutor,  # TODO: Implement
    AgentAction.CREATE_SPOTIFY_PLAYLIST: IdleExecutor,  # TODO: Implement
}


class ExecutionModule(ExecutionModuleBase):
    """Module for executing agent actions with context awareness."""

    def __init__(self, context_manager: ContextManager):
        """Initialize execution module."""
        super().__init__(context_manager)
        self._executors = ACTION_EXECUTOR_MAP

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

            # Execute action
            executor = executor_cls()
            success, outcome = await executor.execute(context)

            # Log execution
            logger.info(f"Executed {action.value}: success={success}, outcome={outcome}")

            return success, outcome

        except Exception as e:
            logger.error(f"Failed to execute action {action}: {e}")
            return False, str(e)
