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

### Configuration

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Add your LLM API key to `.env`:
```bash
# Choose one provider
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...
# or
XAI_API_KEY=xai-...
```

3. Configure your LLM provider:
```bash
LLM_PROVIDER=openai  # Options: openai, anthropic, xai, deepseek, qwen, venice, llama
LLM_MODEL=gpt-4o     # Model name for your provider
```

## Running Nevron

### Option 1: Full Stack (Recommended)

Run the agent, API, and dashboard together:

```bash
make dev-full
```

This starts:
- **Agent Process** - Autonomous agent runtime (writes state to `./nevron_state/`)
- **API Server** - FastAPI backend at http://localhost:8000
- **Dashboard** - Svelte UI at http://localhost:5173

### Option 2: Components Separately

Run each component in separate terminals:

```bash
# Terminal 1: Agent process
make run-agent

# Terminal 2: API server
make api

# Terminal 3: Dashboard
make dashboard
```

### Option 3: Dashboard Only (No Agent)

For development or monitoring without running the agent:

```bash
make dev
```

### Option 4: Agent Only (No Dashboard)

Run the agent in legacy coupled mode:

```bash
make run
```

## Architecture

Nevron uses a decoupled architecture where the API and Agent run as independent processes:

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dashboard     │────▶│   FastAPI        │────▶│  Shared State   │
│   (Svelte)      │     │   (Port 8000)    │     │  ./nevron_state │
│   Port 5173     │◀────│   + WebSocket    │◀────│                 │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  Agent Runner   │
                                                 │  (Independent)  │
                                                 └─────────────────┘
```

**Benefits:**
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
- **LLM Configuration** - Provider, model, temperature
- **Agent Settings** - Personality, goal, behavior
- **Actions** - Enable/disable available actions
- **Integrations** - Configure Twitter, Discord, Telegram, etc.
- **MCP Servers** - Add custom tool servers

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

| Provider | Models | Environment Variable |
|----------|--------|---------------------|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4-turbo, o1, o1-mini | `OPENAI_API_KEY` |
| Anthropic | claude-sonnet-4, claude-opus-4 | `ANTHROPIC_API_KEY` |
| xAI | grok-3, grok-3-fast, grok-2 | `XAI_API_KEY` |
| DeepSeek | deepseek-chat, deepseek-reasoner | `DEEPSEEK_API_KEY` |
| Qwen | qwen-max, qwen-plus, qwen-turbo | `QWEN_API_KEY` |
| Venice | llama-3.3-70b, qwen3-235b | `VENICE_API_KEY` |

## Integrations

Nevron supports various external services:

- **Social Media**: Twitter, Discord, Telegram, Slack, WhatsApp
- **Development**: GitHub
- **Storage**: Google Drive
- **Media**: Spotify, YouTube
- **Web3**: Lens Protocol
- **Search**: Tavily, Perplexity

Configure integrations via the dashboard Settings page or `.env` file.

## Documentation

For detailed documentation, visit: [https://axioma-ai-labs.github.io/nevron/](https://axioma-ai-labs.github.io/nevron/)

## License

This project is licensed under the Nevron Public License (NPL). See the [LICENSE](LICENSE) file for details.

---

Made with love by [Neurobro](https://neurobro.ai)
