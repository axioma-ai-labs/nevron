"""Execution module for handling agent actions."""

from typing import Any, Dict, List, Optional, Tuple, Type, Union

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
from src.mcp.manager import MCPToolManager
from src.mcp.types import ToolDescription


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
    """Module for executing agent actions with context awareness.

    Supports both legacy ActionExecutor-based actions and MCP tools.
    MCP tools are dynamically discovered from connected MCP servers.
    """

    def __init__(
        self,
        context_manager: ContextManager,
        mcp_tool_manager: Optional[MCPToolManager] = None,
    ):
        """Initialize execution module.

        Args:
            context_manager: Context manager for action history
            mcp_tool_manager: Optional MCP tool manager for MCP-based tools
        """
        super().__init__(context_manager)
        self._executors = ACTION_EXECUTOR_MAP
        self._mcp_manager = mcp_tool_manager
        self._mcp_initialized = False

    @property
    def mcp_manager(self) -> Optional[MCPToolManager]:
        """Get the MCP tool manager."""
        return self._mcp_manager

    def set_mcp_manager(self, mcp_manager: MCPToolManager) -> None:
        """Set the MCP tool manager.

        Args:
            mcp_manager: MCP tool manager instance
        """
        self._mcp_manager = mcp_manager

    def get_available_actions(self) -> List[str]:
        """Get list of all available actions (legacy + MCP).

        Returns:
            List of action names
        """
        actions = [action.value for action in self._executors.keys()]

        if self._mcp_manager:
            for tool in self._mcp_manager.available_tools:
                # Prefix MCP tools to distinguish them
                actions.append(f"mcp:{tool.name}")

        return actions

    def get_available_tools(self) -> List[ToolDescription]:
        """Get list of available MCP tools.

        Returns:
            List of MCP tool descriptions
        """
        if self._mcp_manager:
            return self._mcp_manager.get_tool_descriptions()
        return []

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

    async def execute_action(
        self, action: Union[AgentAction, str], arguments: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Execute an action with required context.

        Supports both legacy AgentAction enum values and MCP tool names.
        MCP tools should be prefixed with "mcp:" (e.g., "mcp:fetch").

        Args:
            action: Action to execute (AgentAction or string for MCP tools)
            arguments: Optional arguments for MCP tools

        Returns:
            Tuple of (success, outcome)
        """
        try:
            # Check if this is an MCP tool call
            resolved_action: AgentAction
            if isinstance(action, str):
                if action.startswith("mcp:"):
                    return await self._execute_mcp_tool(action[4:], arguments or {})
                else:
                    # Try to parse as AgentAction
                    try:
                        resolved_action = AgentAction(action)
                    except ValueError:
                        # Could be an MCP tool without prefix
                        if self._mcp_manager and self._mcp_manager.has_tool(action):
                            return await self._execute_mcp_tool(action, arguments or {})
                        raise ExecutionError(f"Unknown action: {action}")
            else:
                resolved_action = action

            # Legacy executor path
            executor_cls = self._executors.get(resolved_action)
            if not executor_cls:
                raise ExecutionError(f"No executor found for action {resolved_action}")

            # Get required context
            context = self._get_required_context(resolved_action)

            # Execute action
            executor = executor_cls()
            success, outcome = await executor.execute(context)

            # Log execution
            logger.info(f"Executed {resolved_action.value}: success={success}, outcome={outcome}")

            return success, outcome

        except Exception as e:
            logger.error(f"Failed to execute action {action}: {e}")
            return False, str(e)

    async def _execute_mcp_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Execute an MCP tool.

        Args:
            tool_name: Name of the MCP tool
            arguments: Tool arguments

        Returns:
            Tuple of (success, outcome)
        """
        if not self._mcp_manager:
            return False, "MCP tool manager not configured"

        result = await self._mcp_manager.execute_tool(tool_name, arguments)

        if result.success:
            logger.info(f"Executed MCP tool '{tool_name}': success")
            return True, result.to_outcome_string()
        else:
            logger.warning(f"MCP tool '{tool_name}' failed: {result.error}")
            return False, result.error

    async def execute_mcp_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Public method to execute an MCP tool directly.

        Args:
            tool_name: Name of the MCP tool
            arguments: Tool arguments

        Returns:
            Tuple of (success, outcome)
        """
        return await self._execute_mcp_tool(tool_name, arguments)

    def has_mcp_tool(self, tool_name: str) -> bool:
        """Check if an MCP tool is available.

        Args:
            tool_name: Name of the tool

        Returns:
            True if tool is available
        """
        if self._mcp_manager:
            return self._mcp_manager.has_tool(tool_name)
        return False
