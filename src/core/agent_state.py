"""Shared agent state manager for IPC between API and agent process.

This module provides a file-based shared state system that allows:
- Agent process to write its current state
- API server to read the state without owning the runtime
- Both processes to operate independently

The state is stored in JSON files with file locking for safe concurrent access.
"""

import fcntl
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


# Default state directory
DEFAULT_STATE_DIR = Path("./nevron_state")


@dataclass
class AgentRuntimeState:
    """Current state of the agent runtime."""

    # Process info
    pid: Optional[int] = None
    started_at: Optional[str] = None
    last_heartbeat: Optional[str] = None

    # Runtime state
    status: str = "stopped"  # stopped, starting, running, paused, stopping, error
    is_running: bool = False

    # Agent state
    agent_state: str = "unknown"
    personality: str = ""
    goal: str = ""

    # MCP status
    mcp_enabled: bool = False
    mcp_connected_servers: int = 0
    mcp_available_tools: int = 0

    # Current cycle info
    current_action: Optional[str] = None
    cycle_count: int = 0
    last_action_time: Optional[str] = None

    # Statistics
    total_rewards: float = 0.0
    successful_actions: int = 0
    failed_actions: int = 0

    # Error info
    last_error: Optional[str] = None
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentRuntimeState":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CycleInfo:
    """Information about a single agent cycle."""

    cycle_id: str
    timestamp: str
    action: str
    state_before: str
    state_after: str
    success: bool
    outcome: Optional[str] = None
    reward: float = 0.0
    duration_ms: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CycleInfo":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RecentCycles:
    """Recent cycle history for quick access."""

    cycles: List[CycleInfo] = field(default_factory=list)
    max_cycles: int = 50

    def add_cycle(self, cycle: CycleInfo) -> None:
        """Add a cycle, maintaining max size."""
        self.cycles.insert(0, cycle)
        if len(self.cycles) > self.max_cycles:
            self.cycles = self.cycles[: self.max_cycles]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cycles": [c.to_dict() for c in self.cycles],
            "max_cycles": self.max_cycles,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RecentCycles":
        """Create from dictionary."""
        cycles = [CycleInfo.from_dict(c) for c in data.get("cycles", [])]
        return cls(cycles=cycles, max_cycles=data.get("max_cycles", 50))


