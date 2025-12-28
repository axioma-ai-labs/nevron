"""Config router - endpoints for configuration management."""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel

from src.api.config import api_settings
from src.api.dependencies import verify_api_key
from src.api.schemas import APIResponse


router = APIRouter()


class AgentConfig(BaseModel):
    """Agent configuration."""

    personality: str
    goal: str
    rest_time: float
    mcp_enabled: bool


class RuntimeConfig(BaseModel):
    """Runtime configuration."""

    webhook_enabled: bool
    webhook_port: int
    scheduler_enabled: bool
    background_enabled: bool
    process_timeout: float
    max_concurrent_events: int


class MemoryConfig(BaseModel):
    """Memory system configuration."""

    backend_type: str
    consolidation_enabled: bool
    consolidation_interval: int


class LearningConfig(BaseModel):
    """Learning module configuration."""

    critique_on_failure: bool
    critique_threshold: float
    auto_create_lessons: bool
    enable_bias_adaptation: bool


class APIConfig(BaseModel):
    """API server configuration."""

    host: str
    port: int
    debug: bool
    cors_origins: List[str]
    api_key_enabled: bool
    rate_limit_enabled: bool


class FullConfig(BaseModel):
    """Complete system configuration."""

    agent: AgentConfig
    runtime: RuntimeConfig
    memory: MemoryConfig
    learning: LearningConfig
    api: APIConfig


@router.get("/agent", response_model=APIResponse[AgentConfig])
async def get_agent_config(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[AgentConfig]:
    """Get agent configuration.

    Returns agent personality, goal, and MCP settings.
    """
    try:
        from src.core.config import settings

        config = AgentConfig(
            personality=settings.AGENT_PERSONALITY,
            goal=settings.AGENT_GOAL,
            rest_time=settings.AGENT_REST_TIME,
            mcp_enabled=settings.MCP_ENABLED,
        )

        return APIResponse(
            success=True,
            data=config,
            message="Agent configuration retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get agent config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get agent config: {str(e)}",
        )


@router.get("/runtime", response_model=APIResponse[RuntimeConfig])
async def get_runtime_config(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[RuntimeConfig]:
    """Get runtime configuration.

    Returns webhook, scheduler, and processing settings.
    """
    try:
        from src.runtime.runtime import RuntimeConfiguration

        default_config = RuntimeConfiguration()

        config = RuntimeConfig(
            webhook_enabled=default_config.webhook_enabled,
            webhook_port=default_config.webhook_port,
            scheduler_enabled=default_config.scheduler_enabled,
            background_enabled=default_config.background_enabled,
            process_timeout=default_config.process_timeout,
            max_concurrent_events=default_config.max_concurrent_events,
        )

        return APIResponse(
            success=True,
            data=config,
            message="Runtime configuration retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get runtime config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get runtime config: {str(e)}",
        )


@router.get("/memory", response_model=APIResponse[MemoryConfig])
async def get_memory_config(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[MemoryConfig]:
    """Get memory system configuration.

    Returns backend type and consolidation settings.
    """
    try:
        from src.core.config import settings

        config = MemoryConfig(
            backend_type=settings.MEMORY_BACKEND_TYPE,
            consolidation_enabled=True,  # Default
            consolidation_interval=3600,  # Default 1 hour
        )

        return APIResponse(
            success=True,
            data=config,
            message="Memory configuration retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get memory config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory config: {str(e)}",
        )


@router.get("/learning", response_model=APIResponse[LearningConfig])
async def get_learning_config(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[LearningConfig]:
    """Get learning module configuration.

    Returns critique and lesson settings.
    """
    try:
        from src.learning.learning_module import LearningConfig as LC

        default_config = LC()

        config = LearningConfig(
            critique_on_failure=default_config.critique_on_failure,
            critique_threshold=default_config.critique_threshold,
            auto_create_lessons=default_config.auto_create_lessons,
            enable_bias_adaptation=default_config.enable_bias_adaptation,
        )

        return APIResponse(
            success=True,
            data=config,
            message="Learning configuration retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get learning config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get learning config: {str(e)}",
        )


@router.get("/api", response_model=APIResponse[APIConfig])
async def get_api_config(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[APIConfig]:
    """Get API server configuration.

    Returns server, CORS, and security settings.
    """
    try:
        config = APIConfig(
            host=api_settings.API_HOST,
            port=api_settings.API_PORT,
            debug=api_settings.API_DEBUG,
            cors_origins=api_settings.CORS_ORIGINS,
            api_key_enabled=api_settings.API_KEY is not None,
            rate_limit_enabled=api_settings.RATE_LIMIT_ENABLED,
        )

        return APIResponse(
            success=True,
            data=config,
            message="API configuration retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get API config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API config: {str(e)}",
        )


@router.get("/", response_model=APIResponse[FullConfig])
async def get_full_config(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[FullConfig]:
    """Get complete system configuration.

    Returns all configuration sections.
    """
    try:
        from src.core.config import settings
        from src.learning.learning_module import LearningConfig as LC
        from src.runtime.runtime import RuntimeConfiguration

        default_runtime = RuntimeConfiguration()
        default_learning = LC()

        config = FullConfig(
            agent=AgentConfig(
                personality=settings.AGENT_PERSONALITY,
                goal=settings.AGENT_GOAL,
                rest_time=settings.AGENT_REST_TIME,
                mcp_enabled=settings.MCP_ENABLED,
            ),
            runtime=RuntimeConfig(
                webhook_enabled=default_runtime.webhook_enabled,
                webhook_port=default_runtime.webhook_port,
                scheduler_enabled=default_runtime.scheduler_enabled,
                background_enabled=default_runtime.background_enabled,
                process_timeout=default_runtime.process_timeout,
                max_concurrent_events=default_runtime.max_concurrent_events,
            ),
            memory=MemoryConfig(
                backend_type=settings.MEMORY_BACKEND_TYPE,
                consolidation_enabled=True,
                consolidation_interval=3600,
            ),
            learning=LearningConfig(
                critique_on_failure=default_learning.critique_on_failure,
                critique_threshold=default_learning.critique_threshold,
                auto_create_lessons=default_learning.auto_create_lessons,
                enable_bias_adaptation=default_learning.enable_bias_adaptation,
            ),
            api=APIConfig(
                host=api_settings.API_HOST,
                port=api_settings.API_PORT,
                debug=api_settings.API_DEBUG,
                cors_origins=api_settings.CORS_ORIGINS,
                api_key_enabled=api_settings.API_KEY is not None,
                rate_limit_enabled=api_settings.RATE_LIMIT_ENABLED,
            ),
        )

        return APIResponse(
            success=True,
            data=config,
            message="Full configuration retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get full config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get full config: {str(e)}",
        )


@router.get("/environment", response_model=APIResponse[Dict[str, Any]])
async def get_environment_info(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[Dict[str, Any]]:
    """Get environment information.

    Returns Python version, OS, and package versions.
    """
    import platform
    import sys

    try:
        env_info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        }

        # Try to get package versions
        try:
            import fastapi

            env_info["fastapi_version"] = fastapi.__version__
        except Exception:
            pass

        try:
            import uvicorn

            env_info["uvicorn_version"] = uvicorn.__version__
        except Exception:
            pass

        return APIResponse(
            success=True,
            data=env_info,
            message="Environment information retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get environment info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get environment info: {str(e)}",
        )
