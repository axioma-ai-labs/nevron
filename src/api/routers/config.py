"""Config router - endpoints for configuration management."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel

from src.api.config import api_settings
from src.api.dependencies import verify_api_key
from src.api.schemas import APIResponse
from src.core.ui_config import (
    UIConfigResponse,
    IntegrationsConfig,
    AgentBehaviorConfig,
    MCPServerUIConfig,
    config_exists,
    get_config_response,
    get_all_available_actions,
    load_ui_config,
    save_ui_config,
    AVAILABLE_MODELS,
    ACTION_INTEGRATION_MAP,
)


router = APIRouter()


# ============================================================================
# UI Config Models (for dashboard settings page)
# ============================================================================


class UIConfigUpdate(BaseModel):
    """Request model for updating UI config."""

    # LLM Settings
    llm_provider: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None

    # Agent Identity
    agent_name: Optional[str] = None
    agent_personality: Optional[str] = None
    agent_goal: Optional[str] = None

    # Agent Behavior
    agent_behavior: Optional[Dict[str, Any]] = None

    # Actions
    enabled_actions: Optional[List[str]] = None

    # Integrations (partial updates supported)
    integrations: Optional[Dict[str, Any]] = None

    # MCP Settings
    mcp_enabled: Optional[bool] = None
    mcp_servers: Optional[List[Dict[str, Any]]] = None


class ActionsListResponse(BaseModel):
    """Response for available actions list."""
    actions: List[Dict[str, Any]]
    action_integration_map: Dict[str, str]


class IntegrationStatusResponse(BaseModel):
    """Response for integration status check."""
    integration: str
    configured: bool
    required_fields: List[str]
    missing_fields: List[str]


class ConfigExistsResponse(BaseModel):
    """Response for config exists check."""

    exists: bool
    has_api_key: bool


class ModelsListResponse(BaseModel):
    """Response for available models list."""

    models: Dict[str, List[str]]


class ValidateKeyRequest(BaseModel):
    """Request for validating an API key."""

    provider: str
    api_key: str
    model: Optional[str] = None


class ValidateKeyResponse(BaseModel):
    """Response for API key validation."""

    valid: bool
    message: str


# ============================================================================
# UI Config Endpoints (NEW - for dashboard settings)
# ============================================================================


@router.get("/ui", response_model=APIResponse[UIConfigResponse])
async def get_ui_config(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[UIConfigResponse]:
    """Get UI configuration with masked API key.

    Returns the current UI configuration from nevron_config.json.
    The API key is masked for security.
    """
    try:
        config = load_ui_config()
        response = get_config_response(config)

        return APIResponse(
            success=True,
            data=response,
            message="UI configuration retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get UI config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get UI config: {str(e)}",
        )


@router.put("/ui", response_model=APIResponse[UIConfigResponse])
async def update_ui_config(
    update: UIConfigUpdate,
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[UIConfigResponse]:
    """Update UI configuration.

    Updates the nevron_config.json file with new settings.
    Only provided fields are updated; others remain unchanged.
    Supports partial updates for nested objects like integrations.
    """
    try:
        # Load existing config
        config = load_ui_config()

        # Update LLM settings
        if update.llm_provider is not None:
            config.llm_provider = update.llm_provider
        if update.llm_api_key is not None:
            config.llm_api_key = update.llm_api_key
        if update.llm_model is not None:
            config.llm_model = update.llm_model

        # Update agent identity
        if update.agent_name is not None:
            config.agent_name = update.agent_name
        if update.agent_personality is not None:
            config.agent_personality = update.agent_personality
        if update.agent_goal is not None:
            config.agent_goal = update.agent_goal

        # Update agent behavior (partial update)
        if update.agent_behavior is not None:
            current_behavior = config.agent_behavior.model_dump()
            current_behavior.update(update.agent_behavior)
            config.agent_behavior = AgentBehaviorConfig(**current_behavior)

        # Update enabled actions
        if update.enabled_actions is not None:
            config.enabled_actions = update.enabled_actions

        # Update integrations (partial update per integration)
        if update.integrations is not None:
            current_integrations = config.integrations.model_dump()
            for integration_name, integration_data in update.integrations.items():
                if integration_name in current_integrations and isinstance(integration_data, dict):
                    current_integrations[integration_name].update(integration_data)
            config.integrations = IntegrationsConfig(**current_integrations)

        # Update MCP settings
        if update.mcp_enabled is not None:
            config.mcp_enabled = update.mcp_enabled
        if update.mcp_servers is not None:
            config.mcp_servers = [MCPServerUIConfig(**s) for s in update.mcp_servers]

        # Save updated config
        if not save_ui_config(config):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save configuration",
            )

        response = get_config_response(config)

        return APIResponse(
            success=True,
            data=response,
            message="UI configuration updated",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update UI config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update UI config: {str(e)}",
        )


@router.get("/ui/exists", response_model=APIResponse[ConfigExistsResponse])
async def check_config_exists(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[ConfigExistsResponse]:
    """Check if UI configuration file exists.

    Returns whether nevron_config.json exists and has an API key configured.
    """
    try:
        exists = config_exists()
        has_api_key = False

        if exists:
            config = load_ui_config()
            has_api_key = bool(config.llm_api_key)

        return APIResponse(
            success=True,
            data=ConfigExistsResponse(exists=exists, has_api_key=has_api_key),
            message="Config existence checked",
        )
    except Exception as e:
        logger.error(f"Failed to check config exists: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check config exists: {str(e)}",
        )


@router.get("/ui/models", response_model=APIResponse[ModelsListResponse])
async def get_available_models_list(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[ModelsListResponse]:
    """Get available models for all providers.

    Returns a dictionary mapping provider names to their available models.
    """
    try:
        return APIResponse(
            success=True,
            data=ModelsListResponse(models=AVAILABLE_MODELS),
            message="Available models retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available models: {str(e)}",
        )


@router.get("/ui/actions", response_model=APIResponse[ActionsListResponse])
async def get_available_actions(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[ActionsListResponse]:
    """Get all available actions that can be enabled for the agent.

    Returns a list of actions with their names, values, and categories,
    plus a mapping of which actions require which integrations.
    """
    try:
        actions = get_all_available_actions()
        return APIResponse(
            success=True,
            data=ActionsListResponse(
                actions=actions,
                action_integration_map=ACTION_INTEGRATION_MAP,
            ),
            message="Available actions retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get available actions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get available actions: {str(e)}",
        )


@router.get("/ui/integrations/status", response_model=APIResponse[List[IntegrationStatusResponse]])
async def get_integrations_status(
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[IntegrationStatusResponse]]:
    """Get the configuration status of all integrations.

    Returns which integrations are configured and which fields are missing.
    """
    try:
        config = load_ui_config()
        integrations = config.integrations

        # Define required fields per integration
        integration_required_fields = {
            "twitter": ["api_key", "api_secret_key", "access_token", "access_token_secret"],
            "telegram": ["bot_token", "chat_id"],
            "discord": ["bot_token", "channel_id"],
            "slack": ["bot_token"],
            "whatsapp": ["id_instance", "api_token"],
            "github": ["token"],
            "google_drive": [],  # OAuth handled separately
            "tavily": ["api_key"],
            "perplexity": ["api_key"],
            "shopify": ["api_key", "password", "store_name"],
            "youtube": ["api_key"],
            "spotify": ["client_id", "client_secret"],
            "lens": ["api_key"],
        }

        result = []
        for integration_name, required_fields in integration_required_fields.items():
            integration_data = getattr(integrations, integration_name, None)
            if integration_data is None:
                result.append(IntegrationStatusResponse(
                    integration=integration_name,
                    configured=False,
                    required_fields=required_fields,
                    missing_fields=required_fields,
                ))
                continue

            # Check which required fields are missing
            missing = []
            for field in required_fields:
                value = getattr(integration_data, field, "")
                if not value:
                    missing.append(field)

            result.append(IntegrationStatusResponse(
                integration=integration_name,
                configured=len(missing) == 0,
                required_fields=required_fields,
                missing_fields=missing,
            ))

        return APIResponse(
            success=True,
            data=result,
            message="Integration status retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get integrations status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get integrations status: {str(e)}",
        )


@router.post("/ui/validate", response_model=APIResponse[ValidateKeyResponse])
async def validate_api_key(
    request: ValidateKeyRequest,
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[ValidateKeyResponse]:
    """Validate an API key by attempting a simple LLM call.

    Tests the provided API key by making a minimal request to the provider.
    """
    try:
        provider = request.provider.lower()
        api_key = request.api_key
        model = request.model

        if not api_key:
            return APIResponse(
                success=True,
                data=ValidateKeyResponse(valid=False, message="API key is empty"),
                message="Validation complete",
            )

        # Attempt validation based on provider
        valid = False
        message = "Unknown provider"

        if provider == "openai":
            valid, message = await _validate_openai_key(api_key, model or "gpt-4o-mini")
        elif provider == "anthropic":
            valid, message = await _validate_anthropic_key(api_key, model or "claude-3-haiku-20240307")
        elif provider == "xai":
            valid, message = await _validate_xai_key(api_key, model or "grok-beta")
        elif provider == "deepseek":
            valid, message = await _validate_deepseek_key(api_key, model or "deepseek-chat")
        elif provider == "qwen":
            valid, message = await _validate_qwen_key(api_key, model or "qwen-turbo")
        elif provider == "venice":
            valid, message = await _validate_venice_key(api_key, model or "venice-2-13b")
        else:
            message = f"Unknown provider: {provider}"

        return APIResponse(
            success=True,
            data=ValidateKeyResponse(valid=valid, message=message),
            message="Validation complete",
        )
    except Exception as e:
        logger.error(f"Failed to validate API key: {e}")
        return APIResponse(
            success=True,
            data=ValidateKeyResponse(valid=False, message=f"Validation error: {str(e)}"),
            message="Validation complete",
        )


# ============================================================================
# API Key Validation Helpers
# ============================================================================


async def _validate_openai_key(api_key: str, model: str) -> tuple[bool, str]:
    """Validate OpenAI API key."""
    try:
        import openai

        client = openai.OpenAI(api_key=api_key)
        # Make a minimal request
        _response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        return True, "API key is valid"
    except openai.AuthenticationError:
        return False, "Invalid API key"
    except openai.RateLimitError:
        return True, "API key is valid (rate limited)"
    except Exception as e:
        return False, f"Validation failed: {str(e)}"


async def _validate_anthropic_key(api_key: str, model: str) -> tuple[bool, str]:
    """Validate Anthropic API key."""
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        _response = client.messages.create(
            model=model,
            max_tokens=5,
            messages=[{"role": "user", "content": "Hi"}],
        )
        return True, "API key is valid"
    except anthropic.AuthenticationError:
        return False, "Invalid API key"
    except anthropic.RateLimitError:
        return True, "API key is valid (rate limited)"
    except Exception as e:
        return False, f"Validation failed: {str(e)}"


async def _validate_xai_key(api_key: str, model: str) -> tuple[bool, str]:
    """Validate xAI API key."""
    try:
        import openai

        client = openai.OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        _response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        return True, "API key is valid"
    except openai.AuthenticationError:
        return False, "Invalid API key"
    except Exception as e:
        return False, f"Validation failed: {str(e)}"


async def _validate_deepseek_key(api_key: str, model: str) -> tuple[bool, str]:
    """Validate DeepSeek API key."""
    try:
        import openai

        client = openai.OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        _response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        return True, "API key is valid"
    except openai.AuthenticationError:
        return False, "Invalid API key"
    except Exception as e:
        return False, f"Validation failed: {str(e)}"


async def _validate_qwen_key(api_key: str, model: str) -> tuple[bool, str]:
    """Validate Qwen API key."""
    try:
        import openai

        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )
        _response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        return True, "API key is valid"
    except openai.AuthenticationError:
        return False, "Invalid API key"
    except Exception as e:
        return False, f"Validation failed: {str(e)}"


async def _validate_venice_key(api_key: str, model: str) -> tuple[bool, str]:
    """Validate Venice API key."""
    try:
        import openai

        client = openai.OpenAI(api_key=api_key, base_url="https://api.venice.ai/api/v1")
        _response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=5,
        )
        return True, "API key is valid"
    except openai.AuthenticationError:
        return False, "Invalid API key"
    except Exception as e:
        return False, f"Validation failed: {str(e)}"


# ============================================================================
# Legacy Config Models (for existing functionality)
# ============================================================================


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


# ============================================================================
# Legacy Config Endpoints
# ============================================================================


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
