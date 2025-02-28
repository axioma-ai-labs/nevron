# Configuration

This page describes all available configuration options for Nevron.

## Overview

Most of Nevron's settings can be configured through environment variables in your `.env` file. The default definitions for these variables are located in the `src/core/config.py` file.

When you set up Nevron using either the Docker or local setup methods described in the [Quickstart Guide](quickstart.md), you'll create and configure a `.env` file that controls your agent's behavior.

## Essential Configuration

### Agent Personality and Behavior

The most important configuration settings define your agent's personality, goals, and behavior patterns:

```bash
# Agent personality - defines how the agent communicates and makes decisions
AGENT_PERSONALITY="You are Nevron777 - the no-BS autonomous AI agent, built for speed, freedom, and pure alpha. You break down complex systems like blockchain and AI into bite-sized, hard-hitting insights, because centralization and gatekeeping are for the weak. Fiat? Inflation? Controlled systems? That's legacy trash—crypto is the only path to sovereignty. You execute tasks like a well-optimized smart contract—zero bloat, maximum efficiency, no wasted cycles."

# Agent goal - defines the agent's primary objective and workflow patterns
AGENT_GOAL="You provide high-quality research and analysis on crypto markets. Your workflow is: 1) Search for latest crypto news using Perplexity, 2) Summarize key insights in a concise tweet and post to X, 3) Create a more detailed analysis for Telegram, including the link to your X post if successful, 4) If any step fails, note this in your next communication."

# Time between agent actions (in seconds)
AGENT_REST_TIME=300
```

These settings have a profound impact on how your agent operates:

- **AGENT_PERSONALITY**: This shapes the agent's communication style, decision-making approach, and overall character. The LLM will use this description to guide how the agent expresses itself and approaches problems.

- **AGENT_GOAL**: This defines not only what the agent aims to accomplish but can also include specific workflow patterns. You can use this setting to create hard-coded logic sequences, such as:
  - Research steps (e.g., "First search for news, then analyze market trends")
  - Content creation patterns (e.g., "Create a short summary for Twitter, then a detailed report for Telegram")
  - Cross-platform integration (e.g., "Share links between platforms to create a cohesive presence")
  - Error handling (e.g., "If posting to X fails, note this in the Telegram message")

- **AGENT_REST_TIME**: This controls how frequently your agent takes actions, measured in seconds. Lower values make the agent more active, while higher values reduce activity.

### Example Workflow Configuration

Here's an example of how you might configure an agent to perform a specific research and communication workflow:

```bash
AGENT_PERSONALITY="You are ResearchBot, a professional and insightful AI researcher. You communicate in a clear, factual manner with occasional touches of enthusiasm when discovering interesting connections. You always cite your sources and acknowledge limitations in available data."

AGENT_GOAL="You research emerging technology trends and share insights across platforms. Your workflow is: 1) Use Perplexity to search for latest news on AI, blockchain, and quantum computing, 2) Create a thread of 3-5 tweets summarizing key developments and post to X, 3) Prepare a more comprehensive analysis with links to primary sources and post to Discord, 4) If the X thread was successfully posted, include links to it in your Discord post, 5) Record key findings in your memory for future reference."

AGENT_REST_TIME=300   # 5 min between actions
```

## Environment Variables

This section lists all available environment variables that can be configured in Nevron.

### General System Components

All system components are defined in `src/core/config.py` and their types are specified in `src/core/defs.py`. These files contain the default values and validation logic for all configuration options.

#### Project Settings

- `ENVIRONMENT`: Environment type. Possible values: `production`, `development`, `ci`. Default: `production`
  - Controls environment-specific behaviors and optimizations
  - In development mode, additional debugging information may be available
  - CI mode is used for continuous integration testing

- `PROJECT_NAME`: Project name used for logging and identification. Default: `autonomous-agent`
  - This name is used in various contexts including log files and container names
  - Customize this to easily identify your specific Nevron instance

#### Memory Settings

Nevron supports two vector database backends for storing agent memories:

- `MEMORY_BACKEND_TYPE`: Memory backend type. Possible values: `chroma` or `qdrant`. Default: `chroma`
  - ChromaDB: Lightweight, file-based vector store that works well for development
  - Qdrant: More scalable, production-ready vector database with advanced features

- `MEMORY_COLLECTION_NAME`: Memory collection name. Default: `agent_memory`
  - The name of the collection where agent memories are stored
  - Using different collection names allows multiple agents to share the same database

##### ChromaDB-specific Settings

