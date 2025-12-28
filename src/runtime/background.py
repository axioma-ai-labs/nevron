"""Background process manager for the event-driven runtime."""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

from loguru import logger


class ProcessState(Enum):
    """State of a background process."""

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ProcessStatistics:
    """Statistics for a background process."""

    iterations: int = 0
    errors: int = 0
    last_run_at: Optional[datetime] = None
    last_error: Optional[str] = None
    started_at: Optional[datetime] = None
    total_run_time: float = 0.0


@dataclass
class BackgroundProcess:
    """A background process definition."""

    name: str
    func: Callable[[], Coroutine[Any, Any, None]]
    interval: float  # Seconds between runs
    enabled: bool = True
    state: ProcessState = ProcessState.STOPPED
    statistics: ProcessStatistics = field(default_factory=ProcessStatistics)
    run_on_start: bool = False
    max_errors: int = 10  # Max consecutive errors before stopping
    consecutive_errors: int = 0
    _task: Optional[asyncio.Task[None]] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "interval": self.interval,
            "enabled": self.enabled,
            "state": self.state.value,
            "statistics": {
                "iterations": self.statistics.iterations,
                "errors": self.statistics.errors,
                "last_run_at": (
                    self.statistics.last_run_at.isoformat() if self.statistics.last_run_at else None
                ),
                "last_error": self.statistics.last_error,
                "started_at": (
                    self.statistics.started_at.isoformat() if self.statistics.started_at else None
                ),
                "total_run_time": self.statistics.total_run_time,
            },
        }


