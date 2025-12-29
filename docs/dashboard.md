# Dashboard

The Nevron Dashboard provides a web-based interface for monitoring and controlling your AI agent. It features a clean 3-page layout with real-time statistics, memory exploration, learning insights, and configuration management.

## Architecture

```
+-----------------------------------------------------------+
|                    Svelte Dashboard                        |
|  +-------------+  +-------------+  +-------------+        |
|  |   Control   |  |  Settings   |  |   Explore   |        |
|  |   (Home)    |  | (LLM Config)|  | (Mem/Learn) |        |
|  +------+------+  +------+------+  +------+------+        |
|         +----------------+----------------+                |
|                          | REST + WebSocket                |
+-----------------------------------------------------------+
                           |
+-----------------------------------------------------------+
|               FastAPI Backend (src/api/)                   |
|  +-------------------------------------------------------+ |
|  | Routers: agent, runtime, memory, learning,            | |
|  |          metacognition, mcp, config                   | |
|  +---------------------------+---------------------------+ |
|                              |                             |
|  +---------------------------+---------------------------+ |
|  | WebSocket Manager (real-time event streaming)         | |
|  +---------------------------+---------------------------+ |
+-----------------------------------------------------------+
                           |
           +---------------+---------------+
           |               |               |
     +-----v-----+   +-----v-----+   +-----v-----+
     |   Agent   |   |  Runtime  |   |  Memory   |
     +-----------+   +-----------+   +-----------+
```

## Quick Start

### Prerequisites

- Python 3.13+
- Node.js 20+
- Poetry (Python package manager)

### Installation

1. **Install Python dependencies:**
   ```bash
   make deps
   ```

2. **Install dashboard dependencies:**
   ```bash
   make dashboard-deps
   ```

### Running the Dashboard

#### Option 1: Development Mode (Recommended)

Run both API and dashboard with hot-reload:

```bash
make dev
```

This starts:

- **API**: http://localhost:8000
- **Dashboard**: http://localhost:5173

#### Option 2: Separate Terminals

**Terminal 1 - API:**
```bash
make api
```

**Terminal 2 - Dashboard:**
```bash
make dashboard
```

#### Option 3: Docker

```bash
make docker-up
```

This starts:

- **API**: http://localhost:8000
- **Dashboard**: http://localhost:3000

To stop:
```bash
make docker-down
```

## Dashboard Pages

### Control (Home)

The main dashboard for agent control and monitoring:

- **Agent Status Hero**: Current state (Running/Paused/Stopped) with uptime
- **Configuration Warning**: Banner prompting API key setup on first run
- **Control Buttons**: Start, Pause, and Stop the agent
- **Statistics Cards**: Events processed, success rate, uptime, memories
- **Agent Identity**: Current personality and goal display
- **Live Event Feed**: Real-time WebSocket events

### Settings

Configure your LLM provider and agent identity:

- **LLM Provider**: Select from OpenAI, Anthropic, xAI, DeepSeek, Qwen, Venice
- **API Key**: Secure input with test validation button
- **Model Selection**: Provider-specific model options
- **Agent Personality**: Define agent behavior and communication style
- **Agent Goal**: Set the primary objective
- **MCP Toggle**: Enable/disable Model Context Protocol integration

### Explore

Deep dive into agent systems with tabbed navigation:

#### Memory Tab
Explore the tri-memory system:
- **Episodes**: Time-indexed experiences with emotional valence
- **Facts**: Knowledge graph entries (subject-predicate-object)
- **Concepts**: Abstract concepts and their properties
- **Skills**: Learned procedural patterns
- **Memory Consolidation**: Trigger memory consolidation

#### Learning Tab
View the agent's learning progress:
- **Training History**: Outcomes with success rates and bias changes
- **Self-Critiques**: Generated critiques from failures
- **Improvement Suggestions**: AI-generated recommendations
- **Failure Analysis**: Analyze patterns in failures

#### Runtime Tab
Monitor the event-driven runtime:
- **Control Buttons**: Start, Pause, Resume, Stop
- **Statistics**: Queue size, events processed, uptime
- **Queue Details**: Priority distribution and event types
- **Scheduler**: Scheduled tasks with next run times
- **Background Processes**: Consolidation and cleanup jobs

## API Reference

