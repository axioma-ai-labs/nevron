"""API configuration settings."""

from typing import List, Optional

from pydantic_settings import BaseSettings


class APISettings(BaseSettings):
    """Settings for the Nevron Dashboard API."""

    # Server settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = False

    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # API versioning
    API_V1_PREFIX: str = "/api/v1"

    # Authentication (optional)
    API_KEY: Optional[str] = None
    API_KEY_HEADER: str = "X-API-Key"

    # WebSocket settings
    WS_HEARTBEAT_INTERVAL: float = 30.0
    WS_MAX_CONNECTIONS: int = 100

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    class Config:
        env_prefix = "NEVRON_"
        case_sensitive = True


api_settings = APISettings()