class BackgroundProcessManager:
    """Manages long-running background tasks.

    Provides a framework for running periodic tasks like:
    - Memory consolidation
    - Goal monitoring
    - Health checks
    - Learning updates
    """

    def __init__(self):
        """Initialize background process manager."""
        self._processes: Dict[str, BackgroundProcess] = {}
        self._running = False
        logger.debug("BackgroundProcessManager initialized")

    def register(
        self,
        name: str,
        func: Callable[[], Coroutine[Any, Any, None]],
        interval: float,
        enabled: bool = True,
        run_on_start: bool = False,
        max_errors: int = 10,
    ) -> BackgroundProcess:
        """Register a background process.

        Args:
            name: Process name
            func: Async function to run
            interval: Seconds between runs
            enabled: Whether process is enabled
            run_on_start: Run immediately on start
            max_errors: Max consecutive errors before auto-stop

        Returns:
            The registered process
        """
        process = BackgroundProcess(
            name=name,
            func=func,
            interval=interval,
            enabled=enabled,
            run_on_start=run_on_start,
            max_errors=max_errors,
        )
        self._processes[name] = process
        logger.debug(f"Registered background process: {name}")
        return process

    def unregister(self, name: str) -> bool:
        """Unregister a background process.

        Args:
            name: Process name

        Returns:
            True if process was found and removed
        """
        if name in self._processes:
            process = self._processes[name]
            if process.state == ProcessState.RUNNING:
                logger.warning(f"Stopping running process before unregister: {name}")
                asyncio.create_task(self._stop_process(process))
            del self._processes[name]
            return True
        return False

    def enable(self, name: str) -> bool:
        """Enable a process.

        Args:
            name: Process name

        Returns:
            True if process was found
        """
        if name in self._processes:
            self._processes[name].enabled = True
            return True
        return False

    def disable(self, name: str) -> bool:
        """Disable a process.

        Args:
            name: Process name

        Returns:
            True if process was found
        """
        if name in self._processes:
            process = self._processes[name]
            process.enabled = False
            if process.state == ProcessState.RUNNING:
                asyncio.create_task(self._stop_process(process))
            return True
        return False

    async def start_all(self) -> None:
        """Start all enabled background processes."""
        self._running = True

        for process in self._processes.values():
            if process.enabled:
                await self._start_process(process)

        logger.info(f"Started {len(self._processes)} background processes")

    async def stop_all(self) -> None:
        """Stop all running background processes."""
        self._running = False

        for process in self._processes.values():
            if process.state == ProcessState.RUNNING:
                await self._stop_process(process)

        logger.info("Stopped all background processes")

    async def start(self, name: str) -> bool:
        """Start a specific process.

        Args:
            name: Process name

        Returns:
            True if process was started
        """
        if name not in self._processes:
            return False

        process = self._processes[name]
        if process.state == ProcessState.RUNNING:
            logger.warning(f"Process already running: {name}")
            return False

        await self._start_process(process)
        return True

    async def stop(self, name: str) -> bool:
        """Stop a specific process.

        Args:
            name: Process name

        Returns:
            True if process was stopped
        """
        if name not in self._processes:
            return False

        process = self._processes[name]
        if process.state != ProcessState.RUNNING:
            logger.warning(f"Process not running: {name}")
            return False

        await self._stop_process(process)
        return True

    async def _start_process(self, process: BackgroundProcess) -> None:
        """Start a process.

        Args:
            process: Process to start
        """
        process.state = ProcessState.STARTING
        process.statistics.started_at = datetime.now(timezone.utc)
        process.consecutive_errors = 0

        process._task = asyncio.create_task(self._run_process(process))
        process.state = ProcessState.RUNNING

        logger.info(f"Background process started: {process.name}")

    async def _stop_process(self, process: BackgroundProcess) -> None:
        """Stop a process.

        Args:
            process: Process to stop
        """
        process.state = ProcessState.STOPPING

        if process._task:
            process._task.cancel()
            try:
                await process._task
            except asyncio.CancelledError:
                pass
            process._task = None

        process.state = ProcessState.STOPPED
        logger.info(f"Background process stopped: {process.name}")

    async def _run_process(self, process: BackgroundProcess) -> None:
        """Run a process loop.

        Args:
            process: Process to run
        """
        # Run immediately if configured
        if process.run_on_start:
            await self._execute_iteration(process)

        # Main loop
        while process.state == ProcessState.RUNNING and self._running:
            try:
                await asyncio.sleep(process.interval)

                if process.state != ProcessState.RUNNING:
                    break

                await self._execute_iteration(process)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in process {process.name}: {e}")
                process.statistics.errors += 1
                process.statistics.last_error = str(e)

    async def _execute_iteration(self, process: BackgroundProcess) -> None:
        """Execute one iteration of a process.

        Args:
            process: Process to execute
        """
        start_time = datetime.now(timezone.utc)

        try:
            await process.func()

            # Reset consecutive errors on success
            process.consecutive_errors = 0
            process.statistics.iterations += 1

        except Exception as e:
            process.consecutive_errors += 1
            process.statistics.errors += 1
            process.statistics.last_error = str(e)
            logger.error(f"Error in background process {process.name}: {e}")

            # Check if we should stop due to too many errors
            if process.consecutive_errors >= process.max_errors:
                logger.error(
                    f"Process {process.name} exceeded max errors ({process.max_errors}), stopping"
                )
                process.state = ProcessState.ERROR
                return

        # Update statistics
        end_time = datetime.now(timezone.utc)
        process.statistics.last_run_at = end_time
        process.statistics.total_run_time += (end_time - start_time).total_seconds()

    def get_process(self, name: str) -> Optional[BackgroundProcess]:
        """Get a process by name.

        Args:
            name: Process name

        Returns:
            Process or None
        """
        return self._processes.get(name)

    def list_processes(
        self,
        running_only: bool = False,
    ) -> List[BackgroundProcess]:
        """List all processes.

        Args:
            running_only: Only return running processes

        Returns:
            List of processes
        """
        processes = list(self._processes.values())
        if running_only:
            processes = [p for p in processes if p.state == ProcessState.RUNNING]
        return processes

    def get_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all processes.

        Returns:
            Dict mapping process names to their statistics
        """
        return {name: process.to_dict() for name, process in self._processes.items()}

    @property
    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running


# Pre-built background process factories


def create_health_check_process(
    health_check_func: Callable[[], Coroutine[Any, Any, None]],
    interval: float = 300.0,
) -> tuple[str, Callable[[], Coroutine[Any, Any, None]], float]:
    """Create a health check process configuration.

    Args:
        health_check_func: Function to perform health check
        interval: Check interval in seconds

    Returns:
        Tuple of (name, func, interval)
    """
    return ("health_check", health_check_func, interval)


def create_memory_consolidation_process(
    consolidate_func: Callable[[], Coroutine[Any, Any, None]],
    interval: float = 3600.0,
) -> tuple[str, Callable[[], Coroutine[Any, Any, None]], float]:
    """Create a memory consolidation process configuration.

    Args:
        consolidate_func: Function to consolidate memory
        interval: Consolidation interval in seconds

    Returns:
        Tuple of (name, func, interval)
    """
    return ("memory_consolidation", consolidate_func, interval)


def create_learning_update_process(
    update_func: Callable[[], Coroutine[Any, Any, None]],
    interval: float = 1800.0,
) -> tuple[str, Callable[[], Coroutine[Any, Any, None]], float]:
    """Create a learning update process configuration.

    Args:
        update_func: Function to update learning
        interval: Update interval in seconds

    Returns:
        Tuple of (name, func, interval)
    """
    return ("learning_update", update_func, interval)
