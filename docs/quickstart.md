# Quickstart Guide

This guide will help you get Nevron, your autonomous AI agent, running in 5 simple steps.


## Prerequisites

To be able to run the agent, you need to have the following:

- **Python 3.12**
- **Pipenv**
- **Docker** (optional, for Qdrant memory backend)
- **OpenAI API key** (or any other API key of an LLM provider of your choice)

-----

## Setup in 5 Steps

### 1. Clone & Install

```bash
# clone the repository
git clone https://github.com/axioma-ai-labs/nevron.git
cd aa-core

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
ENVIRONMENT=development         # Set environment (development or production)

# xAI API   (optional)
XAI_API_KEY=

# Perplexity API   (optional)
PERPLEXITY_API_KEY=

# Coinstats API   (optional)
COINSTATS_API_KEY=

# Telegram   (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Twitter   (optional)
TWITTER_BEARER_TOKEN=
TWITTER_API_KEY=
TWITTER_API_SECRET_KEY=
TWITTER_ACCESS_TOKEN=
TWITTER_ACCESS_TOKEN_SECRET=
```

### 3. Choose Memory Backend

#### Option A: Chroma (Default)
No additional setup required. Uses local file storage.

#### Option B: Qdrant
```bash
# create storage directory
mkdir qdrant_storage

# run qdrant container
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

Update `.env`:
```bash
MEMORY_BACKEND_TYPE=qdrant
```

### 4. Configure Nevron's Personality

Setup the personality, goals and rest time of your agent depending on your needs.

In `.env`:
```bash
AGENT_PERSONALITY="A helpful AI assistant focused on research and analysis"
AGENT_GOAL="To assist with information gathering and analysis"
AGENT_REST_TIME=300  # seconds between actions
```

### 5. Run Nevron

```bash
make run
```

-----

## Available Workflows

Nevron comes with two pre-configured workflows which can be used as a starting point:

- `Analyze signal`: Processes and analyzes incoming signal data
- `Research news`: Gathers and analyzes news using Perplexity API

If you want to create your own workflows, or want to learn more about how the workflows work, please refer to the [Workflows](agent/workflows.md) documentation.

-----

## Customization

For more customization you can add your custom [workflows](agent/workflows.md) and [tools](agent/tools.md), adjust [planning](agent/planning.md) parameters, switch [LLM providers](agent/llm.md), fine-tune the hyper-parameters, etc.

Please refer to the [Agent](agent/overview.md) for more information on how to customize the agent, its behavior & personality.

-----

## Troubleshooting

- Ensure all required API keys are set in `.env`
- Check logs in the console for detailed error messages
- Verify Python version: `python --version`
- Confirm dependencies: `pipenv graph`

-----

If you have any questions or need further assistance, please refer to the [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).
