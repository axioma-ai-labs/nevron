"""Agent runtime implementation."""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from src.context.context import ContextManager
from src.core.config import settings
from src.core.cycle_logger import CycleLog, create_cycle_log, get_cycle_logger
from src.core.defs import AgentAction, AgentState
from src.execution.execution_module import ExecutionModule
from src.feedback.feedback_module import FeedbackModule
from src.mcp.config import MCPSettings
from src.mcp.manager import MCPToolManager
from src.memory.memory_module import get_memory_module
from src.planning.planning_module import PlanningModule


ACTION_2_STATE: Dict[AgentAction, AgentState] = {
    AgentAction.ANALYZE_NEWS: AgentState.JUST_ANALYZED_NEWS,
    AgentAction.CHECK_SIGNAL: AgentState.JUST_ANALYZED_SIGNAL,
    AgentAction.IDLE: AgentState.DEFAULT,
}


class Agent:
    """
    Central runtime for an autonomous AI agent. Integrates:
      1. Perception Module
      2. Memory Module
      3. Planning Module
      4. Execution Module
      5. Feedback Module
      6. Context Manager (for persistent state)
      7. MCP Tool Manager (for dynamic tool integration)
    """

    def __init__(self):
        #: Initialize Memory Module
        self.memory_module = get_memory_module()

        #: Initialize Context Manager
        self.context_manager = ContextManager()

        #: Initialize MCP Tool Manager (may be None if disabled)
        self.mcp_manager: Optional[MCPToolManager] = None

        #: Initialize Planning Module with context
        self.planning_module = PlanningModule(context_manager=self.context_manager)

        #: Initialize Execution Module
        self.execution_module = ExecutionModule(context_manager=self.context_manager)

        #: Initialize Feedback Module
        self.feedback_module = FeedbackModule()

        #: Start with the last known state or default
        self.state = self.context_manager.get_context().last_state

        # ===== Agent Personality =====
        #: The agent's personality description
        self.personality = settings.AGENT_PERSONALITY
        #: The agent's goal
        self.goal = settings.AGENT_GOAL

        # ===== MCP Configuration =====
        self._mcp_enabled = settings.MCP_ENABLED
        self._mcp_initialized = False

        # ===== Cycle Logger =====
        self._cycle_logger = get_cycle_logger()

    # --------------------------------------------------------------
    # MCP INITIALIZATION
    # --------------------------------------------------------------

    async def _initialize_mcp(self) -> None:
        """Initialize MCP tool manager and connect to servers."""
        if not self._mcp_enabled:
            logger.info("MCP integration is disabled")
            return

        if self._mcp_initialized:
            logger.warning("MCP already initialized")
            return

        try:
            # Load MCP settings
            mcp_settings = self._load_mcp_settings()

            if not mcp_settings.servers:
                logger.info("No MCP servers configured")
                self._mcp_initialized = True
                return

            # Create and initialize MCP manager
            self.mcp_manager = MCPToolManager(mcp_settings)
            await self.mcp_manager.initialize()

            # Update execution module with MCP manager
            self.execution_module.set_mcp_manager(self.mcp_manager)

            # Update planning module with available tools
            self.planning_module.set_mcp_tools(self.mcp_manager.get_tool_descriptions())

            self._mcp_initialized = True
            logger.info(
                f"MCP initialized with {len(self.mcp_manager.available_tools)} tools "
                f"from {len(self.mcp_manager.connected_servers)} servers"
            )

        except Exception as e:
            logger.error(f"Failed to initialize MCP: {e}")
            self._mcp_initialized = True  # Mark as initialized to prevent retries

    def _load_mcp_settings(self) -> MCPSettings:
        """Load MCP settings from configuration.

        Returns:
            MCPSettings instance
        """
        if settings.MCP_CONFIG_FILE:
            config_path = Path(settings.MCP_CONFIG_FILE)
            if config_path.exists():
                return MCPSettings.from_yaml(config_path)
            else:
                logger.warning(f"MCP config file not found: {config_path}")

        # Return default settings
        return MCPSettings(
            enabled=settings.MCP_ENABLED,
            auto_connect=settings.MCP_AUTO_CONNECT,
            reconnect_on_failure=settings.MCP_RECONNECT_ON_FAILURE,
            max_reconnect_attempts=settings.MCP_MAX_RECONNECT_ATTEMPTS,
        )

    async def _shutdown_mcp(self) -> None:
        """Shutdown MCP connections."""
        if self.mcp_manager:
            await self.mcp_manager.shutdown()
            self.mcp_manager = None
            self._mcp_initialized = False

    # --------------------------------------------------------------
    # UTILITY FUNCTIONS FOR STATE & PLANNING & FEEDBACK
    # --------------------------------------------------------------

    def _update_state(self, last_action: AgentAction):
        """Updates the agent's state based on the last action."""
        new_state = ACTION_2_STATE.get(last_action, AgentState.DEFAULT)
        self.state = new_state
        logger.info(f"Agent state updated to: {self.state.value}")

    def _collect_feedback(self, action: str, outcome: Optional[Any]) -> float:
        """Collect feedback for the action & outcome in the FeedbackModule."""
        return self.feedback_module.collect_feedback(action, outcome)

    # --------------------------------------------------------------
    # MAIN LOOP
    # --------------------------------------------------------------

    async def start_runtime_loop(self) -> None:
        """The main runtime loop for the agent."""
        logger.info("Starting the autonomous agent runtime loop...")

        # Initialize MCP if enabled
        await self._initialize_mcp()

        try:
            while True:
                cycle_start_time = time.time()
                cycle_log: Optional[CycleLog] = None

                try:
                    # Get recent actions for context
                    recent_actions_ctx = self.context_manager.get_context().get_recent_actions(n=5)
                    recent_action_names = [a.action.value for a in recent_actions_ctx]

                    # 1. Choose an action using LLM-based planning
                    logger.info(f"Current state: {self.state.value}")
                    planning_start = time.time()
                    action_name = await self.planning_module.get_action(self.state)
                    planning_duration = int((time.time() - planning_start) * 1000)
                    logger.info(f"Action chosen: {action_name.value}")

                    # Create cycle log
                    cycle_log = create_cycle_log(
                        state=self.state.value,
                        recent_actions=recent_action_names,
                        action=action_name.value,
                    )
                    cycle_log.planning_duration_ms = planning_duration

                    # 2. Execute action using execution module
                    exec_start = time.time()
                    success, outcome = await self.execution_module.execute_action(action_name)
                    exec_duration = int((time.time() - exec_start) * 1000)
                    logger.info(f"Execution result: success={success}, outcome={outcome}")

                    # Update cycle log with execution info
                    cycle_log.execution_success = success
                    cycle_log.execution_duration_ms = exec_duration
                    cycle_log.execution_result = {"outcome": outcome}
                    if not success:
                        cycle_log.execution_error = str(outcome) if outcome else "Unknown error"

                    # 3. Collect feedback
                    reward = self._collect_feedback(action_name.value, outcome)
                    logger.info(f"Reward: {reward}")
                    cycle_log.reward = reward

                    # 4. Update context and state
                    self.context_manager.add_action(
                        action=action_name,
                        state=self.state,
                        outcome=str(outcome) if outcome else None,
                        reward=reward,
                    )
                    self._update_state(action_name)
                    cycle_log.agent_state_after = self.state.value

                    # 5. Finalize and log cycle
                    cycle_log.total_duration_ms = int((time.time() - cycle_start_time) * 1000)
                    self._cycle_logger.log_cycle(cycle_log)

                    # 6. Sleep or yield
                    logger.info("Let's rest a bit...")
                    await asyncio.sleep(settings.AGENT_REST_TIME)

                except KeyboardInterrupt:
                    logger.info("Agent runtime loop interrupted by user.")
                    break
                except Exception as e:
                    logger.error(f"Error in runtime loop: {e}")
                    # Log failed cycle if we have one
                    if cycle_log:
                        cycle_log.execution_success = False
                        cycle_log.execution_error = str(e)
                        cycle_log.total_duration_ms = int((time.time() - cycle_start_time) * 1000)
                        self._cycle_logger.log_cycle(cycle_log)
                    break
        finally:
            # Cleanup MCP connections
            await self._shutdown_mcp()

    async def start_runtime_loop_with_mcp(self) -> None:
        """Enhanced runtime loop that supports MCP tools.

        This loop uses the get_action_with_tools method which can select
        both legacy actions and MCP tools.
        """
        logger.info("Starting enhanced agent runtime loop with MCP support...")

        # Initialize MCP if enabled
        await self._initialize_mcp()

        try:
            while True:
                try:
                    # 1. Choose an action using LLM-based planning (with MCP tools)
                    logger.info(f"Current state: {self.state.value}")
                    action_str = await self.planning_module.get_action_with_tools(self.state)
                    logger.info(f"Action chosen: {action_str}")

                    # 2. Execute action
                    if action_str.startswith("mcp:"):
                        # MCP tool execution
                        tool_name = action_str[4:]
                        tool = self.mcp_manager.get_tool(tool_name) if self.mcp_manager else None

                        if tool:
                            # Plan arguments for the tool
                            arguments = await self.planning_module.plan_tool_arguments(
                                tool, self.goal
                            )
                            success, outcome = await self.execution_module.execute_mcp_tool(
                                tool_name, arguments
                            )
                        else:
                            success, outcome = False, f"Tool not found: {tool_name}"
                    else:
                        # Legacy action execution
                        try:
                            action = AgentAction(action_str)
                            success, outcome = await self.execution_module.execute_action(action)
                        except ValueError:
                            success, outcome = False, f"Unknown action: {action_str}"

                    logger.info(f"Execution result: success={success}, outcome={outcome}")

                    # 3. Collect feedback
                    reward = self._collect_feedback(action_str, outcome)
                    logger.info(f"Reward: {reward}")

                    # 4. Update context (only for legacy actions that we can track)
                    if not action_str.startswith("mcp:"):
                        try:
                            action = AgentAction(action_str)
                            self.context_manager.add_action(
                                action=action,
                                state=self.state,
                                outcome=str(outcome) if outcome else None,
                                reward=reward,
                            )
                            self._update_state(action)
                        except ValueError:
                            pass

                    # 5. Sleep or yield
                    logger.info("Let's rest a bit...")
                    await asyncio.sleep(settings.AGENT_REST_TIME)

                except KeyboardInterrupt:
                    logger.info("Agent runtime loop interrupted by user.")
                    break
                except Exception as e:
                    logger.error(f"Error in runtime loop: {e}")
                    break
        finally:
            # Cleanup MCP connections
            await self._shutdown_mcp()

    # --------------------------------------------------------------
    # MCP UTILITY METHODS
    # --------------------------------------------------------------

    def get_mcp_status(self) -> dict:
        """Get the current MCP status.

        Returns:
            Dictionary with MCP status information
        """
        if not self.mcp_manager:
            return {
                "enabled": self._mcp_enabled,
                "initialized": self._mcp_initialized,
                "connected_servers": [],
                "available_tools": 0,
            }

        return {
            "enabled": self._mcp_enabled,
            "initialized": self._mcp_initialized,
            "connected_servers": self.mcp_manager.connected_servers,
            "available_tools": len(self.mcp_manager.available_tools),
            "connection_status": [
                info.model_dump() for info in self.mcp_manager.get_connection_status()
            ],
        }

    async def reconnect_mcp_server(self, server_name: str) -> bool:
        """Attempt to reconnect to a specific MCP server.

        Args:
            server_name: Name of the server to reconnect

        Returns:
            True if reconnection was successful
        """
        if not self.mcp_manager:
            logger.error("MCP manager not initialized")
            return False

        success = await self.mcp_manager.reconnect_server(server_name)
        if success:
            # Update planning module with new tools
            self.planning_module.set_mcp_tools(self.mcp_manager.get_tool_descriptions())

        return success
