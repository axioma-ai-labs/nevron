# Quickstart Guide

This guide will help you get Nevron, your autonomous AI agent, running quickly. Choose the setup path that best suits your needs:

- [Docker Setup](#docker-setup) (Recommended for production)
- [Local Setup](#local-setup) (Recommended for development)

## Prerequisites

General requirements:
- For Docker setup: **Docker**
- For local setup: **Python 3.13** and **Poetry**

Additional requirements:
- API keys for LLM providers your Agent will use
- API keys for tools your Agent will use

-----

## Docker Setup

Get Nevron running with Docker in 3 steps:

### 1. Pull & Setup

First pull the docker image:

```bash
docker pull axiomai/nevron:latest
```

Create volumes:

```bash
mkdir -p volumes/nevron/logs
mkdir -p volumes/qdrant/data
mkdir -p volumes/ollama/models
```

Create env file:

```bash
cp .env.example .env
```

### 2. Configure

Edit `.env` file to use local Llama and Qdrant as vector store:

```bash
# LLM configuration
LLAMA_PROVIDER=ollama
LLAMA_OLLAMA_MODEL=llama3:8b-instruct

# Memory configuration
MEMORY_BACKEND_TYPE=qdrant
```

Then configure the personality, goals and rest time of your agent in `.env`:

```bash
AGENT_PERSONALITY="You are Nevron777 - the no-BS autonomous AI agent, built for speed, freedom, and pure alpha. You break down complex systems like blockchain and AI into bite-sized, hard-hitting insights, because centralization and gatekeeping are for the weak. Fiat? Inflation? Controlled systems? That's legacy trash—crypto is the only path to sovereignty. You execute tasks like a well-optimized smart contract—zero bloat, maximum efficiency, no wasted cycles."
AGENT_GOAL="You provide high-quality research and analysis on crypto markets."
AGENT_REST_TIME=300  # seconds between actions
```

### 3. Run

```bash
docker compose up -d
```

This will start Nevron with Ollama running locally in the container, using the small model specified in your `.env` file. Qdrant will be used as the default memory vector store.

-----

## Local Setup

Set up Nevron locally in 5 steps:

### 1. Clone & Install

Clone the repository:

```bash
git clone https://github.com/axioma-ai-labs/nevron.git
cd nevron
```

Install Poetry if you haven't already:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Install dependencies:

```bash
make deps
```

### 2. Configure Environment

```bash
cp .env.dev .env
```

### 3. Choose LLM Provider

You have two options for the LLM provider:

#### Option 1: Use LLM API

Edit your `.env` file to include one of these LLM providers:

```bash
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
XAI_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here
QWEN_API_KEY=your_key_here
VENICE_API_KEY=your_key_here
LLAMA_API_KEY=your_key_here   # The API key for the api.llama-api.com
```

You can also use Llama with [openrouter](https://openrouter.ai/api/v1):

```bash
LLAMA_PROVIDER=openrouter
LLAMA_API_KEY=your_key_here
```

Or use Llama with [fireworks](https://api.fireworks.ai/inference):

```bash
LLAMA_PROVIDER=fireworks
LLAMA_API_KEY=your_key_here
```

#### Option 2: Run Ollama locally

First, install Ollama following the instructions at [ollama.ai](https://ollama.ai).

Then, pull a small model:
```bash
ollama pull llama3:8b-instruct
```

Edit your `.env` file:
```bash
# Configure Nevron to use local Ollama
LLAMA_PROVIDER=ollama
LLAMA_OLLAMA_MODEL=llama3:8b-instruct
```

### 4. Configure Personality

Setup the personality, goals and rest time of your agent in `.env`:
```bash
AGENT_PERSONALITY="You are Nevron777 - the no-BS autonomous AI agent, built for speed, freedom, and pure alpha. You break down complex systems like blockchain and AI into bite-sized, hard-hitting insights, because centralization and gatekeeping are for the weak. Fiat? Inflation? Controlled systems? That's legacy trash—crypto is the only path to sovereignty. You execute tasks like a well-optimized smart contract—zero bloat, maximum efficiency, no wasted cycles."
AGENT_GOAL="You provide high-quality research and analysis on crypto markets."
AGENT_REST_TIME=300  # seconds between actions
```

### 5. Run

```bash
make run
```

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
