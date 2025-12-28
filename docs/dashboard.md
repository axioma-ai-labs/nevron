# Dashboard

The Nevron Dashboard provides a web-based interface for monitoring and controlling your AI agent. It includes real-time statistics, memory exploration, learning insights, and MCP server management.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Svelte Dashboard                       │
│  ┌─────────┬─────────┬─────────┬─────────┬───────────┐  │
│  │ Agent   │ Runtime │ Memory  │Learning │   MCP     │  │
│  │ Control │ Monitor │ Explorer│ Insights│  Manager  │  │
│  └────┬────┴────┬────┴────┬────┴────┬────┴─────┬─────┘  │
│       └─────────┴─────────┴─────────┴──────────┘        │
│                         │ REST + WebSocket               │
└─────────────────────────┼───────────────────────────────┘
                          │
┌─────────────────────────┼───────────────────────────────┐
│              FastAPI Backend (src/api/)                  │
│  ┌──────────────────────┴──────────────────────────┐    │
│  │ Routers: agent, runtime, memory, learning,      │    │
│  │          metacognition, mcp, config             │    │
│  └──────────────────────┬──────────────────────────┘    │
│                         │                                │
│  ┌──────────────────────┴──────────────────────────┐    │
│  │ WebSocket Manager (real-time event streaming)   │    │
│  └──────────────────────┬──────────────────────────┘    │
└─────────────────────────┼───────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    ┌─────▼─────┐  ┌──────▼──────┐ ┌──────▼──────┐
    │   Agent   │  │  Runtime    │ │   Memory    │
    │           │  │             │ │             │
    └───────────┘  └─────────────┘ └─────────────┘
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

### Home Dashboard

The main dashboard provides an overview of your agent's status:

- **Agent Status**: Current state (idle/running/paused)
- **Runtime Statistics**: Events processed, queue size, uptime
- **Live Event Feed**: Real-time WebSocket events

### Agent Control

Manage your agent's lifecycle:

- **Start/Stop/Pause**: Control agent execution
- **Execute Actions**: Manually trigger agent actions
- **Action History**: View recent actions and their outcomes

### Runtime Monitor

Monitor the event-driven runtime:

- **Queue Statistics**: Current queue size, processed events
- **Scheduler**: View scheduled tasks and next run times
- **Background Processes**: Monitor consolidation, cleanup jobs

### Memory Explorer

Explore the tri-memory system:

- **Episodic Memory**: Time-indexed experiences
- **Semantic Memory**: Facts and knowledge graph
- **Procedural Memory**: Learned skills and patterns
- **Search**: Query across all memory types

### Learning Insights

View the agent's learning progress:

- **Training History**: Success rates over time
- **Self-Critiques**: Generated critiques from failures
- **Lessons Learned**: Extracted patterns and improvements
- **Suggestions**: AI-generated improvement recommendations

### MCP Manager

Manage Model Context Protocol servers:

- **Server Status**: Connected/disconnected state
- **Available Tools**: List of tools per server
- **Tool Execution**: Execute tools directly from the UI

## API Reference

The dashboard communicates with the FastAPI backend. Full API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/agent/status` | Agent state and info |
| `POST /api/v1/agent/start` | Start the agent |
| `POST /api/v1/agent/stop` | Stop the agent |
| `GET /api/v1/runtime/statistics` | Runtime stats |
| `GET /api/v1/memory/statistics` | Memory system stats |
| `POST /api/v1/memory/recall` | Query memories |
| `GET /api/v1/learning/statistics` | Learning stats |
| `GET /api/v1/mcp/servers` | MCP server status |
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
├── dashboard/                   # Svelte Frontend
│   ├── src/
│   │   ├── lib/
│   │   │   ├── api/            # API client
│   │   │   ├── stores/         # Svelte stores
│   │   │   └── components/     # UI components
│   │   └── routes/             # SvelteKit pages
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
