"""FastAPI dependencies for injecting agent and runtime instances."""

from typing import Optional

from fastapi import Header, HTTPException, status

from src.api.config import api_settings
from src.learning.learning_module import AdaptiveLearningModule, get_learning_module
from src.memory.tri_memory import TriMemorySystem, get_tri_memory_system
from src.metacognition.monitor import MetacognitiveMonitor
from src.runtime.runtime import AutonomousRuntime, RuntimeConfiguration


# Singleton instances
_runtime: Optional[AutonomousRuntime] = None
_memory: Optional[TriMemorySystem] = None
_learning: Optional[AdaptiveLearningModule] = None
_monitor: Optional[MetacognitiveMonitor] = None


def get_runtime() -> AutonomousRuntime:
    """Get the autonomous runtime instance (singleton)."""
    global _runtime
    if _runtime is None:
        config = RuntimeConfiguration(
            webhook_enabled=False,  # We use our own FastAPI server
            scheduler_enabled=True,
            background_enabled=True,
        )
        _runtime = AutonomousRuntime(config=config)
    return _runtime


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


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias=api_settings.API_KEY_HEADER),
) -> bool:
    """Verify API key if authentication is enabled."""
    if api_settings.API_KEY is None:
        # No authentication required
        return True

    if x_api_key is None or x_api_key != api_settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return True


def reset_singletons() -> None:
    """Reset all singleton instances (useful for testing)."""
    global _runtime, _memory, _learning, _monitor
    _runtime = None
    _memory = None
    _learning = None
    _monitor = None
