# Nevron - Lightweight AI Agent Framework

[![CI](https://github.com/axioma-ai-labs/nevron/actions/workflows/main.yml/badge.svg)](https://github.com/axioma-ai-labs/nevron/actions/workflows/main.yml)
[![codecov](https://codecov.io/gh/axioma-ai-labs/nevron/branch/main/graph/badge.svg?token=krO46pgB7P)](https://codecov.io/gh/axioma-ai-labs/nevron)
[![Build Docker image](https://github.com/axioma-ai-labs/nevron/actions/workflows/docker.yml/badge.svg)](https://github.com/axioma-ai-labs/nevron/actions/workflows/docker.yml)
[![Docs](https://img.shields.io/badge/Nevron-Docs-blue)](https://axioma-ai-labs.github.io/nevron/)

Build flexible autonomous AI agents effortlessly. Set up in 2 minutes, run in 5, deploy in 10.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for dashboard)
- Poetry (`pip install poetry`)

### Installation

```bash
# Clone the repository
git clone https://github.com/axioma-ai-labs/nevron.git
cd nevron

# Install Python dependencies
make deps

# Install dashboard dependencies
make dashboard-deps
```

### Running Nevron

```bash
# Start everything (Agent + API + Dashboard)
make dev-full
```

This starts:
- **Dashboard**: http://localhost:5173
- **API**: http://localhost:8000
- **Agent**: Running in background

### Configuration

**All configuration is done through the Dashboard UI** - no `.env` file needed!

1. Open the dashboard at http://localhost:5173
2. Go to **Settings** page
3. Configure your LLM provider and API key
4. Set up agent personality and goals
5. Enable integrations as needed

Configuration is saved to `nevron_config.json` and loaded automatically.

## Architecture

Nevron uses a decoupled architecture where the API and Agent run as independent processes:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dashboard     │────▶│   FastAPI        │────▶│  Shared State   │
│   (Svelte)      │     │   (Port 8000)    │     │  ./nevron_state │
│   Port 5173     │◀────│   + WebSocket    │◀────│                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                              nevron_config.json ─────────┤
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  Agent Runner   │
                                                 │  (Independent)  │
                                                 └─────────────────┘
```

**Benefits:**
- Configure everything from the UI
- Restart API without stopping the agent
- Multiple dashboards can connect simultaneously
- Agent continues running if dashboard disconnects

## Dashboard Features

### Overview Page
- Agent status (running/paused/stopped)
- Start, pause, stop controls
- Real-time statistics
- Live event feed via WebSocket

### Activity Page
- Agent cycle history (Plan → Execute → Learn → Remember)
- Detailed cycle inspection
- Performance metrics

### Settings Page
- **LLM Configuration** - Provider, model, API key
- **Agent Settings** - Personality, goal, behavior
- **Actions** - Enable/disable available actions
- **Integrations** - Configure Twitter, Discord, Telegram, etc.
- **MCP Servers** - Add custom tool servers

## Other Run Options

| Command | What it does |
|---------|-------------|
| `make dev-full` | Agent + API + Dashboard (recommended) |
| `make dev` | API + Dashboard only (no agent) |
| `make run-agent` | Agent process only |
| `make api` | API server only |
| `make dashboard` | Dashboard only |

## Available Commands

```bash
# Development
make deps            # Install Python dependencies
make dashboard-deps  # Install dashboard dependencies
make format          # Format code
make lint            # Run linting
make test            # Run tests

# Running
make run             # Run agent (legacy mode)
make run-agent       # Run agent process (decoupled)
make api             # Run API server
make dashboard       # Run dashboard
make dev             # Run API + dashboard
make dev-full        # Run agent + API + dashboard

# Docker
make docker-up       # Start all services
make docker-down     # Stop all services
make docker-logs     # View logs
```

## Supported LLM Providers

| Provider | Models |
|----------|--------|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4-turbo, o1, o1-mini |
| Anthropic | claude-sonnet-4, claude-opus-4 |
| xAI | grok-3, grok-3-fast, grok-2 |
| DeepSeek | deepseek-chat, deepseek-reasoner |
| Qwen | qwen-max, qwen-plus, qwen-turbo |
| Venice | llama-3.3-70b, qwen3-235b |

## Integrations

Nevron supports various external services (configure in Settings):

- **Social Media**: Twitter, Discord, Telegram, Slack, WhatsApp
- **Development**: GitHub
- **Storage**: Google Drive
- **Media**: Spotify, YouTube
- **Web3**: Lens Protocol
- **Search**: Tavily, Perplexity

## Documentation

For detailed documentation, visit: [https://axioma-ai-labs.github.io/nevron/](https://axioma-ai-labs.github.io/nevron/)

## License

This project is licensed under the Nevron Public License (NPL). See the [LICENSE](LICENSE) file for details.

---

Made with love by [Neurobro](https://neurobro.ai)
