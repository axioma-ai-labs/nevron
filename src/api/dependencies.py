"""FastAPI dependencies for injecting shared state and services.

This module provides dependency injection for the API. It no longer owns
the agent runtime - instead it reads from shared state and sends commands
via the command queue.
"""

from typing import Optional

from src.api.auth import verify_api_key  # noqa: F401  (re-export for routers)
from src.core.agent_commands import CommandQueue, get_command_queue
from src.core.agent_state import SharedStateManager, get_state_manager
from src.learning.learning_module import AdaptiveLearningModule, get_learning_module
from src.memory.tri_memory import TriMemorySystem, get_tri_memory_system
from src.metacognition.monitor import MetacognitiveMonitor


# Singleton instances for stateless services (not agent runtime)
_memory: Optional[TriMemorySystem] = None
_learning: Optional[AdaptiveLearningModule] = None
_monitor: Optional[MetacognitiveMonitor] = None


def get_shared_state() -> SharedStateManager:
    """Get the shared state manager for reading agent state.

    This replaces the old get_runtime() - the API no longer owns the runtime.
    Instead, it reads state from shared storage.

    Returns:
        SharedStateManager instance
    """
    return get_state_manager()


def get_commands() -> CommandQueue:
    """Get the command queue for sending commands to the agent.

    Returns:
        CommandQueue instance
    """
    return get_command_queue()


def get_memory() -> TriMemorySystem:
    """Get the tri-memory system instance (singleton)."""
    global _memory
    if _memory is None:
        _memory = get_tri_memory_system(enable_consolidation=True)
    return _memory


def get_learning() -> AdaptiveLearningModule:
    """Get the learning module instance (singleton)."""
    global _learning
    if _learning is None:
        _learning = get_learning_module()
    return _learning


def get_monitor() -> MetacognitiveMonitor:
    """Get the metacognitive monitor instance (singleton)."""
    global _monitor
    if _monitor is None:
        _monitor = MetacognitiveMonitor(enable_human_handoff=False)
    return _monitor


def reset_singletons() -> None:
    """Reset all singleton instances (useful for testing)."""
    global _memory, _learning, _monitor
    _memory = None
    _learning = None
    _monitor = None
