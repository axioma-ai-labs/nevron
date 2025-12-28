# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Nevron is a lightweight Python framework for building autonomous AI agents. The framework provides a modular architecture with planning, execution, memory, and feedback systems that work together in a runtime loop.

## Common Commands

```bash
# Install dependencies
make deps

# Run the agent
make run

# Run all tests with coverage
make test

# Run a single test file
poetry run pytest tests/path/to/test_file.py -v

# Run a specific test
poetry run pytest tests/path/to/test_file.py::test_function_name -v

# Format code
make format

# Run linting (ruff, isort, mypy)
make lint

# Serve documentation locally
make docs
```

## Architecture

### Agent Runtime Loop (`src/agent.py`)

The `Agent` class orchestrates the main runtime loop:
1. **Planning** - LLM decides next action based on current state and history
2. **Execution** - Action executor runs the chosen action
3. **Feedback** - Collect reward signal from action outcome
4. **Context Update** - Persist state and action history

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

Set provider via `LLM_PROVIDER` env var.

### Tools (`src/tools/`)

Integration clients for external services: Twitter, Discord, Telegram, Slack, WhatsApp, GitHub, Google Drive, Shopify, Spotify, YouTube, Lens Protocol, Tavily, Perplexity.

### Workflows (`src/workflows/`)

Complex multi-step actions: `analyze_signal.py`, `research_news.py`.

## Configuration

All settings in `src/core/config.py` via pydantic-settings, loaded from `.env`:
- `LLM_PROVIDER` - LLM backend (openai, anthropic, xai, llama, deepseek, qwen, venice)
- `MEMORY_BACKEND_TYPE` - Vector store (chroma, qdrant)
- `AGENT_PERSONALITY`, `AGENT_GOAL` - Agent behavior prompts
- API keys for each integration

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
