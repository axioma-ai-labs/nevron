"""Standalone agent runner process.

This module provides a standalone process for running the agent independently
from the API server. It:
- Writes state to shared storage for API to read
- Polls for commands from the API
- Can be started/stopped independently of the API

Usage:
    python -m src.agent_runner
    # or
    make run-agent
"""

import asyncio
import os
import signal
import sys
import time
from typing import Any, Dict, Optional

from loguru import logger

from src.agent import Agent
from src.core.agent_commands import AgentCommand, CommandQueue, CommandType, get_command_queue
from src.core.agent_state import CycleInfo, SharedStateManager, get_state_manager
from src.core.config import settings
from src.core.cycle_logger import CycleLog, create_cycle_log, get_cycle_logger
from src.core.defs import AgentAction
from src.utils import log_settings


# Configure logging
logger.add(
    "logs/agent_runner.log",
    rotation="1 MB",
    retention="10 days",
    level="DEBUG",
)


class AgentRunner:
    """Standalone agent runner with IPC support.

    This runner:
    - Starts in STOPPED state, waiting for START command
    - Manages the agent lifecycle independently of the API
    - Writes state to shared storage for API access
    - Processes commands from the command queue
    - Sends heartbeats to indicate liveness

    Lifecycle:
    - Process starts -> state = "stopped", waiting for commands
    - START command -> state = "running", begins agent cycles
    - PAUSE command -> state = "paused", cycles paused
    - RESUME command -> state = "running", cycles resume
    - STOP command -> state = "stopped", cycles stop (can be restarted)
    - SHUTDOWN command -> process exits
    """

    def __init__(
        self,
        state_manager: Optional[SharedStateManager] = None,
        command_queue: Optional[CommandQueue] = None,
    ):
        """Initialize the agent runner.

        Args:
            state_manager: Shared state manager (defaults to global instance)
            command_queue: Command queue (defaults to global instance)
        """
        self.state_manager = state_manager or get_state_manager()
        self.command_queue = command_queue or get_command_queue()

        self._agent: Optional[Agent] = None
        self._process_running = False  # Process is alive
        self._agent_started = False  # Agent cycles are running
        self._paused = False
        self._shutdown_requested = False

        # Heartbeat settings
        self._heartbeat_interval = 10.0  # seconds
        self._last_heartbeat = 0.0

        # Command poll settings
        self._command_poll_interval = 1.0  # seconds
        self._last_command_poll = 0.0

        logger.info("AgentRunner initialized")

    async def initialize(self) -> None:
        """Initialize the agent runner process (but don't start cycles).

        This sets up the agent and shared state, but waits for a START command
        before actually running cycles.
        """
        if self._process_running:
            logger.warning("Agent runner already initialized")
            return

        logger.info("Initializing agent runner (waiting for START command)...")
        log_settings()

        # Initialize the agent
        self._agent = Agent()

        # Update shared state - mark as STOPPED (waiting for start)
        self.state_manager.update_state(
            pid=os.getpid(),
            status="stopped",
            is_running=False,
            personality=self._agent.personality,
            goal=self._agent.goal,
        )

        # Initialize MCP if enabled
        await self._agent._initialize_mcp()

        # Update MCP status
        mcp_status = self._agent.get_mcp_status()
        self.state_manager.update_mcp_status(
            enabled=mcp_status.get("enabled", False),
            connected_servers=len(mcp_status.get("connected_servers", [])),
            available_tools=mcp_status.get("available_tools", 0),
        )

        self._process_running = True
        self._agent_started = False
        self._shutdown_requested = False

        # Setup signal handlers
        self._setup_signal_handlers()

        logger.info("Agent runner initialized - waiting for START command")

    async def start_agent(self) -> None:
        """Start agent cycles (called when START command received)."""
        if self._agent_started:
            logger.warning("Agent already started")
            return

        logger.info("Starting agent cycles...")

        # Update shared state
        self.state_manager.set_running(
            pid=os.getpid(),
            personality=self._agent.personality if self._agent else "",
            goal=self._agent.goal if self._agent else "",
        )

        self._agent_started = True
        self._paused = False

        logger.info("Agent cycles started")

    async def stop_agent(self) -> None:
        """Stop agent cycles (can be restarted with START command)."""
        if not self._agent_started:
            return

        logger.info("Stopping agent cycles...")
        self._agent_started = False
        self._paused = False

        # Update shared state
        self.state_manager.update_state(status="stopped", is_running=False)

        logger.info("Agent cycles stopped - waiting for START command")

    async def shutdown(self, error: Optional[str] = None) -> None:
        """Shutdown the agent runner process completely.

        Args:
            error: Optional error message if shutting down due to error
        """
        if not self._process_running:
            return

        logger.info("Shutting down agent runner...")

        self._process_running = False
        self._agent_started = False

        # Cleanup MCP connections
        if self._agent:
            await self._agent._shutdown_mcp()

        # Update shared state
        self.state_manager.set_stopped(error=error)

        logger.info("Agent runner shutdown complete")

    def _setup_signal_handlers(self) -> None:
        """Setup OS signal handlers for graceful shutdown."""

        def handle_signal(signum: int, frame: Any) -> None:
            logger.info(f"Received signal {signum}, requesting shutdown...")
            self._shutdown_requested = True

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    async def _send_heartbeat(self) -> None:
        """Send a heartbeat to indicate liveness."""
        now = time.time()
        if now - self._last_heartbeat >= self._heartbeat_interval:
            self.state_manager.heartbeat()
            self._last_heartbeat = now

    async def _process_commands(self) -> None:
        """Process any pending commands."""
        now = time.time()
        if now - self._last_command_poll < self._command_poll_interval:
            return

        self._last_command_poll = now

        command = self.command_queue.get_next_command()
        if not command:
            return

        logger.info(f"Processing command: {command.command_type}")

        # Mark as processing
        self.command_queue.mark_processing(command.command_id)

        try:
            result = await self._handle_command(command)
            self.command_queue.mark_completed(command.command_id, result)
        except Exception as e:
            logger.error(f"Command failed: {e}")
            self.command_queue.mark_failed(command.command_id, str(e))

    async def _handle_command(self, command: AgentCommand) -> Dict[str, Any]:
        """Handle a specific command.

        Args:
            command: Command to handle

        Returns:
            Result dictionary
        """
        cmd_type = command.command_type

        if cmd_type == CommandType.START.value:
            if self._agent_started:
                return {"status": "already_running"}
            await self.start_agent()
            return {"status": "started"}

        elif cmd_type == CommandType.STOP.value:
            if not self._agent_started:
                return {"status": "already_stopped"}
            await self.stop_agent()
            return {"status": "stopped"}

        elif cmd_type == CommandType.PAUSE.value:
            if not self._agent_started:
                return {"status": "error", "error": "Agent not running"}
            self._paused = True
            self.state_manager.update_state(status="paused")
            return {"status": "paused"}

        elif cmd_type == CommandType.RESUME.value:
            if not self._agent_started:
                return {"status": "error", "error": "Agent not running"}
            self._paused = False
            self.state_manager.update_state(status="running")
            return {"status": "resumed"}

        elif cmd_type == CommandType.SHUTDOWN.value:
            self._shutdown_requested = True
            return {"status": "shutdown_requested"}

        elif cmd_type == CommandType.EXECUTE_ACTION.value:
            # Execute a specific action
            if not self._agent:
                return {"success": False, "error": "Agent not initialized"}

            action_name = command.params.get("action") if command.params else None
            if not action_name:
                return {"success": False, "error": "No action specified"}

            try:
                action = AgentAction(action_name)
                success, outcome = await self._agent.execution_module.execute_action(action)
                return {
                    "success": success,
                    "action": action_name,
                    "outcome": str(outcome) if outcome else None,
                }
            except ValueError:
                return {"success": False, "error": f"Unknown action: {action_name}"}

        elif cmd_type == CommandType.RELOAD_CONFIG.value:
            # Reload configuration (placeholder)
            return {"status": "config_reloaded"}

        else:
            return {"error": f"Unknown command type: {cmd_type}"}

    async def run_cycle(self) -> bool:
        """Run a single agent cycle.

        Returns:
            True if cycle completed successfully
        """
        if not self._agent:
            return False

        cycle_start_time = time.time()
        cycle_log: Optional[CycleLog] = None

        try:
            # Get recent actions for context
            recent_actions_ctx = self._agent.context_manager.get_context().get_recent_actions(n=5)
            recent_action_names = [a.action.value for a in recent_actions_ctx]

            # 1. Choose an action using LLM-based planning
            current_state = self._agent.state.value
            logger.info(f"Current state: {current_state}")

            self.state_manager.update_state(agent_state=current_state)

            planning_start = time.time()
            action = await self._agent.planning_module.get_action(self._agent.state)
            planning_duration = int((time.time() - planning_start) * 1000)
            logger.info(f"Action chosen: {action.value}")

            # Update state with current action
            self.state_manager.set_current_action(action.value)

            # Create cycle log
            cycle_log = create_cycle_log(
                state=current_state,
                recent_actions=recent_action_names,
                action=action.value,
            )
            cycle_log.planning_duration_ms = planning_duration

            # 2. Execute action
            exec_start = time.time()
            success, outcome = await self._agent.execution_module.execute_action(action)
            exec_duration = int((time.time() - exec_start) * 1000)
            logger.info(f"Execution result: success={success}, outcome={outcome}")

            # Update cycle log
            cycle_log.execution_success = success
            cycle_log.execution_duration_ms = exec_duration
            cycle_log.execution_result = {"outcome": outcome}
            if not success:
                cycle_log.execution_error = str(outcome) if outcome else "Unknown error"

            # 3. Collect feedback
            reward = self._agent._collect_feedback(action.value, outcome)
            logger.info(f"Reward: {reward}")
            cycle_log.reward = reward

            # 4. Update agent context and state
            self._agent.context_manager.add_action(
                action=action,
                state=self._agent.state,
                outcome=str(outcome) if outcome else None,
                reward=reward,
            )
            previous_state = self._agent.state.value
            self._agent._update_state(action)
            new_state = self._agent.state.value
            cycle_log.agent_state_after = new_state

            # 5. Finalize cycle log
            total_duration = int((time.time() - cycle_start_time) * 1000)
            cycle_log.total_duration_ms = total_duration
            get_cycle_logger().log_cycle(cycle_log)

            # 6. Update shared state
            self.state_manager.update_cycle_info(
                action=action.value,
                agent_state=new_state,
                success=success,
                reward=reward,
            )

            # 7. Add to recent cycles in shared state
            cycle_info = CycleInfo(
                cycle_id=cycle_log.cycle_id,
                timestamp=cycle_log.timestamp,
                action=action.value,
                state_before=previous_state,
                state_after=new_state,
                success=success,
                outcome=str(outcome) if outcome else None,
                reward=reward,
                duration_ms=total_duration,
                error=cycle_log.execution_error,
            )
            self.state_manager.add_cycle(cycle_info)

            return True

        except Exception as e:
            logger.error(f"Error in cycle: {e}")

            # Log failed cycle
            if cycle_log:
                cycle_log.execution_success = False
                cycle_log.execution_error = str(e)
                cycle_log.total_duration_ms = int((time.time() - cycle_start_time) * 1000)
                get_cycle_logger().log_cycle(cycle_log)

            return False

    async def run(self) -> None:
        """Main run loop.

        The agent runner starts in STOPPED state and waits for commands.
        When START command is received, it begins running cycles.
        """
        await self.initialize()

        try:
            while self._process_running and not self._shutdown_requested:
                # Send heartbeat
                await self._send_heartbeat()

                # Process any pending commands
                await self._process_commands()

                # Check for shutdown
                if self._shutdown_requested:
                    break

                # If agent not started, just wait for commands
                if not self._agent_started:
                    await asyncio.sleep(1.0)
                    continue

                # Skip cycle if paused
                if self._paused:
                    await asyncio.sleep(1.0)
                    continue

                # Run a cycle
                await self.run_cycle()

                # Check for shutdown again
                if self._shutdown_requested:
                    break

                # Rest between cycles
                logger.info("Resting between cycles...")
                await asyncio.sleep(settings.AGENT_REST_TIME)

        except KeyboardInterrupt:
            logger.info("Agent runner interrupted by user")
        except Exception as e:
            logger.critical(f"Fatal error in agent runner: {e}")
            await self.shutdown(error=str(e))
            raise
        finally:
            await self.shutdown()


async def async_main() -> None:
    """Async entry point."""
    runner = AgentRunner()
    await runner.run()


def main() -> None:
    """Main entry point."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Agent runner shutting down...")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