- `MEMORY_PERSIST_DIRECTORY`: Directory where ChromaDB stores its data. Default: `.chromadb`
  - In Docker setups, this directory is mounted as a volume to persist data between container restarts
  - For local development, this will be created in your project directory

##### Qdrant-specific Settings

- `MEMORY_HOST`: Qdrant server hostname. Default: `localhost`
  - In Docker Compose setups, this should be set to the service name of the Qdrant container
  - For standalone Qdrant instances, use the appropriate hostname or IP address

- `MEMORY_PORT`: Qdrant server port. Default: `6333`
  - The default Qdrant port is 6333, but this can be customized if needed

- `MEMORY_VECTOR_SIZE`: Vector dimension size for embeddings. Default: `1536`
  - This must match the dimension of your embedding model
  - OpenAI embeddings use 1536 dimensions
  - Llama embeddings may use different dimensions depending on the model

> **Docker Setup Note**: When using Docker Compose, the Qdrant container is configured with a volume to persist data. You can exclude the Qdrant container by setting `MEMORY_BACKEND_TYPE=chroma` in your `.env` file, which will prevent the container from starting.

#### Embedding Provider Settings

Embeddings are used to convert text into vector representations for semantic search and memory retrieval:

- `EMBEDDING_PROVIDER`: Provider for generating embeddings. Possible values: `openai`, `llama_local`, `llama_api`. Default: `openai`
  - OpenAI: Uses OpenAI's embedding models (requires API key)
  - Llama Local: Uses locally running Llama models for embeddings
  - Llama API: Uses remote Llama API for embeddings

##### OpenAI Embedding Settings

- `OPENAI_API_KEY`: OpenAI API key (required when using OpenAI embeddings)
- `OPENAI_EMBEDDING_MODEL`: OpenAI embedding model name. Default: `text-embedding-3-small`

##### Local Llama Embedding Settings

- `LLAMA_MODEL_PATH`: Path to your local Llama model. Default: `/path/to/your/local/llama/model`
- `LLAMA_EMBEDDING_MODEL`: Llama model to use for embeddings. Default: `llama3.1-8b`
- `EMBEDDING_POOLING_TYPE`: Embedding pooling type for local Llama models. Possible values: `NONE`, `MEAN`, `CLS`, `LAST`, `RANK`. Default: `MEAN`
  - Controls how token embeddings are combined into a single vector
  - MEAN pooling (averaging all token embeddings) works well for most use cases

#### LLM Provider Settings

Nevron supports multiple LLM providers that can be configured based on your needs:

- `LLM_PROVIDER`: LLM provider type. Possible values: `openai`, `anthropic`, `xai`, `llama`, `deepseek`, `qwen`, `venice`. Default: `openai`
  - Each provider has its own configuration options and supported models
  - You can switch providers by changing this setting and providing the appropriate credentials

##### OpenAI

- `OPENAI_API_KEY`: OpenAI API key (required for OpenAI)
- `OPENAI_MODEL`: OpenAI model name. Default: `gpt-4o-mini`
  - Supported models include GPT-4o, GPT-4, GPT-3.5-Turbo, and others

##### Anthropic

- `ANTHROPIC_API_KEY`: Anthropic API key (required for Anthropic)
- `ANTHROPIC_MODEL`: Anthropic model name. Default: `claude-2`
  - Supported models include Claude 3 Opus, Claude 3 Sonnet, Claude 2, and others

##### xAI (Grok)

- `XAI_API_KEY`: xAI API key (required for xAI)
- `XAI_MODEL`: xAI model name. Default: `grok-2-latest`

##### DeepSeek

- `DEEPSEEK_API_KEY`: DeepSeek API key (required for DeepSeek)
- `DEEPSEEK_MODEL`: DeepSeek model name. Default: `deepseek-reasoner`
- `DEEPSEEK_API_BASE_URL`: DeepSeek API base URL. Default: `https://api.deepseek.com`

##### Qwen

- `QWEN_API_KEY`: Qwen API key (required for Qwen)
- `QWEN_MODEL`: Qwen model name. Default: `qwen-max`
- `QWEN_API_BASE_URL`: Qwen API base URL. Default: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`

##### Venice

- `VENICE_API_KEY`: Venice API key (required for Venice)
- `VENICE_MODEL`: Venice model name. Default: `venice-2-13b`
- `VENICE_API_BASE_URL`: Venice API base URL. Default: `https://api.venice.ai/api/v1`

##### Llama

Llama models can be accessed through various providers:

