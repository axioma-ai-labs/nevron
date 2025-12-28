"""Event bridge for connecting runtime events to WebSocket broadcasts."""

from typing import Any, Dict, Optional

from loguru import logger

from src.api.schemas import WSMessageType
from src.api.websocket.manager import ConnectionManager, get_connection_manager


class EventBridge:
    """Bridges runtime events to WebSocket broadcasts.

    Provides a way to hook into various system events and
    broadcast them to connected WebSocket clients.
    """

    def __init__(self, manager: Optional[ConnectionManager] = None):
        """Initialize the event bridge.

        Args:
            manager: ConnectionManager instance (uses singleton if not provided)
        """
        self._manager = manager or get_connection_manager()
        self._running = False
        self._hooks_installed = False

        logger.debug("EventBridge initialized")

    @property
    def manager(self) -> ConnectionManager:
        """Get the connection manager."""
        return self._manager

    async def broadcast(
        self,
        event_type: WSMessageType,
        data: Dict[str, Any],
    ) -> int:
        """Broadcast an event to all connected clients.

        Args:
            event_type: Type of event
            data: Event data

        Returns:
            Number of clients that received the message
        """
        return await self._manager.broadcast(event_type, data)

    async def emit_runtime_state_change(
        self,
        old_state: str,
        new_state: str,
        reason: Optional[str] = None,
    ) -> None:
        """Emit a runtime state change event.

        Args:
            old_state: Previous state
            new_state: New state
            reason: Optional reason for change
        """
        await self.broadcast(
            WSMessageType.RUNTIME_STATE_CHANGE,
            {
                "old_state": old_state,
                "new_state": new_state,
                "reason": reason,
            },
        )

    async def emit_runtime_stats_update(self, stats: Dict[str, Any]) -> None:
        """Emit runtime statistics update.

        Args:
            stats: Runtime statistics
        """
        await self.broadcast(
            WSMessageType.RUNTIME_STATS_UPDATE,
            stats,
        )

    async def emit_agent_action(
        self,
        action: str,
        state: str,
        success: bool,
        outcome: Optional[str] = None,
        reward: float = 0.0,
    ) -> None:
        """Emit an agent action event.

        Args:
            action: Action that was taken
            state: Agent state
            success: Whether action succeeded
            outcome: Action outcome
            reward: Reward received
        """
        await self.broadcast(
            WSMessageType.AGENT_ACTION,
            {
                "action": action,
                "state": state,
                "success": success,
                "outcome": outcome,
                "reward": reward,
            },
        )

    async def emit_agent_state_change(
        self,
        old_state: str,
        new_state: str,
    ) -> None:
        """Emit an agent state change event.

        Args:
            old_state: Previous state
            new_state: New state
        """
        await self.broadcast(
            WSMessageType.AGENT_STATE_CHANGE,
            {
                "old_state": old_state,
                "new_state": new_state,
            },
        )

    async def emit_learning_outcome(
        self,
        action: str,
        reward: float,
        success: bool,
        new_success_rate: float,
    ) -> None:
        """Emit a learning outcome event.

        Args:
            action: Action that was learned from
            reward: Reward received
            success: Whether action succeeded
            new_success_rate: Updated success rate
        """
        await self.broadcast(
            WSMessageType.LEARNING_OUTCOME,
            {
                "action": action,
                "reward": reward,
                "success": success,
                "new_success_rate": new_success_rate,
            },
        )

    async def emit_critique(
        self,
        action: str,
        what_went_wrong: str,
        better_approach: str,
    ) -> None:
        """Emit a critique event.

        Args:
            action: Action that was critiqued
            what_went_wrong: What went wrong
            better_approach: Suggested better approach
        """
        await self.broadcast(
            WSMessageType.CRITIQUE_GENERATED,
            {
                "action": action,
                "what_went_wrong": what_went_wrong,
                "better_approach": better_approach,
            },
        )

    async def emit_lesson_created(
        self,
        lesson_id: str,
        summary: str,
        action: str,
    ) -> None:
        """Emit a lesson created event.

        Args:
            lesson_id: ID of created lesson
            summary: Lesson summary
            action: Related action
        """
        await self.broadcast(
            WSMessageType.LESSON_CREATED,
            {
                "lesson_id": lesson_id,
                "summary": summary,
                "action": action,
            },
        )

    async def emit_intervention(
        self,
        intervention_type: str,
        reason: str,
        suggested_action: Optional[str] = None,
    ) -> None:
        """Emit a metacognitive intervention event.

        Args:
            intervention_type: Type of intervention
            reason: Reason for intervention
            suggested_action: Suggested alternative action
        """
        await self.broadcast(
            WSMessageType.INTERVENTION,
            {
                "type": intervention_type,
                "reason": reason,
                "suggested_action": suggested_action,
            },
        )

    async def emit_confidence_update(
        self,
        level: float,
        should_request_help: bool,
    ) -> None:
        """Emit a confidence update event.

        Args:
            level: New confidence level
            should_request_help: Whether help should be requested
        """
        await self.broadcast(
            WSMessageType.CONFIDENCE_UPDATE,
            {
                "level": level,
                "should_request_help": should_request_help,
            },
        )

    async def emit_loop_detected(
        self,
        description: str,
        repetitions: int,
    ) -> None:
        """Emit a loop detection event.

        Args:
            description: Description of the loop
            repetitions: Number of repetitions detected
        """
        await self.broadcast(
            WSMessageType.LOOP_DETECTED,
            {
                "description": description,
                "repetitions": repetitions,
            },
        )

    async def emit_memory_stored(
        self,
        memory_type: str,
        memory_id: str,
        summary: str,
    ) -> None:
        """Emit a memory stored event.

        Args:
            memory_type: Type of memory (episode, fact, skill, etc.)
            memory_id: ID of stored memory
            summary: Brief summary
        """
        await self.broadcast(
            WSMessageType.MEMORY_STORED,
            {
                "memory_type": memory_type,
                "memory_id": memory_id,
                "summary": summary,
            },
        )

    async def emit_memory_consolidated(
        self,
        episodes_processed: int,
        facts_created: int,
        skills_updated: int,
    ) -> None:
        """Emit a memory consolidation event.

        Args:
            episodes_processed: Number of episodes processed
            facts_created: Number of facts created
            skills_updated: Number of skills updated
        """
        await self.broadcast(
            WSMessageType.MEMORY_CONSOLIDATED,
            {
                "episodes_processed": episodes_processed,
                "facts_created": facts_created,
                "skills_updated": skills_updated,
            },
        )

    async def emit_mcp_connected(
        self,
        server_name: str,
        tools_count: int,
    ) -> None:
        """Emit an MCP server connected event.

        Args:
            server_name: Name of connected server
            tools_count: Number of tools discovered
        """
        await self.broadcast(
            WSMessageType.MCP_SERVER_CONNECTED,
            {
                "server_name": server_name,
                "tools_count": tools_count,
            },
        )

    async def emit_mcp_disconnected(
        self,
        server_name: str,
        reason: Optional[str] = None,
    ) -> None:
        """Emit an MCP server disconnected event.

        Args:
            server_name: Name of disconnected server
            reason: Reason for disconnection
        """
        await self.broadcast(
            WSMessageType.MCP_SERVER_DISCONNECTED,
            {
                "server_name": server_name,
                "reason": reason,
            },
        )

    async def emit_mcp_tool_executed(
        self,
        tool_name: str,
        success: bool,
        execution_time: float,
    ) -> None:
        """Emit an MCP tool execution event.

        Args:
            tool_name: Name of executed tool
            success: Whether execution succeeded
            execution_time: Execution time in seconds
        """
        await self.broadcast(
            WSMessageType.MCP_TOOL_EXECUTED,
            {
                "tool_name": tool_name,
                "success": success,
                "execution_time": execution_time,
            },
        )

    async def emit_log(
        self,
        level: str,
        message: str,
        source: Optional[str] = None,
    ) -> None:
        """Emit a system log event.

        Args:
            level: Log level (debug, info, warning, error)
            message: Log message
            source: Source of the log
        """
        await self.broadcast(
            WSMessageType.LOG,
            {
                "level": level,
                "message": message,
                "source": source,
            },
        )

    async def emit_error(
        self,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit a system error event.

        Args:
            error_type: Type of error
            message: Error message
            details: Additional error details
        """
        await self.broadcast(
            WSMessageType.ERROR,
            {
                "error_type": error_type,
                "message": message,
                "details": details or {},
            },
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get event bridge statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "running": self._running,
            "hooks_installed": self._hooks_installed,
            "manager_stats": self._manager.get_statistics(),
        }


# Singleton instance
_event_bridge: Optional[EventBridge] = None


def get_event_bridge() -> EventBridge:
    """Get or create the event bridge singleton.

    Returns:
        EventBridge instance
    """
    global _event_bridge
    if _event_bridge is None:
        _event_bridge = EventBridge()
    return _event_bridge
