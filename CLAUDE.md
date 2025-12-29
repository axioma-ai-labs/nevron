# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nevron is a lightweight Python framework for building autonomous AI agents. The framework provides a modular architecture with planning, execution, memory, and feedback systems that work together in a runtime loop.

**Key Architecture:** The Agent, API, and Dashboard run as independent processes, communicating via shared state files (`./nevron_state/`). The agent starts in **stopped** state and must be started via the dashboard or API.

## Common Commands

```bash
# Install dependencies
make deps
make dashboard-deps    # For dashboard

# Development (recommended)
make dev-full         # Agent + API + Dashboard (all-in-one)
make dev              # API + Dashboard only (no agent)

# Individual components
make run-agent        # Agent process only
make api              # API server only
make dashboard        # Dashboard only

# Legacy mode (no dashboard)
make run              # Agent with .env config

# Testing & Quality
make test             # Run all tests with coverage
make format           # Format code
make lint             # Run linting (ruff, isort, mypy)
make docs             # Serve documentation locally

# Run specific tests
poetry run pytest tests/path/to/test_file.py -v
poetry run pytest tests/path/to/test_file.py::test_function_name -v
```

## Architecture

### Decoupled Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Dashboard     │────▶│   FastAPI        │────▶│  Shared State   │
│   (Svelte)      │     │   (Port 8000)    │     │  ./nevron_state │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                              nevron_config.json ─────────┤
                                                          ▼
                                                 ┌─────────────────┐
                                                 │  Agent Runner   │
                                                 │  (Independent)  │
                                                 └─────────────────┘
```

### Key Components

- **AgentRunner** (`src/agent_runner.py`) - Standalone process that runs agent cycles, polls for commands
- **SharedStateManager** (`src/core/agent_state.py`) - File-based IPC for state sharing
- **CommandQueue** (`src/core/agent_commands.py`) - File-based command queue for agent control
- **API routers** (`src/api/routers/`) - FastAPI endpoints for agent, config, cycles, memory, etc.

### Agent Runtime Loop (`src/agent.py`)

The `Agent` class orchestrates the main runtime loop:
1. **Planning** - LLM decides next action based on current state and history
2. **Execution** - Action executor runs the chosen action
3. **Feedback** - Collect reward signal from action outcome
4. **Context Update** - Persist state and action history

### Agent Lifecycle

The agent starts in **stopped** state and waits for commands:
- **START** - Begin running cycles
- **PAUSE** - Pause cycles (can resume)
- **RESUME** - Resume paused cycles
- **STOP** - Stop cycles (can restart)

Control via dashboard or API endpoints: `POST /api/v1/agent/{start,stop,pause,resume}`

### Core Modules

- **PlanningModule** (`src/planning/`) - Uses LLM to select actions from `AgentAction` enum based on state and recent action history
- **ExecutionModule** (`src/execution/`) - Maps `AgentAction` to `ActionExecutor` subclasses. Each executor implements `execute()` and `get_required_context()`
- **MemoryModule** (`src/memory/`) - Vector store for semantic memory. Supports Qdrant and ChromaDB backends
- **FeedbackModule** (`src/feedback/`) - Collects and processes action rewards
- **ContextManager** (`src/context/`) - Persists agent state and action history to JSON

### LLM Providers (`src/llm/`)

The `LLM` class routes to provider-specific implementations:
- OpenAI, Anthropic, xAI, DeepSeek, Qwen, Venice
- Llama (via Ollama, Fireworks, llama-api, OpenRouter, or local)

Set provider via dashboard settings or `LLM_PROVIDER` env var.

### Tools (`src/tools/`)

Integration clients for external services: Twitter, Discord, Telegram, Slack, WhatsApp, GitHub, Google Drive, Shopify, Spotify, YouTube, Lens Protocol, Tavily, Perplexity.

### Workflows (`src/workflows/`)

Complex multi-step actions: `analyze_signal.py`, `research_news.py`.

## Configuration

### UI Configuration (Recommended)
Configuration via dashboard is saved to `nevron_config.json`. Managed by `src/core/ui_config.py`.

### Environment Variables
Settings in `src/core/config.py` via pydantic-settings, loaded from `.env`:
- `LLM_PROVIDER` - LLM backend (openai, anthropic, xai, llama, deepseek, qwen, venice)
- `MEMORY_BACKEND_TYPE` - Vector store (chroma, qdrant)
- `AGENT_PERSONALITY`, `AGENT_GOAL` - Agent behavior prompts
- API keys for each integration

**Priority:** `.env` > `nevron_config.json` > code defaults

## Adding New Actions

1. Add action to `AgentAction` enum in `src/core/defs.py`
2. Create executor class extending `ActionExecutor` in appropriate `src/execution/*_executors.py`
3. Register in `ACTION_EXECUTOR_MAP` in `src/execution/execution_module.py`
4. Add corresponding test in `tests/execution/`

## Docker

```bash
# Run with docker-compose (includes Qdrant and Ollama)
docker-compose up
```
