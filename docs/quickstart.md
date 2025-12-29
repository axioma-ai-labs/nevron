# Quickstart Guide

This guide will help you get Nevron, your autonomous AI agent, running quickly. Choose the setup path that best suits your needs:

- [Local Setup with Dashboard](#local-setup-with-dashboard) (Recommended for development)
- [Docker Setup](#docker-setup) (Recommended for production)
- [Legacy Setup](#legacy-setup) (No dashboard, `.env` configuration)

## Prerequisites

General requirements:
- For local setup: **Python 3.11+**, **Node.js 18+**, and **Poetry**
- For Docker setup: **Docker** and **Docker Compose**

-----

## Local Setup with Dashboard

The recommended way to run Nevron with full UI control and configuration.

### 1. Clone & Install

```bash
# Clone the repository
git clone https://github.com/axioma-ai-labs/nevron.git
cd nevron

# Install Python dependencies
make deps

# Install dashboard dependencies
make dashboard-deps
```

### 2. Start Everything

```bash
make dev-full
```

This starts:
- **Dashboard**: http://localhost:5173
- **API**: http://localhost:8000
- **Agent**: Running in background (starts in stopped state)

### 3. Configure via Dashboard

1. Open the dashboard at http://localhost:5173
2. You'll see a configuration banner - click **Settings**
3. Select your LLM provider (OpenAI, Anthropic, xAI, etc.)
4. Enter your API key and click **Test** to validate
5. Choose a model from the dropdown
6. Set your agent's personality and goal
7. Click **Save Configuration**

Configuration is saved to `nevron_config.json` - no `.env` file needed!

### 4. Control the Agent

Back on the **Control** page:
1. Click **Start** to begin the agent runtime loop
2. Use **Pause** to temporarily stop cycles (agent remains ready)
3. Use **Stop** to fully stop the agent (can restart with Start)
4. Watch the live event feed for real-time activity

The agent starts in **stopped** state and waits for you to start it from the dashboard. This gives you full control over when cycles begin.

-----

## Docker Setup

Get Nevron running with Docker in 3 steps:

### 1. Pull & Setup

```bash
docker pull axiomai/nevron:latest

# Create volumes
mkdir -p volumes/nevron/logs
mkdir -p volumes/qdrant/data
mkdir -p volumes/ollama/models
```

### 2. Configure

For Docker, create a `.env` file with your LLM configuration:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# LLM configuration (choose one provider)
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here

# Or use local Ollama
# LLM_PROVIDER=llama
# LLAMA_PROVIDER=ollama
# LLAMA_OLLAMA_MODEL=llama3:8b-instruct

# Memory configuration
MEMORY_BACKEND_TYPE=qdrant

# Agent settings
AGENT_PERSONALITY="You are Nevron - an autonomous AI agent."
AGENT_GOAL="You provide high-quality research and analysis."
AGENT_REST_TIME=300
```

### 3. Run

```bash
docker compose up -d
```

Access the dashboard at http://localhost:3000 (API at http://localhost:8000).

-----

## Legacy Setup

For running the agent without the dashboard, using `.env` configuration only.

### 1. Clone & Install

```bash
git clone https://github.com/axioma-ai-labs/nevron.git
cd nevron
make deps
```

### 2. Configure Environment

```bash
cp .env.dev .env
```

Edit `.env` with your LLM provider credentials and agent settings. See [Configuration](configuration.md) for all options.

### 3. Run

```bash
make run
```

This runs the agent directly without the API or dashboard.

-----

## Available Workflows and Tools

Nevron comes with two pre-configured workflows:

- `Analyze signal`: Processes and analyzes incoming signal data
- `Research news`: Gathers and analyzes news using Perplexity API

And with various tools:

- `X`: Post tweets
- `Discord`: Listen to incoming messages and send messages
- `Telegram`: Send telegram messages
- `Lens`: Post to Lens, fetch from Lens
- `WhatsApp`: Get and post messages
- `Slack`: Get and post messages
- `Tavily`: Search with Tavily
- `Perplexity`: Search with Perplexity
- `Coinstats`: Get Coinstats news
- `YouTube`: Search for YouTube videos and playlists
- `Spotify`: Search for songs and get details of particular songs
- `GitHub`: Create GitHub Issues or PRs, get the latest GitHub Actions
- `Google Drive`: Search for files, upload files to Drive
- `Shopify`: Get products, orders, update product info

You will see errors in the logs since the agent will try to call these tools, but for their usage, you'll need to configure the appropriate API keys. Refer to the [Configuration](configuration.md) documentation for more details.

## Customizations

Please refer to the [Configuration](configuration.md) documentation for customizing the agent.

## Troubleshooting

Common issues:
- If using OpenAI, ensure your API key is set correctly in `.env`
- If using Ollama, verify it's running with `ollama list`
- Check logs in the console for detailed error messages
- Verify Python version: `python --version` (should be 3.13)
- Confirm dependencies: `poetry show`

For more help, visit our [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).