The dashboard communicates with the FastAPI backend. Full API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/agent/status` | Agent state and info |
| `POST /api/v1/runtime/start` | Start the agent |
| `POST /api/v1/runtime/stop` | Stop the agent |
| `POST /api/v1/runtime/pause` | Pause the agent |
| `GET /api/v1/runtime/statistics` | Runtime stats |
| `GET /api/v1/memory/statistics` | Memory system stats |
| `POST /api/v1/memory/recall` | Query memories |
| `GET /api/v1/learning/statistics` | Learning stats |
| `GET /api/v1/config/ui` | Get UI configuration |
| `PUT /api/v1/config/ui` | Save UI configuration |
| `GET /api/v1/config/ui/exists` | Check if config exists |
| `POST /api/v1/config/ui/validate` | Validate API key |
| `WS /ws/{client_id}` | WebSocket for real-time events |

## WebSocket Events

The dashboard receives real-time events via WebSocket:

```typescript
// Event types
type WSMessageType =
  | 'runtime.state_change'
  | 'runtime.stats_update'
  | 'agent.action'
  | 'agent.state_change'
  | 'learning.outcome'
  | 'learning.critique'
  | 'memory.stored'
  | 'memory.consolidated'
  | 'mcp.connected'
  | 'mcp.disconnected'
  | 'system.log'
  | 'system.error'
  | 'system.heartbeat';
```

## Configuration

### First-Run Setup

On first launch, the dashboard will display a configuration warning banner. Navigate to Settings to:

1. Select your LLM provider
2. Enter your API key (use "Test" button to validate)
3. Choose a model
4. Set agent personality and goal
5. Save configuration

The configuration is stored in `nevron_config.json` in the project root.

### API Configuration

Environment variables for the API (in `.env`):

```bash
# API Settings
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=your-optional-api-key

# CORS (for dashboard)
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

### Dashboard Configuration

The dashboard reads the API URL from environment:

```bash
# dashboard/.env
PUBLIC_API_URL=http://localhost:8000
```

## Docker Deployment

### Build Images

```bash
make docker-build
```

### Start Services

```bash
make docker-up
```

### View Logs

```bash
make docker-logs
```

### Stop Services

```bash
make docker-down
```

### Docker Compose Services

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI backend |
| `dashboard` | 3000 | Svelte frontend |

## Development

### Project Structure

```
nevron/
├── src/api/                    # FastAPI Backend
│   ├── main.py                 # App entry point
│   ├── config.py               # API settings
│   ├── dependencies.py         # Dependency injection
│   ├── routers/                # API route handlers
│   │   ├── agent.py
│   │   ├── runtime.py
│   │   ├── memory.py
│   │   ├── learning.py
│   │   ├── metacognition.py
│   │   ├── mcp.py
│   │   └── config.py
│   ├── schemas/                # Pydantic models
│   └── websocket/              # WebSocket handling
│       ├── manager.py
│       └── events.py
│
├── src/core/
│   └── ui_config.py            # Dashboard config management
│
├── dashboard/                   # Svelte Frontend
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api/            # API client
│   │   │   └── components/     # UI components
│   │   └── routes/             # SvelteKit pages
│   │       ├── +page.svelte    # Control (Home)
│   │       ├── settings/       # Settings page
│   │       └── explore/        # Explore page
│   └── static/
│
└── docker/
    ├── Dockerfile.api
    └── Dockerfile.dashboard
```

### Building for Production

```bash
# Build dashboard
make dashboard-build

# Build Docker images
make docker-build
```

## Troubleshooting

### API won't start

1. Check if port 8000 is in use:
   ```bash
   lsof -i :8000
   ```

2. Verify dependencies are installed:
   ```bash
   make deps
   ```

### Dashboard won't connect to API

1. Ensure API is running on port 8000
2. Check CORS settings in API config
3. Verify `PUBLIC_API_URL` in dashboard environment

### WebSocket disconnects

The dashboard auto-reconnects on WebSocket disconnection. If issues persist:

1. Check API logs for WebSocket errors
2. Verify no firewall blocking WebSocket connections
3. Try refreshing the dashboard page

### API Key Validation Fails

1. Verify the API key is correct for the selected provider
2. Check network connectivity to the provider's API
3. Ensure the selected model is available for your API key tier
