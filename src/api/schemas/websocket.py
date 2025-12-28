"""WebSocket message schemas."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class WSMessageType(str, Enum):
    """Types of WebSocket messages."""

    # Runtime events
    RUNTIME_STATE_CHANGE = "runtime.state_change"
    RUNTIME_STATS_UPDATE = "runtime.stats_update"

    # Event queue
    EVENT_QUEUED = "event.queued"
    EVENT_PROCESSING = "event.processing"
    EVENT_PROCESSED = "event.processed"
    EVENT_FAILED = "event.failed"

    # Agent events
    AGENT_ACTION = "agent.action"
    AGENT_STATE_CHANGE = "agent.state_change"

    # Learning events
    LEARNING_OUTCOME = "learning.outcome"
    CRITIQUE_GENERATED = "learning.critique"
    LESSON_CREATED = "learning.lesson"

    # Metacognition events
    INTERVENTION = "metacognition.intervention"
    CONFIDENCE_UPDATE = "metacognition.confidence"
    LOOP_DETECTED = "metacognition.loop"

    # Memory events
    MEMORY_STORED = "memory.stored"
    MEMORY_CONSOLIDATED = "memory.consolidated"

    # MCP events
    MCP_SERVER_CONNECTED = "mcp.connected"
    MCP_SERVER_DISCONNECTED = "mcp.disconnected"
    MCP_TOOL_EXECUTED = "mcp.tool_executed"

    # System events
    LOG = "system.log"
    ERROR = "system.error"
    HEARTBEAT = "system.heartbeat"


class WSMessage(BaseModel):
    """WebSocket message."""

    type: WSMessageType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any] = Field(default_factory=dict)


class WSSubscription(BaseModel):
    """WebSocket subscription request."""

    action: str  # "subscribe" or "unsubscribe"
    events: List[str] = Field(default_factory=lambda: ["*"])


class WSPing(BaseModel):
    """WebSocket ping message."""

    action: str = "ping"


class WSPong(BaseModel):
    """WebSocket pong response."""

    action: str = "pong"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