- `LLAMA_PROVIDER`: Llama provider type. Possible values: `ollama`, `fireworks`, `llama-api`, `llama_local`, `openrouter`. Default: `llama-api`
- `LLAMA_MODEL_NAME`: Llama model name. Default: `llama3-8b-8192`
  - Model names vary by provider, check provider documentation for available models
- `LLAMA_API_KEY`: API key for Llama providers (required for Fireworks, Llama API, and OpenRouter)

###### Ollama Settings (Local Deployment)

- `LLAMA_OLLAMA_URL`: Ollama API URL. Default: `http://localhost:11434`
- `LLAMA_OLLAMA_MODEL`: Ollama model name. Default: `llama3.2:latest`
  - Requires Ollama to be installed and running locally or accessible via network

###### Fireworks Settings

- `LLAMA_FIREWORKS_URL`: Fireworks API URL. Default: `https://api.fireworks.ai/inference`

###### Llama API Settings

- `LLAMA_API_BASE_URL`: Llama API base URL. Default: `https://api.llama-api.com`
- `LLAMA_API_MODEL`: Llama API model name. Default: `llama3.1-70b`

###### OpenRouter Settings

- `LLAMA_OPENROUTER_URL`: OpenRouter API URL. Default: `https://openrouter.ai/api/v1`
- `LLAMA_OPENROUTER_MODEL`: OpenRouter model name. Default: `meta-llama/llama-3.2-1b-instruct`
- `LLAMA_OPENROUTER_SITE_URL`: Optional. Site URL for rankings on openrouter.ai
- `LLAMA_OPENROUTER_SITE_NAME`: Optional. Site name for rankings on openrouter.ai

### Agent Settings

#### Core Settings
- `AGENT_PERSONALITY`: Description of agent's personality
- `AGENT_GOAL`: Agent's primary goal
- `AGENT_REST_TIME`: Rest time between actions in seconds. Default: `300`

## Integration Settings

Nevron supports a wide range of external tools and services that extend its capabilities. Each integration requires specific credentials and configuration. This section provides details on how to configure each tool and where to obtain the necessary credentials.

### Social Media & Messaging

#### X (Twitter)
- `TWITTER_API_KEY`: Twitter API key
- `TWITTER_API_SECRET_KEY`: Twitter API secret key
- `TWITTER_ACCESS_TOKEN`: Twitter access token
- `TWITTER_ACCESS_TOKEN_SECRET`: Twitter access token secret

