# Quickstart Guide

This guide will help you get Nevron, your autonomous AI agent, running quickly. Choose the setup path that best suits your needs:

- [Docker Setup](#docker-setup) (Recommended for production)
- [Local Setup](#local-setup) (Recommended for development)

## Prerequisites

Common requirements for all installation methods:
- **OpenAI API key** (or any other API key of an LLM provider of your choice)

Additional requirements:
- For Docker setup: **Docker**
- For local setup: **Python 3.12** and **Pipenv**

-----

## Docker Setup

Get Nevron running with Docker in 3 steps:

### 1. Pull & Setup

```bash
# pull the latest image
docker pull axiomai/nevron:latest

# create directories for volumes
mkdir -p volumes/.chromadb

# copy example environment file
cp .env.example .env
```

### 2. Configure

Edit `.env` file with your settings:
```bash
# Required: Choose one of the LLM providers and set its API key
OPENAI_API_KEY=your_key_here    # For OpenAI
# ANTHROPIC_API_KEY=your_key_here # For Anthropic
# XAI_API_KEY=your_key_here      # For xAI
# LLAMA_API_KEY=your_key_here    # For Llama with Fireworks
# Or use local Llama with Ollama:
# LLAMA_PROVIDER=ollama
# LLAMA_OLLAMA_MODEL=llama3.1:8b

# Optional: Set the environment
ENVIRONMENT=production          # Recommended for Docker setup

# Optional: Choose memory backend
MEMORY_BACKEND_TYPE=chroma     # Default memory backend
```

Also, you can configure the personality, goals and rest time of your agent in `.env`.

```bash
AGENT_PERSONALITY="A helpful AI assistant focused on research and analysis"
AGENT_GOAL="To assist with information gathering and analysis"
AGENT_REST_TIME=300  # seconds between actions
```

Note: the full list of available configuration options is available in the [Environment Variables](development/environment.md) documentation.

### 3. Run

```bash
docker run -d \
  --name nevron \
  -e .env \
  -v $(pwd)/volumes/.chromadb:/app/.chromadb \
  axiomai/nevron:latest
```

For production deployments, we recommend using Docker Compose. See our [Deployment Guide](deployment.md) for details.

-----

## Local Setup

Set up Nevron locally in 5 steps:

### 1. Clone & Install

```bash
# clone the repository
git clone https://github.com/axioma-ai-labs/nevron.git
cd nevron

# install dependencies
make deps
```

### 2. Configure Environment

```bash
# copy example environment file
cp .env.dev .env
```

Required environment variables:
```bash
OPENAI_API_KEY=your_key_here    # Required for embeddings
```

For a complete list of available environment variables, see the [Environment Variables](development/environment.md) documentation.

### 3. Configure Personality

Setup the personality, goals and rest time of your agent in `.env`:
```bash
AGENT_PERSONALITY="A helpful AI assistant focused on research and analysis"
AGENT_GOAL="To assist with information gathering and analysis"
AGENT_REST_TIME=300  # seconds between actions
```

### 4. Run

```bash
make run
```

-----

## Available Workflows

Nevron comes with two pre-configured workflows:

- `Analyze signal`: Processes and analyzes incoming signal data
- `Research news`: Gathers and analyzes news using Perplexity API

For more information about workflows, see the [Workflows](agent/workflows.md) documentation.

## Customization

You can customize Nevron by:
- Adding custom [workflows](agent/workflows.md) and [tools](agent/tools.md)
- Adjusting [planning](agent/planning.md) parameters
- Switching [LLM providers](agent/llm.md)

See the [Agent Overview](agent/overview.md) for more details.

## Troubleshooting

Common issues:
- Ensure all required API keys are set in `.env`
- Check logs in the console for detailed error messages
- Verify Python version: `python --version`
- Confirm dependencies: `pipenv graph`

For more help, visit our [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).
