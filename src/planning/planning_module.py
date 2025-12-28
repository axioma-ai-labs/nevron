"""Planning module for the agent's decision making using LLM."""

from typing import List, Optional

from loguru import logger

from src.context.context import ActionContext, ContextManager
from src.core.defs import AgentAction, AgentState
from src.llm.llm import LLM
from src.mcp.types import ToolDescription


class PlanningModule:
    """LLM-based planning module for high-level autonomous decisions.

    Supports both static AgentAction-based actions and dynamic MCP tools.
    """

    def __init__(
        self,
        context_manager: ContextManager,
        mcp_tools: Optional[List[ToolDescription]] = None,
    ):
        """
        Initialize the planning module.

        Args:
            context_manager: Context manager instance for action history
            mcp_tools: Optional list of MCP tool descriptions for dynamic tools
        """
        self.context_manager = context_manager
        self.llm = LLM()
        self._mcp_tools: List[ToolDescription] = mcp_tools or []

    def set_mcp_tools(self, tools: List[ToolDescription]) -> None:
        """Update the list of available MCP tools.

        Args:
            tools: List of MCP tool descriptions
        """
        self._mcp_tools = tools
        logger.debug(f"Updated MCP tools list: {[t.name for t in tools]}")

    def get_mcp_tools(self) -> List[ToolDescription]:
        """Get the current list of MCP tools.

        Returns:
            List of MCP tool descriptions
        """
        return self._mcp_tools

    def _format_action_for_prompt(self, action: ActionContext) -> str:
        """Format a single action for the prompt."""
        success = "successful" if action.reward and action.reward > 0 else "unsuccessful"
        return f"Action: {action.action.value}, Outcome: {success}"

    def _format_actions_history(self, actions: List[ActionContext]) -> str:
        """Format action history for the prompt."""
        return "\n".join(
            f"{i + 1}. {self._format_action_for_prompt(action)}" for i, action in enumerate(actions)
        )

    def _format_mcp_tools_for_prompt(self) -> str:
        """Format MCP tools for the prompt.

        Returns:
            Formatted string of MCP tool descriptions
        """
        if not self._mcp_tools:
            return ""

        tools_text = ["\n\nAdditional MCP Tools Available:"]
        for tool in self._mcp_tools:
            tools_text.append(tool.to_prompt_format())

        return "\n".join(tools_text)

    def _create_planning_prompt(self, current_state: AgentState) -> str:
        """Create prompt for the LLM."""
        # Get recent actions
        recent_actions = self.context_manager.get_context().get_recent_actions(n=5)
        actions_history = self._format_actions_history(recent_actions)

        # Available actions (legacy)
        available_actions = ", ".join([action.value for action in AgentAction])

        # Add MCP tools if available
        mcp_tools_section = self._format_mcp_tools_for_prompt()

        return (
            f"Based on the following recent action history and current state, choose the next action."
            f"\nCurrent State: {current_state.value}\nRecent Actions History: {actions_history} "
            f"\nAvailable Actions: {available_actions}"
            f"{mcp_tools_section}"
            f"\n\nChoose exactly one action from the available actions. "
            f"For legacy actions, respond with just the action name (e.g., analyze_news). "
            f"For MCP tools, respond with 'mcp:<tool_name>' (e.g., mcp:fetch). "
            f"Respond with just the action name, nothing else."
        )

    def _create_planning_prompt_with_tools(
        self, current_state: AgentState, task: Optional[str] = None
    ) -> str:
        """Create an enhanced planning prompt that includes task context and tool selection.

        Args:
            current_state: Current agent state
            task: Optional specific task to accomplish

        Returns:
            Formatted prompt string
        """
        # Get recent actions
        recent_actions = self.context_manager.get_context().get_recent_actions(n=5)
        actions_history = self._format_actions_history(recent_actions)

        # Build tool descriptions
        legacy_tools = "\n".join(
            [
                f"- {action.value}: Execute {action.name.replace('_', ' ').lower()}"
                for action in AgentAction
            ]
        )

        mcp_tools = ""
        if self._mcp_tools:
            mcp_tools = "\n\nMCP Tools:\n" + "\n".join(
                [tool.to_prompt_format() for tool in self._mcp_tools]
            )

        task_section = ""
        if task:
            task_section = f"\n\nCurrent Task: {task}"

        return f"""You are an autonomous agent planning your next action.

Current State: {current_state.value}
{task_section}

Recent Actions:
{actions_history if actions_history else "(No recent actions)"}

Available Legacy Actions:
{legacy_tools}
{mcp_tools}

Instructions:
1. Analyze the current state and recent action history
2. Select the most appropriate action to make progress
3. For legacy actions, respond with just the action name (e.g., analyze_news)
4. For MCP tools, respond with 'mcp:<tool_name>' (e.g., mcp:fetch)

Respond with ONLY the action name, nothing else."""

    async def get_action(self, current_state: AgentState) -> AgentAction:
        """
        Get the next action using LLM.

        Args:
            current_state: Current state of the agent

        Returns:
            AgentAction: The chosen action
        """
        try:
            # Create planning prompt
            prompt = self._create_planning_prompt(current_state)
            logger.debug(f"Planning prompt: {prompt}")

            # Get LLM response
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.generate_response(messages)
            logger.debug(f"LLM response: {response}")

            # Parse response to get action
            action_str = response.strip().lower()

            # Check if it's an MCP tool
            if action_str.startswith("mcp:"):
                # Return IDLE for now, but the action string is logged
                # The agent runtime should handle MCP tools separately
                logger.info(f"LLM suggested MCP tool: {action_str}")
                return AgentAction.IDLE

            # Validate action
            try:
                return AgentAction(action_str)
            except ValueError:
                logger.error(f"Invalid action from LLM: {action_str}")
                return AgentAction.IDLE  # Fallback to IDLE if invalid action

        except Exception as e:
            logger.error(f"Error in planning: {e}")
            return AgentAction.IDLE  # Fallback to IDLE on error

    async def get_action_with_tools(
        self, current_state: AgentState, task: Optional[str] = None
    ) -> str:
        """Get the next action, supporting both legacy actions and MCP tools.

        This method returns a string that can be either:
        - A legacy action name (e.g., "analyze_news")
        - An MCP tool name (e.g., "mcp:fetch")

        Args:
            current_state: Current state of the agent
            task: Optional specific task context

        Returns:
            String representing the chosen action
        """
        try:
            # Create planning prompt with tools
            prompt = self._create_planning_prompt_with_tools(current_state, task)
            logger.debug(f"Planning prompt: {prompt}")

            # Get LLM response
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.generate_response(messages)
            logger.debug(f"LLM response: {response}")

            # Parse response
            action_str = response.strip().lower()

            # Validate the action
            if action_str.startswith("mcp:"):
                tool_name = action_str[4:]
                if any(t.name == tool_name for t in self._mcp_tools):
                    return action_str
                else:
                    logger.warning(f"Unknown MCP tool: {tool_name}")
                    return "idle"

            # Check if it's a valid legacy action
            try:
                AgentAction(action_str)
                return action_str
            except ValueError:
                logger.error(f"Invalid action from LLM: {action_str}")
                return "idle"

        except Exception as e:
            logger.error(f"Error in planning with tools: {e}")
            return "idle"

    async def plan_tool_arguments(self, tool: ToolDescription, task: str) -> dict:
        """Plan arguments for an MCP tool based on the task.

        Args:
            tool: The MCP tool to plan arguments for
            task: The task context

        Returns:
            Dictionary of tool arguments
        """
        prompt = f"""You need to provide arguments for the following tool to accomplish a task.

Tool: {tool.name}
Description: {tool.description}

Input Schema:
{tool.input_schema}

Task: {task}

Provide the arguments as a JSON object. Only include the necessary parameters.
Respond with ONLY valid JSON, nothing else."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.generate_response(messages)

            # Parse JSON response
            import json

            try:
                arguments = json.loads(response.strip())
                return arguments
            except json.JSONDecodeError:
                logger.error(f"Failed to parse tool arguments: {response}")
                return {}

        except Exception as e:
            logger.error(f"Error planning tool arguments: {e}")
            return {}
