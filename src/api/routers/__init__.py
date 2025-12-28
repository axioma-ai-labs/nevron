"""API routers for the Nevron Dashboard."""

from src.api.routers.agent import router as agent_router
from src.api.routers.config import router as config_router
from src.api.routers.learning import router as learning_router
from src.api.routers.mcp import router as mcp_router
from src.api.routers.memory import router as memory_router
from src.api.routers.metacognition import router as metacognition_router
from src.api.routers.runtime import router as runtime_router


__all__ = [
    "agent_router",
    "runtime_router",
    "memory_router",
    "learning_router",
    "metacognition_router",
    "mcp_router",
    "config_router",
]
