"""Execution module for handling agent actions."""

from typing import Any, Dict, Optional, Tuple, Type

from loguru import logger

from src.context.context import ContextManager
from src.core.defs import AgentAction
from src.core.exceptions import ExecutionError
from src.execution.base import ActionExecutor, ExecutionModuleBase
from src.execution.development_executors import (
    CreateGithubIssueExecutor,
    CreateGithubPRExecutor,
    ProcessGithubMemoriesExecutor,
    SearchGoogleDriveExecutor,
    UploadGoogleDriveExecutor,
)
from src.execution.ecommerce_executors import (
    GetShopifyOrdersExecutor,
    GetShopifyProductExecutor,
    UpdateShopifyProductExecutor,
)
from src.execution.media_executors import (
    RetrieveSpotifyPlaylistExecutor,
    RetrieveYouTubePlaylistExecutor,
    SearchSpotifySongExecutor,
    SearchYouTubeVideoExecutor,
)
from src.execution.research_executors import (
    CoinstatsExecutor,
    PerplexityExecutor,
    SearchTavilyExecutor,
)
from src.execution.social_media_executors import (
    FetchLensExecutor,
    ListenDiscordMessagesExecutor,
    ListenSlackMessagesExecutor,
    ListenWhatsAppMessagesExecutor,
    PostLensExecutor,
    PostTweetExecutor,
    SendDiscordMessageExecutor,
    SendSlackMessageExecutor,
    SendTelegramMessageExecutor,
    SendWhatsAppMessageExecutor,
)
from src.execution.workflows_executors import AnalyzeNewsExecutor, CheckSignalExecutor, IdleExecutor


ACTION_EXECUTOR_MAP: Dict[AgentAction, Type[ActionExecutor]] = {
    # Workflows
    AgentAction.ANALYZE_NEWS: AnalyzeNewsExecutor,
    AgentAction.CHECK_SIGNAL: CheckSignalExecutor,
    AgentAction.IDLE: IdleExecutor,
    # Social Media
    AgentAction.POST_TWEET: PostTweetExecutor,
    AgentAction.LISTEN_DISCORD_MESSAGES: ListenDiscordMessagesExecutor,  # TODO: Implement
    AgentAction.SEND_DISCORD_MESSAGE: SendDiscordMessageExecutor,  # TODO: Implement
    AgentAction.SEND_TELEGRAM_MESSAGE: SendTelegramMessageExecutor,
    AgentAction.POST_LENS: PostLensExecutor,  # TODO: Implement
    AgentAction.FETCH_LENS: FetchLensExecutor,  # TODO: Implement
    AgentAction.LISTEN_WHATSAPP_MESSAGES: ListenWhatsAppMessagesExecutor,  # TODO: Implement
    AgentAction.SEND_WHATSAPP_MESSAGE: SendWhatsAppMessageExecutor,  # TODO: Implement
    AgentAction.LISTEN_SLACK_MESSAGES: ListenSlackMessagesExecutor,  # TODO: Implement
    AgentAction.SEND_SLACK_MESSAGE: SendSlackMessageExecutor,  # TODO: Implement
    # Research
    AgentAction.SEARCH_TAVILY: SearchTavilyExecutor,  # TODO: Implement
    AgentAction.ASK_PERPLEXITY: PerplexityExecutor,  # TODO: Implement
    AgentAction.ASK_COINSTATS: CoinstatsExecutor,  # TODO: Implement
    # Development
    AgentAction.CREATE_GITHUB_ISSUE: CreateGithubIssueExecutor,  # TODO: Implement
    AgentAction.CREATE_GITHUB_PR: CreateGithubPRExecutor,  # TODO: Implement
    AgentAction.PROCESS_GITHUB_MEMORIES: ProcessGithubMemoriesExecutor,  # TODO: Implement
    AgentAction.SEARCH_GOOGLE_DRIVE: SearchGoogleDriveExecutor,  # TODO: Implement
    AgentAction.UPLOAD_GOOGLE_DRIVE: UploadGoogleDriveExecutor,  # TODO: Implement
    # E-commerce
    AgentAction.GET_SHOPIFY_PRODUCT: GetShopifyProductExecutor,  # TODO: Implement
    AgentAction.GET_SHOPIFY_ORDERS: GetShopifyOrdersExecutor,  # TODO: Implement
    AgentAction.UPDATE_SHOPIFY_PRODUCT: UpdateShopifyProductExecutor,  # TODO: Implement
    # Media
    AgentAction.SEARCH_YOUTUBE_VIDEO: SearchYouTubeVideoExecutor,  # TODO: Implement
    AgentAction.RETRIEVE_YOUTUBE_PLAYLIST: RetrieveYouTubePlaylistExecutor,  # TODO: Implement
    AgentAction.SEARCH_SPOTIFY_SONG: SearchSpotifySongExecutor,  # TODO: Implement
    AgentAction.RETRIEVE_SPOTIFY_PLAYLIST: RetrieveSpotifyPlaylistExecutor,  # TODO: Implement
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
