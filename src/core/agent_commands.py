"""Agent command queue for IPC between API and agent process.

This module provides a file-based command queue that allows:
- API to send commands to the agent (start, stop, pause, etc.)
- Agent to poll for and execute commands
- Atomic command handling with acknowledgment

Commands are written as JSON files that the agent polls and processes.
"""

import json
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


# Default command directory
DEFAULT_COMMAND_DIR = Path("./nevron_state/commands")


class CommandType(str, Enum):
    """Types of commands that can be sent to the agent."""

    START = "start"
    STOP = "stop"
    PAUSE = "pause"
    RESUME = "resume"
    EXECUTE_ACTION = "execute_action"
    RELOAD_CONFIG = "reload_config"
    SHUTDOWN = "shutdown"  # Graceful shutdown


class CommandStatus(str, Enum):
    """Status of a command."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class AgentCommand:
    """A command to be sent to the agent."""

    command_id: str
    command_type: str
    created_at: str
    status: str = CommandStatus.PENDING.value
    params: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    completed_at: Optional[str] = None
    expires_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCommand":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def is_expired(self) -> bool:
        """Check if the command has expired."""
        if not self.expires_at:
            return False
        try:
            expires = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            return datetime.now(timezone.utc) > expires
        except (ValueError, TypeError):
            return False


class CommandQueue:
    """Manages commands between API and agent process.

    Commands are stored as individual JSON files for atomic operations.
    The agent polls for pending commands and processes them.
    """

    def __init__(self, command_dir: Optional[Path] = None):
        """Initialize the command queue.

        Args:
            command_dir: Directory for command files. Defaults to ./nevron_state/commands
        """
        self.command_dir = command_dir or DEFAULT_COMMAND_DIR
        self.command_dir.mkdir(parents=True, exist_ok=True)

        self._pending_dir = self.command_dir / "pending"
        self._completed_dir = self.command_dir / "completed"
        self._failed_dir = self.command_dir / "failed"

        # Create subdirectories
        for d in [self._pending_dir, self._completed_dir, self._failed_dir]:
            d.mkdir(parents=True, exist_ok=True)

        logger.debug(f"CommandQueue initialized at {self.command_dir}")

    def _generate_command_id(self) -> str:
        """Generate a unique command ID."""
        return f"cmd_{uuid.uuid4().hex[:12]}"

    def _get_command_path(self, command_id: str, status: CommandStatus) -> Path:
        """Get the path for a command file.

        Args:
            command_id: Command ID
            status: Command status

        Returns:
            Path to the command file
        """
        if status == CommandStatus.PENDING:
            return self._pending_dir / f"{command_id}.json"
        elif status in (CommandStatus.COMPLETED, CommandStatus.PROCESSING):
            return self._completed_dir / f"{command_id}.json"
        else:
            return self._failed_dir / f"{command_id}.json"

    def _write_command(self, command: AgentCommand) -> None:
        """Write a command to file.

        Args:
            command: Command to write
        """
        status = CommandStatus(command.status)
        path = self._get_command_path(command.command_id, status)
        with open(path, "w") as f:
            json.dump(command.to_dict(), f, indent=2)

    def _read_command(self, path: Path) -> Optional[AgentCommand]:
        """Read a command from file.

        Args:
            path: Path to command file

        Returns:
            AgentCommand or None if not found
        """
        try:
            if not path.exists():
                return None
            with open(path, "r") as f:
                data = json.load(f)
            return AgentCommand.from_dict(data)
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to read command from {path}: {e}")
            return None

    def _move_command(
        self,
        command_id: str,
        from_status: CommandStatus,
        to_status: CommandStatus,
    ) -> None:
        """Move a command file between status directories.

        Args:
            command_id: Command ID
            from_status: Current status
            to_status: New status
        """
        from_path = self._get_command_path(command_id, from_status)
        to_path = self._get_command_path(command_id, to_status)

        if from_path.exists():
            from_path.rename(to_path)

    # =========================================================================
    # API Methods (for sending commands)
    # =========================================================================

    def send_command(
        self,
        command_type: CommandType,
        params: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 60.0,
    ) -> AgentCommand:
        """Send a command to the agent.

        Args:
            command_type: Type of command
            params: Optional parameters
            timeout_seconds: When the command expires

        Returns:
            The created command
        """
        now = datetime.now(timezone.utc)
        expires_at = None
        if timeout_seconds > 0:
            from datetime import timedelta

            expires_at = (now + timedelta(seconds=timeout_seconds)).isoformat()

        command = AgentCommand(
            command_id=self._generate_command_id(),
            command_type=command_type.value,
            created_at=now.isoformat(),
            status=CommandStatus.PENDING.value,
            params=params,
            expires_at=expires_at,
        )

        self._write_command(command)
        logger.info(f"Sent command: {command_type.value} (id={command.command_id})")

        return command

    def get_command_status(self, command_id: str) -> Optional[AgentCommand]:
        """Get the status of a command.

        Args:
            command_id: Command ID to check

        Returns:
            Command or None if not found
        """
        # Check all directories
        for status in [CommandStatus.PENDING, CommandStatus.COMPLETED, CommandStatus.FAILED]:
            path = self._get_command_path(command_id, status)
            command = self._read_command(path)
            if command:
                return command
        return None

    def wait_for_command(
        self,
        command_id: str,
        timeout_seconds: float = 30.0,
        poll_interval: float = 0.5,
    ) -> Optional[AgentCommand]:
        """Wait for a command to complete.

        Args:
            command_id: Command ID to wait for
            timeout_seconds: Max time to wait
            poll_interval: Time between polls

        Returns:
            Completed command or None if timeout
        """
        start = time.time()
        while time.time() - start < timeout_seconds:
            command = self.get_command_status(command_id)
            if command and command.status in [
                CommandStatus.COMPLETED.value,
                CommandStatus.FAILED.value,
            ]:
                return command
            time.sleep(poll_interval)
        return None

    # =========================================================================
    # Agent Methods (for processing commands)
    # =========================================================================

    def get_pending_commands(self) -> List[AgentCommand]:
        """Get all pending commands.

        Returns:
            List of pending commands, oldest first
        """
        commands = []
        for path in sorted(self._pending_dir.glob("*.json")):
            command = self._read_command(path)
            if command:
                if command.is_expired():
                    # Mark as expired
                    command.status = CommandStatus.EXPIRED.value
                    command.error = "Command expired"
                    self._move_command(
                        command.command_id,
                        CommandStatus.PENDING,
                        CommandStatus.FAILED,
                    )
                    self._write_command(command)
                else:
                    commands.append(command)
        return commands

    def get_next_command(self) -> Optional[AgentCommand]:
        """Get the next pending command.

        Returns:
            Next command to process or None
        """
        commands = self.get_pending_commands()
        return commands[0] if commands else None

    def mark_processing(self, command_id: str) -> Optional[AgentCommand]:
        """Mark a command as being processed.

        Args:
            command_id: Command ID

        Returns:
            Updated command or None if not found
        """
        path = self._get_command_path(command_id, CommandStatus.PENDING)
        command = self._read_command(path)

        if not command:
            return None

        command.status = CommandStatus.PROCESSING.value
        self._move_command(command_id, CommandStatus.PENDING, CommandStatus.COMPLETED)
        self._write_command(command)

        logger.debug(f"Command marked as processing: {command_id}")
        return command

    def mark_completed(
        self,
        command_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[AgentCommand]:
        """Mark a command as completed.

        Args:
            command_id: Command ID
            result: Optional result data

        Returns:
            Updated command or None if not found
        """
        command = self.get_command_status(command_id)
        if not command:
            return None

        command.status = CommandStatus.COMPLETED.value
        command.completed_at = datetime.now(timezone.utc).isoformat()
        command.result = result

        # Write to completed directory
        path = self._get_command_path(command_id, CommandStatus.COMPLETED)
        with open(path, "w") as f:
            json.dump(command.to_dict(), f, indent=2)

        logger.debug(f"Command completed: {command_id}")
        return command

    def mark_failed(
        self,
        command_id: str,
        error: str,
    ) -> Optional[AgentCommand]:
        """Mark a command as failed.

        Args:
            command_id: Command ID
            error: Error message

        Returns:
            Updated command or None if not found
        """
        # First check if it's in pending
        pending_path = self._get_command_path(command_id, CommandStatus.PENDING)
        completed_path = self._get_command_path(command_id, CommandStatus.COMPLETED)

        command = self._read_command(pending_path) or self._read_command(completed_path)
        if not command:
            return None

        command.status = CommandStatus.FAILED.value
        command.completed_at = datetime.now(timezone.utc).isoformat()
        command.error = error

        # Move to failed directory
        if pending_path.exists():
            pending_path.unlink()
        if completed_path.exists():
            completed_path.unlink()

        path = self._get_command_path(command_id, CommandStatus.FAILED)
        with open(path, "w") as f:
            json.dump(command.to_dict(), f, indent=2)

        logger.debug(f"Command failed: {command_id} - {error}")
        return command

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def cleanup_old_commands(self, max_age_hours: float = 24.0) -> int:
        """Clean up old completed/failed commands.

        Args:
            max_age_hours: Max age of commands to keep

        Returns:
            Number of commands cleaned up
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cleaned = 0

        for directory in [self._completed_dir, self._failed_dir]:
            for path in directory.glob("*.json"):
                command = self._read_command(path)
                if command and command.completed_at:
                    try:
                        completed = datetime.fromisoformat(
                            command.completed_at.replace("Z", "+00:00")
                        )
                        if completed < cutoff:
                            path.unlink()
                            cleaned += 1
                    except (ValueError, TypeError):
                        pass

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old commands")

        return cleaned

    def get_statistics(self) -> Dict[str, Any]:
        """Get command queue statistics.

        Returns:
            Statistics dictionary
        """
        pending_count = len(list(self._pending_dir.glob("*.json")))
        completed_count = len(list(self._completed_dir.glob("*.json")))
        failed_count = len(list(self._failed_dir.glob("*.json")))

        return {
            "pending": pending_count,
            "completed": completed_count,
            "failed": failed_count,
            "total": pending_count + completed_count + failed_count,
        }


# =========================================================================
# Global Instance
# =========================================================================

_command_queue: Optional[CommandQueue] = None


def get_command_queue(command_dir: Optional[Path] = None) -> CommandQueue:
    """Get or create the global CommandQueue instance.

    Args:
        command_dir: Optional command directory path

    Returns:
        CommandQueue instance
    """
    global _command_queue
    if _command_queue is None:
        _command_queue = CommandQueue(command_dir)
    return _command_queue


def reset_command_queue() -> None:
    """Reset the global command queue (for testing)."""
    global _command_queue
    _command_queue = None
