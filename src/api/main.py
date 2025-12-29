"""FastAPI application entry point for the Nevron Dashboard API."""

import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.config import api_settings
from src.api.routers import (
    agent_router,
    config_router,
    cycles_router,
    learning_router,
    mcp_router,
    memory_router,
    metacognition_router,
    runtime_router,
)
from src.api.schemas import HealthCheck


# Application start time for uptime tracking
_start_time: Optional[float] = None

# Version info
__version__ = "0.1.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    global _start_time
    _start_time = time.time()
    logger.info("Nevron Dashboard API starting...")

    # Initialize WebSocket manager
    from src.api.websocket.manager import get_connection_manager

    manager = get_connection_manager()
    app.state.ws_manager = manager

    yield

    # Cleanup on shutdown
    logger.info("Nevron Dashboard API shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Nevron Dashboard API",
        description="REST API and WebSocket interface for monitoring and controlling the Nevron AI agent",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_settings.CORS_ORIGINS,
        allow_credentials=api_settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=api_settings.CORS_ALLOW_METHODS,
        allow_headers=api_settings.CORS_ALLOW_HEADERS,
    )

    # Include routers
    app.include_router(
        agent_router,
        prefix=f"{api_settings.API_V1_PREFIX}/agent",
        tags=["Agent"],
    )
    app.include_router(
        runtime_router,
        prefix=f"{api_settings.API_V1_PREFIX}/runtime",
        tags=["Runtime"],
    )
    app.include_router(
        memory_router,
        prefix=f"{api_settings.API_V1_PREFIX}/memory",
        tags=["Memory"],
    )
    app.include_router(
        learning_router,
        prefix=f"{api_settings.API_V1_PREFIX}/learning",
        tags=["Learning"],
    )
    app.include_router(
        metacognition_router,
        prefix=f"{api_settings.API_V1_PREFIX}/metacognition",
        tags=["Metacognition"],
    )
    app.include_router(
        mcp_router,
        prefix=f"{api_settings.API_V1_PREFIX}/mcp",
        tags=["MCP"],
    )
    app.include_router(
        config_router,
        prefix=f"{api_settings.API_V1_PREFIX}/config",
        tags=["Config"],
    )
    app.include_router(
        cycles_router,
        prefix=f"{api_settings.API_V1_PREFIX}/cycles",
        tags=["Cycles"],
    )

    # Health check endpoint
    @app.get("/health", response_model=HealthCheck, tags=["System"])
    async def health_check() -> HealthCheck:
        """Check API health status."""
        uptime = time.time() - _start_time if _start_time else 0.0

        # Check component status
        components: Dict[str, str] = {
            "api": "healthy",
        }

        # Try to check runtime
        try:
            from src.api.dependencies import get_runtime

            runtime = get_runtime()
            components["runtime"] = runtime.state.value
        except Exception:
            components["runtime"] = "unavailable"

        # Try to check memory
        try:
            from src.api.dependencies import get_memory

            memory = get_memory()
            components["memory"] = "healthy" if memory else "unavailable"
        except Exception:
            components["memory"] = "unavailable"

        return HealthCheck(
            status="healthy",
            version=__version__,
            uptime_seconds=uptime,
            components=components,
        )

    # Root endpoint
    @app.get("/", tags=["System"])
    async def root() -> Dict[str, Any]:
        """API root endpoint with basic info."""
        return {
            "name": "Nevron Dashboard API",
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
        }

    # WebSocket endpoint
    @app.websocket("/ws/{client_id}")
    async def websocket_endpoint(websocket: WebSocket, client_id: str):
        """WebSocket endpoint for real-time event streaming.

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
        """
        from src.api.websocket.manager import get_connection_manager

        manager = get_connection_manager()

        await manager.connect(websocket, client_id)
        try:
            while True:
                # Receive messages from client
                data = await websocket.receive_json()

                # Handle subscription messages
                if data.get("action") == "subscribe":
                    events = data.get("events", ["*"])
                    manager.subscribe(client_id, events)
                    await websocket.send_json({"type": "subscribed", "events": events})
                elif data.get("action") == "unsubscribe":
                    events = data.get("events", [])
                    manager.unsubscribe(client_id, events)
                    await websocket.send_json({"type": "unsubscribed", "events": events})
                elif data.get("action") == "ping":
                    await websocket.send_json(
                        {
                            "action": "pong",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

        except WebSocketDisconnect:
            manager.disconnect(client_id)
            logger.debug(f"WebSocket client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket error for client {client_id}: {e}")
            manager.disconnect(client_id)

    return app


# Create the application instance
app = create_app()


def run_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
    reload: bool = False,
) -> None:
    """Run the API server using uvicorn.

    Args:
        host: Host to bind to (defaults to config)
        port: Port to bind to (defaults to config)
        reload: Enable auto-reload for development
    """
    import uvicorn

    uvicorn.run(
        "src.api.main:app",
        host=host or api_settings.API_HOST,
        port=port or api_settings.API_PORT,
        reload=reload,
        log_level="debug" if api_settings.API_DEBUG else "info",
    )


if __name__ == "__main__":
    run_server(reload=True)