class SharedStateManager:
    """Manages shared state between API and agent process.

    Uses file-based storage with file locking for safe concurrent access.
    State is split into multiple files for better granularity:
    - state.json: Current agent runtime state
    - cycles.json: Recent cycle history
    """

    def __init__(self, state_dir: Optional[Path] = None):
        """Initialize the shared state manager.

        Args:
            state_dir: Directory for state files. Defaults to ./nevron_state
        """
        self.state_dir = state_dir or DEFAULT_STATE_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self._state_file = self.state_dir / "state.json"
        self._cycles_file = self.state_dir / "cycles.json"
        self._lock_file = self.state_dir / ".lock"

        # Initialize files if they don't exist
        self._init_files()

        logger.debug(f"SharedStateManager initialized at {self.state_dir}")

    def _init_files(self) -> None:
        """Initialize state files if they don't exist."""
        if not self._state_file.exists():
            self._write_state(AgentRuntimeState())

        if not self._cycles_file.exists():
            self._write_cycles(RecentCycles())

    def _acquire_lock(self, lock_file: Path) -> int:
        """Acquire an exclusive lock on a file.

        Args:
            lock_file: File to lock

        Returns:
            File descriptor for the lock
        """
        fd = os.open(str(lock_file), os.O_CREAT | os.O_RDWR)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd

    def _release_lock(self, fd: int) -> None:
        """Release a file lock.

        Args:
            fd: File descriptor to release
        """
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    def _read_json(self, file_path: Path) -> Dict[str, Any]:
        """Read JSON from a file with locking.

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON data
        """
        fd = self._acquire_lock(self._lock_file)
        try:
            if not file_path.exists():
                return {}
            with open(file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in {file_path}, returning empty dict")
            return {}
        finally:
            self._release_lock(fd)

    def _write_json(self, file_path: Path, data: Dict[str, Any]) -> None:
        """Write JSON to a file with locking.

        Args:
            file_path: Path to JSON file
            data: Data to write
        """
        fd = self._acquire_lock(self._lock_file)
        try:
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        finally:
            self._release_lock(fd)

    # =========================================================================
    # State Operations
    # =========================================================================

    def get_state(self) -> AgentRuntimeState:
        """Get the current agent runtime state.

        Returns:
            AgentRuntimeState instance
        """
        data = self._read_json(self._state_file)
        return AgentRuntimeState.from_dict(data)

    def _write_state(self, state: AgentRuntimeState) -> None:
        """Write state to file.

        Args:
            state: State to write
        """
        self._write_json(self._state_file, state.to_dict())

    def update_state(self, **kwargs: Any) -> AgentRuntimeState:
        """Update specific fields in the state.

        Args:
            **kwargs: Fields to update

        Returns:
            Updated state
        """
        state = self.get_state()
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
        self._write_state(state)
        return state

    def set_running(
        self,
        pid: int,
        personality: str = "",
        goal: str = "",
    ) -> None:
        """Mark agent as running.

        Args:
            pid: Process ID of the agent
            personality: Agent personality
            goal: Agent goal
        """
        now = datetime.now(timezone.utc).isoformat()
        self.update_state(
            pid=pid,
            started_at=now,
            last_heartbeat=now,
            status="running",
            is_running=True,
            personality=personality,
            goal=goal,
        )

    def set_stopped(self, error: Optional[str] = None) -> None:
        """Mark agent as stopped.

        Args:
            error: Optional error message if stopped due to error
        """
        updates: Dict[str, Any] = {
            "status": "error" if error else "stopped",
            "is_running": False,
            "current_action": None,
        }
        if error:
            updates["last_error"] = error
            updates["error_count"] = self.get_state().error_count + 1
        self.update_state(**updates)

    def heartbeat(self) -> None:
        """Update the heartbeat timestamp."""
        self.update_state(last_heartbeat=datetime.now(timezone.utc).isoformat())

    def update_cycle_info(
        self,
        action: str,
        agent_state: str,
        success: bool,
        reward: float = 0.0,
    ) -> None:
        """Update state after a cycle.

        Args:
            action: Action that was executed
            agent_state: Current agent state
            success: Whether the action succeeded
            reward: Reward from the action
        """
        state = self.get_state()
        updates: Dict[str, Any] = {
            "current_action": None,
            "cycle_count": state.cycle_count + 1,
            "last_action_time": datetime.now(timezone.utc).isoformat(),
            "agent_state": agent_state,
            "total_rewards": state.total_rewards + reward,
        }
        if success:
            updates["successful_actions"] = state.successful_actions + 1
        else:
            updates["failed_actions"] = state.failed_actions + 1

        self.update_state(**updates)

    def set_current_action(self, action: str) -> None:
        """Set the currently executing action.

        Args:
            action: Action name
        """
        self.update_state(current_action=action)

    def update_mcp_status(
        self,
        enabled: bool,
        connected_servers: int = 0,
        available_tools: int = 0,
    ) -> None:
        """Update MCP status.

        Args:
            enabled: Whether MCP is enabled
            connected_servers: Number of connected servers
            available_tools: Number of available tools
        """
        self.update_state(
            mcp_enabled=enabled,
            mcp_connected_servers=connected_servers,
            mcp_available_tools=available_tools,
        )

    # =========================================================================
    # Cycles Operations
    # =========================================================================

    def get_recent_cycles(self) -> RecentCycles:
        """Get recent cycle history.

        Returns:
            RecentCycles instance
        """
        data = self._read_json(self._cycles_file)
        return RecentCycles.from_dict(data)

    def _write_cycles(self, cycles: RecentCycles) -> None:
        """Write cycles to file.

        Args:
            cycles: Cycles to write
        """
        self._write_json(self._cycles_file, cycles.to_dict())

    def add_cycle(self, cycle: CycleInfo) -> None:
        """Add a cycle to the history.

        Args:
            cycle: Cycle info to add
        """
        cycles = self.get_recent_cycles()
        cycles.add_cycle(cycle)
        self._write_cycles(cycles)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def is_agent_alive(self, timeout_seconds: float = 60.0) -> bool:
        """Check if the agent process is alive based on heartbeat.

        Args:
            timeout_seconds: Max seconds since last heartbeat

        Returns:
            True if agent appears alive
        """
        state = self.get_state()

        if not state.is_running or not state.last_heartbeat:
            return False

        try:
            last_beat = datetime.fromisoformat(state.last_heartbeat.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age = (now - last_beat).total_seconds()
            return age < timeout_seconds
        except (ValueError, TypeError):
            return False

    def is_agent_process_running(self) -> bool:
        """Check if the agent process is actually running.

        Returns:
            True if the process exists
        """
        state = self.get_state()
        if not state.pid:
            return False

        try:
            os.kill(state.pid, 0)  # Signal 0 just checks if process exists
            return True
        except (OSError, ProcessLookupError):
            return False

    def clear_state(self) -> None:
        """Clear all state (for testing or reset)."""
        self._write_state(AgentRuntimeState())
        self._write_cycles(RecentCycles())

    def get_full_status(self) -> Dict[str, Any]:
        """Get complete status information.

        Returns:
            Dictionary with full status
        """
        state = self.get_state()
        cycles = self.get_recent_cycles()

        return {
            "state": state.to_dict(),
            "is_alive": self.is_agent_alive(),
            "is_process_running": self.is_agent_process_running(),
            "recent_cycles_count": len(cycles.cycles),
        }


# =========================================================================
# Global Instance
# =========================================================================

_state_manager: Optional[SharedStateManager] = None


def get_state_manager(state_dir: Optional[Path] = None) -> SharedStateManager:
    """Get or create the global SharedStateManager instance.

    Args:
        state_dir: Optional state directory path

    Returns:
        SharedStateManager instance
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = SharedStateManager(state_dir)
    return _state_manager


def reset_state_manager() -> None:
    """Reset the global state manager (for testing)."""
    global _state_manager
    _state_manager = None
