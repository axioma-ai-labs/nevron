"""Agent-related schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentStatus(BaseModel):
    """Agent status response."""

    state: str
    personality: str
    goal: str
    mcp_enabled: bool
    mcp_connected_servers: int
    mcp_available_tools: int
    is_running: bool


class AgentInfo(BaseModel):
    """Detailed agent information."""

    personality: str
    goal: str
    state: str
    available_actions: List[str]
    total_actions_executed: int
    total_rewards: float
    last_action: Optional[str] = None
    last_action_time: Optional[datetime] = None


class ActionRequest(BaseModel):
    """Request to execute an action."""

    action: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ActionResponse(BaseModel):
    """Response from action execution."""

    action: str
    success: bool
    outcome: Optional[str] = None
    reward: float
    execution_time: float


class ActionHistoryItem(BaseModel):
    """Single item in action history."""

    timestamp: datetime
    action: str
    state: str
    outcome: Optional[str] = None
    reward: Optional[float] = None


class AgentContext(BaseModel):
    """Agent context information."""

    actions_history: List[ActionHistoryItem]
    last_state: str
    total_actions: int
    total_rewards: float