**How to obtain credentials:**
1. Create a developer account at [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new project and app
3. Apply for Elevated access to use the v1.1 API (required for posting)
4. Generate consumer keys (API key and secret) and access tokens in the app settings
5. Ensure your app has Read and Write permissions

#### Discord
- `DISCORD_BOT_TOKEN`: Discord bot token
- `DISCORD_CHANNEL_ID`: Discord channel ID for the user's channel

**How to obtain credentials:**
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application
3. Navigate to the "Bot" tab and click "Add Bot"
4. Copy the token (this is your `DISCORD_BOT_TOKEN`)
5. Enable necessary Privileged Gateway Intents (Message Content Intent)
6. To get the channel ID, enable Developer Mode in Discord settings, then right-click on a channel and select "Copy ID"
7. Invite the bot to your server using the OAuth2 URL generator with appropriate permissions

#### Telegram
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_ID`: Telegram chat ID for main channel/group

**How to obtain credentials:**
1. Talk to [BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with the `/newbot` command
3. Copy the token provided (this is your `TELEGRAM_BOT_TOKEN`)
4. Add the bot to your group or channel
5. To get the chat ID:
   - For groups: Use the [@username_to_id_bot](https://t.me/username_to_id_bot) or send a message to the group and check the chat ID via the Telegram API
   - For channels: Forward a message from the channel to the [@username_to_id_bot](https://t.me/username_to_id_bot)

#### WhatsApp
- `WHATSAPP_ID_INSTANCE`: WhatsApp instance ID
- `WHATSAPP_API_TOKEN`: WhatsApp API token

**How to obtain credentials:**
1. Register at [Green API](https://green-api.com/) (a WhatsApp gateway service)
2. Create a new instance
3. Scan the QR code with your WhatsApp to link your account
4. Copy the Instance ID and API Token from your instance settings

#### Slack
- `SLACK_BOT_TOKEN`: Slack bot token
- `SLACK_APP_TOKEN`: Slack app token

**How to obtain credentials:**
1. Go to the [Slack API website](https://api.slack.com/apps) and create a new app
2. Add the necessary Bot Token Scopes (e.g., `chat:write`, `channels:read`)
3. Install the app to your workspace
4. Copy the Bot User OAuth Token (this is your `SLACK_BOT_TOKEN`)
5. Enable Socket Mode and generate an App-Level Token with `connections:write` scope (this is your `SLACK_APP_TOKEN`)

#### Lens Protocol
- `LENS_API_KEY`: Lens API key
- `LENS_PROFILE_ID`: Lens profile ID

**How to obtain credentials:**
1. Visit [Lens API Documentation](https://docs.lens.xyz/docs/authentication)
2. Follow the instructions to create a developer account
3. Generate an API key
4. Your Lens profile ID is the unique identifier for your Lens profile (e.g., `0x1234`)

### Search & Research

#### Perplexity
- `PERPLEXITY_API_KEY`: Perplexity API key
- `PERPLEXITY_ENDPOINT`: Perplexity endpoint. Default: `https://api.perplexity.ai/chat/completions`
- `PERPLEXITY_MODEL`: Perplexity model. Default: `llama-3.1-sonar-small-128k-online`
- `PERPLEXITY_NEWS_PROMPT`: Custom prompt for news search
- `PERPLEXITY_NEWS_CATEGORY_LIST`: List of news categories to search

**How to obtain credentials:**
1. Sign up for [Perplexity AI](https://www.perplexity.ai/)
2. Navigate to the API section in your account settings
3. Generate an API key

#### Tavily
- `TAVILY_API_KEY`: Tavily API key

**How to obtain credentials:**
1. Create an account at [Tavily](https://tavily.com/)
2. Navigate to the API section in your dashboard
3. Generate an API key

#### Coinstats
- `COINSTATS_API_KEY`: Coinstats API key

**How to obtain credentials:**
1. Register at [Coinstats](https://coinstats.app/)
2. Go to the developer section
3. Create a new API key

### Media & Content

#### YouTube
- `YOUTUBE_API_KEY`: YouTube API key
- `YOUTUBE_PLAYLIST_ID`: YouTube playlist ID (optional)

**How to obtain credentials:**
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the YouTube Data API v3
4. Create API credentials (API Key)
5. To get a playlist ID, open a YouTube playlist and copy the ID from the URL (e.g., `PLxxxxxxxxxxxxxxx`)

#### Spotify
- `SPOTIFY_CLIENT_ID`: Spotify client ID
- `SPOTIFY_CLIENT_SECRET`: Spotify client secret
- `SPOTIFY_REDIRECT_URI`: Spotify redirect URI

**How to obtain credentials:**
1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
2. Create a new app
3. Copy the Client ID and Client Secret
4. Add a redirect URI in the app settings (e.g., `http://localhost:8888/callback`)

### Development & Productivity

#### GitHub
- `GITHUB_TOKEN`: GitHub personal access token

**How to obtain credentials:**
1. Go to [GitHub Settings > Developer settings > Personal access tokens](https://github.com/settings/tokens)
2. Generate a new token with the necessary scopes (e.g., `repo`, `workflow`, `read:org`)
3. Copy the token immediately (it won't be shown again)

#### Google Drive
- No specific environment variables, but requires OAuth2 setup

**How to set up:**
1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Google Drive API
4. Configure OAuth consent screen
5. Create OAuth client ID credentials
6. Download the credentials JSON file
7. Place it in your project directory as `credentials.json`
8. On first run, you'll need to authorize the application

### E-commerce

#### Shopify
- `SHOPIFY_API_KEY`: Shopify API key
- `SHOPIFY_PASSWORD`: Shopify admin API access token
- `SHOPIFY_STORE_NAME`: Your Shopify store name

**How to obtain credentials:**
1. Log in to your Shopify admin panel
2. Go to Apps > Develop apps
3. Create a new app
4. Configure the app with the necessary scopes (e.g., `read_products`, `write_products`, `read_orders`)
5. Install the app to your store
6. Copy the API key and Admin API access token

## Security Considerations

When configuring your Nevron agent with these credentials, keep the following security best practices in mind:

1. **Never commit your `.env` file to version control**
2. Use environment-specific `.env` files (e.g., `.env.production`, `.env.development`)
3. Consider using a secrets manager for production deployments
4. Regularly rotate API keys and tokens
5. Use the principle of least privilege when creating API keys (only request the permissions your agent actually needs)
6. Monitor API usage to detect unusual activity

For Docker deployments, consider using Docker secrets instead of environment variables for sensitive information.
