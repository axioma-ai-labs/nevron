# Nevron Architecture Documentation

This document provides a comprehensive overview of the Nevron AI agent framework architecture, its core systems, configuration, and how to extend it.

## Table of Contents

1. [What is Nevron?](#what-is-nevron)
2. [Core Systems](#core-systems)
3. [Configuration System](#configuration-system)
4. [Dashboard and API](#dashboard-and-api)
5. [Adding New Actions/Tools](#adding-new-actionstools)
6. [Agent Cycle Monitoring](#agent-cycle-monitoring)

---

## What is Nevron?

Nevron is a lightweight Python framework for building autonomous AI agents. The framework provides a modular architecture where specialized modules work together in a continuous runtime loop.

### The Runtime Loop

The agent operates in a continuous loop with the following phases:

```
┌─────────────────────────────────────────────────────────┐
│                    RUNTIME LOOP                         │
├─────────────────────────────────────────────────────────┤
│  1. PLANNING                                            │
│     └─ LLM analyzes state + history → selects action   │
│                          ↓                              │
│  2. EXECUTION                                           │
│     └─ Action executor runs the chosen action          │
│                          ↓                              │
│  3. LEARNING (RLAIF)                                    │
│     └─ Collect reward, generate critique, learn        │
│                          ↓                              │
│  4. MEMORY                                              │
│     └─ Store experience, update context                │
│                          ↓                              │
│  5. REST                                                │
│     └─ Wait configured interval before next cycle      │
└─────────────────────────────────────────────────────────┘
```

Each cycle is logged to the database for monitoring and debugging.

---

## Core Systems

### Planning Module (`src/planning/`)

The Planning Module uses an LLM to decide what action to take based on:
- Current agent state
- Recent action history
- Agent's personality and goal
- Available actions (including MCP tools)

**Key Features:**
- Context-aware action selection
- MCP tool integration
- Tool argument planning

**Flow:**
```
State + History + Available Actions
           ↓
    LLM Planning Prompt
           ↓
    Selected Action + Reasoning
```

### Execution Module (`src/execution/`)

Maps actions to their executor implementations. Supports both legacy `ActionExecutor` classes and MCP tools.

**Structure:**
```
src/execution/
├── base.py                    # Base classes
├── execution_module.py        # Main module
├── development_executors.py   # GitHub, Google Drive
├── ecommerce_executors.py     # Shopify
├── media_executors.py         # YouTube, Spotify
├── research_executors.py      # Tavily, Perplexity
├── social_media_executors.py  # Twitter, Discord, etc.
└── workflows_executors.py     # Complex workflows
```

**Action Registration:**
Actions are defined in `src/core/defs.py` as the `AgentAction` enum and mapped to executors in `execution_module.py`.

### Learning Module (`src/feedback/`)

Implements Reinforcement Learning from AI Feedback (RLAIF):

1. **Reward Collection**: Score action outcomes
2. **Critique Generation**: Analyze failures
3. **Lesson Learning**: Extract patterns for improvement
4. **Bias Updates**: Adjust action selection probabilities

### Memory Module (`src/memory/`)

Tri-Memory architecture with three memory types:

| Type | Purpose | Storage |
|------|---------|---------|
| **Episodic** | Past experiences and events | Vector DB |
| **Semantic** | Facts and concepts | Vector DB |
| **Procedural** | Skills and action patterns | Vector DB |

**Backends:**
- Qdrant (recommended for production)
- ChromaDB (good for development)

**Memory Consolidation:**
Periodic process that:
- Extracts facts from episodes
- Updates skill confidence
- Prunes low-importance memories

### Metacognition Module (`src/metacognition/`)

Self-monitoring capabilities:

- **Loop Detection**: Detects repetitive action patterns
- **Failure Prediction**: Predicts high-risk actions
- **Intervention**: Suggests alternatives when stuck
- **Human Handoff**: Escalates when necessary

---

## Configuration System

Nevron uses a hierarchical configuration system with three levels:

### Configuration Hierarchy

```
Priority 1: .env file (overrides everything)
    ↓
Priority 2: nevron_config.json (UI-configured)
    ↓
Priority 3: Code defaults (fallback)
```

### Environment Variables (`.env`)

For developers and production deployments. See `.env.example` for all options:

```bash
# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Agent Settings
AGENT_PERSONALITY="You are a helpful AI assistant."
AGENT_GOAL="Help users accomplish their tasks."
AGENT_REST_TIME=300

# Integration Credentials
TWITTER_API_KEY=...
TELEGRAM_BOT_TOKEN=...
```

### UI Configuration (`nevron_config.json`)

Managed through the dashboard, stored as JSON:

```json
{
  "llm_provider": "openai",
  "llm_api_key": "sk-...",
  "llm_model": "gpt-4o-mini",
  "agent_name": "Nevron",
  "agent_personality": "...",
  "agent_goal": "...",
  "agent_behavior": {
    "rest_time": 300,
    "max_consecutive_failures": 3,
    "verbosity": "normal"
  },
  "enabled_actions": ["idle", "analyze_news", "post_tweet"],
  "integrations": {
    "twitter": {"api_key": "...", ...},
    "telegram": {"bot_token": "...", ...}
  },
  "mcp_enabled": false,
  "mcp_servers": []
}
```

### Configuration Scope

| Category | Settings |
|----------|----------|
| **LLM** | Provider, API key, model |
| **Agent Identity** | Name, personality, goal |
| **Agent Behavior** | Rest time, failure threshold, verbosity |
| **Actions** | Which actions are enabled |
| **Integrations** | Credentials for each service |
| **MCP** | Enable/disable, server configurations |

---

## Dashboard and API

### Dashboard Structure

The Svelte-based dashboard provides a web interface:

```
dashboard/src/routes/
├── +layout.svelte      # Main layout with sidebar
├── +page.svelte        # Control page (start/stop agent)
├── activity/
│   └── +page.svelte    # Cycle monitoring
├── settings/
│   └── +page.svelte    # Configuration UI
└── explore/
    └── +page.svelte    # Memory exploration
```

### API Endpoints

The FastAPI backend (`src/api/`) provides:

#### Agent Control
- `GET /api/v1/agent/status` - Agent status
- `POST /api/v1/agent/start` - Start agent
- `POST /api/v1/agent/stop` - Stop agent

#### Configuration
- `GET /api/v1/config/ui` - Get configuration
- `PUT /api/v1/config/ui` - Update configuration
- `GET /api/v1/config/ui/actions` - List available actions
- `GET /api/v1/config/ui/integrations/status` - Check integration status

#### Cycle Monitoring
- `GET /api/v1/cycles` - List recent cycles
- `GET /api/v1/cycles/{id}` - Get cycle details
- `GET /api/v1/cycles/stats` - Aggregate statistics

#### Other
- `GET /api/v1/memory/*` - Memory operations
- `GET /api/v1/learning/*` - Learning statistics
- `GET /api/v1/metacognition/*` - Metacognition state
- `GET /api/v1/mcp/*` - MCP tool management

### WebSocket Events

Real-time updates via WebSocket at `/ws/{client_id}`:

```javascript
// Subscribe to all events
ws.send(JSON.stringify({ action: 'subscribe', events: ['*'] }));

// Event types
{
  type: 'cycle_complete',
  data: { cycle_id, action, success, reward, duration }
}
```

---

## Adding New Actions/Tools

### Step 1: Define the Action

Add to `src/core/defs.py`:

```python
class AgentAction(str, Enum):
    # ... existing actions
    MY_NEW_ACTION = "my_new_action"
```

### Step 2: Create the Executor

Create in appropriate executor file (e.g., `src/execution/my_executors.py`):

```python
from src.execution.base import ActionExecutor

class MyNewActionExecutor(ActionExecutor):
    """Execute my new action."""

    def get_required_context(self) -> list[str]:
        """Return list of required context fields."""
        return ["some_field"]

    async def execute(self, context: dict) -> tuple[bool, str | None]:
        """Execute the action.

        Args:
            context: Dictionary with required context data

        Returns:
            Tuple of (success, outcome_message)
        """
        try:
            # Your action logic here
            result = await self._do_something(context)
            return True, f"Action completed: {result}"
        except Exception as e:
            return False, str(e)
```

### Step 3: Register the Executor

Add to `src/execution/execution_module.py`:

```python
from src.execution.my_executors import MyNewActionExecutor

ACTION_EXECUTOR_MAP: Dict[AgentAction, Type[ActionExecutor]] = {
    # ... existing mappings
    AgentAction.MY_NEW_ACTION: MyNewActionExecutor,
}
```

### Step 4: Add Integration Mapping (if needed)

If your action requires integration credentials, add to `src/core/ui_config.py`:

```python
ACTION_INTEGRATION_MAP: Dict[str, str] = {
    # ... existing mappings
    "my_new_action": "my_service",
}
```

### Step 5: Add Tests

Create `tests/execution/test_my_executors.py`:

```python
import pytest
from src.execution.my_executors import MyNewActionExecutor

@pytest.mark.asyncio
async def test_my_new_action():
    executor = MyNewActionExecutor()
    success, outcome = await executor.execute({"some_field": "value"})
    assert success
```

---

## Agent Cycle Monitoring

### Cycle Logging

Every agent cycle is logged to SQLite (`nevron_cycles.db`) with full context:

```python
@dataclass
class CycleLog:
    # Identification
    cycle_id: str
    timestamp: str

    # Planning phase
    planning_input_state: str
    planning_input_recent_actions: List[str]
    planning_output_action: str
    planning_output_reasoning: Optional[str]
    planning_duration_ms: int

    # Execution phase
    action_name: str
    execution_result: Dict[str, Any]
    execution_success: bool
    execution_error: Optional[str]
    execution_duration_ms: int

    # Learning phase
    reward: float
    critique: Optional[str]
    lesson_learned: Optional[str]

    # Metadata
    total_duration_ms: int
    agent_state_after: str
```

### Querying Cycles

Via API:
```bash
# Get recent cycles with filtering
GET /api/v1/cycles?page=1&action=post_tweet&success=true

# Get statistics
GET /api/v1/cycles/stats

# Get specific cycle
GET /api/v1/cycles/{cycle_id}
```

Via Python:
```python
from src.core.cycle_logger import get_cycle_logger

logger = get_cycle_logger()

# Get recent cycles
cycles = logger.get_recent_cycles(limit=50, action_filter="post_tweet")

# Get stats
stats = logger.get_stats()
print(f"Success rate: {stats.success_rate}%")
```

### Dashboard Monitoring

The Activity page (`/activity`) provides:
- Real-time cycle feed
- Success rate and metrics
- Action distribution
- Expandable cycle details
- Filtering by action/status

---

## Project Structure

```
nevron/
├── src/
│   ├── agent.py              # Main agent runtime
│   ├── api/                  # FastAPI backend
│   │   ├── main.py
│   │   ├── routers/          # API endpoints
│   │   └── websocket/        # Real-time events
│   ├── core/
│   │   ├── config.py         # Environment config
│   │   ├── ui_config.py      # UI config
│   │   ├── cycle_logger.py   # Cycle logging
│   │   └── defs.py           # Enums and constants
│   ├── execution/            # Action executors
│   ├── feedback/             # Learning/RLAIF
│   ├── memory/               # Tri-memory system
│   ├── metacognition/        # Self-monitoring
│   ├── mcp/                  # MCP integration
│   ├── planning/             # Action planning
│   ├── tools/                # Integration clients
│   └── workflows/            # Complex workflows
├── dashboard/                # Svelte frontend
│   └── src/
│       ├── lib/
│       │   ├── api/          # API client
│       │   └── components/   # UI components
│       └── routes/           # Pages
├── tests/                    # Test suite
└── docs/                     # Documentation
```

---

## Best Practices

1. **Configuration**: Use `.env` for secrets and development, UI config for user-facing settings
2. **Actions**: Keep executors focused and testable
3. **Memory**: Use appropriate memory types for different information
4. **Monitoring**: Check cycle logs when debugging agent behavior
5. **MCP**: Prefer MCP tools for new integrations when possible

---

## Further Reading

- [MCP Specification](https://modelcontextprotocol.io/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SvelteKit Documentation](https://kit.svelte.dev/)
