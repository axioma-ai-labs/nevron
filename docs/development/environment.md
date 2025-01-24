# Environment Variables

This page lists all available environment variables that can be configured in Nevron.

## General Settings

### Project Settings
- `ENVIRONMENT`: Environment type (Production, Development, CI). Default: `PRODUCTION`
- `PROJECT_NAME`: Project name. Default: `autonomous-agent`

### Planning Settings
- `PERSISTENT_Q_TABLE_PATH`: Path to the persistent Q-table file. Default: `persistent_q_table.json`
- `PLANNING_ALPHA`: Learning rate. Default: `0.1`
- `PLANNING_GAMMA`: Discount factor. Default: `0.95`
- `PLANNING_EPSILON`: Exploration rate. Default: `0.1`

### Memory Settings
- `MEMORY_BACKEND_TYPE`: Memory backend type (`chroma` or `qdrant`). Default: `chroma`
- `MEMORY_COLLECTION_NAME`: Memory collection name. Default: `agent_memory`
- `MEMORY_HOST`: Memory host (Qdrant only). Default: `localhost`
- `MEMORY_PORT`: Memory port (Qdrant only). Default: `6333`
- `MEMORY_VECTOR_SIZE`: Memory vector size (Qdrant only). Default: `1536`
- `MEMORY_PERSIST_DIRECTORY`: Memory persist directory (ChromaDB only). Default: `.chromadb`

### LLM Settings
- `LLM_PROVIDER`: LLM provider type (`openai`, `anthropic`, `xai`, `llama`). Default: `openai`

#### Anthropic
- `ANTHROPIC_API_KEY`: Anthropic API key
- `ANTHROPIC_MODEL`: Anthropic model name. Default: `claude-2`

#### OpenAI
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_MODEL`: OpenAI model name. Default: `gpt-4o-mini`
- `OPENAI_EMBEDDING_MODEL`: OpenAI embedding model. Default: `text-embedding-3-small`

#### xAI
- `XAI_API_KEY`: xAI API key
- `XAI_MODEL`: xAI model name. Default: `grok-2-latest`

#### Llama
- `LLAMA_API_KEY`: Llama API key (required for Fireworks, Llama API, and OpenRouter providers)
- `LLAMA_MODEL_NAME`: Llama model name for Fireworks. Default: `llama3-8b-8192`
- `LLAMA_PROVIDER`: Llama provider type (`fireworks`, `ollama`, `llama-api`, or `openrouter`). Default: `ollama`

##### Ollama Settings
- `LLAMA_OLLAMA_URL`: Ollama API URL. Default: `http://localhost:11434`
- `LLAMA_OLLAMA_MODEL`: Ollama model name. Default: `llama3.2:latest`

##### Llama API Settings
- `LLAMA_API_BASE_URL`: Llama API base URL. Default: `https://api.llama-api.com`
- `LLAMA_API_MODEL`: Llama API model name. Default: `llama3.1-70b`

##### OpenRouter Settings
- `LLAMA_OPENROUTER_URL`: OpenRouter API URL. Default: `https://openrouter.ai/api/v1`
- `LLAMA_OPENROUTER_MODEL`: OpenRouter model name. Default: `meta-llama/llama-3.2-1b-instruct`
- `LLAMA_OPENROUTER_SITE_URL`: Optional. Site URL for rankings on openrouter.ai
- `LLAMA_OPENROUTER_SITE_NAME`: Optional. Site name for rankings on openrouter.ai

## Agent Settings

### Core Settings
- `AGENT_PERSONALITY`: Description of agent's personality
- `AGENT_GOAL`: Agent's primary goal
- `AGENT_REST_TIME`: Rest time between actions in seconds. Default: `300`

## Integration Settings

### Telegram
- `TELEGRAM_BOT_TOKEN`: Telegram bot token
- `TELEGRAM_CHAT_ID`: Telegram chat ID for main channel/group

### Twitter
- `TWITTER_API_KEY`: Twitter API key
- `TWITTER_API_SECRET_KEY`: Twitter API secret key
- `TWITTER_ACCESS_TOKEN`: Twitter access token
- `TWITTER_ACCESS_TOKEN_SECRET`: Twitter access token secret

### Perplexity
- `PERPLEXITY_API_KEY`: Perplexity API key
- `PERPLEXITY_ENDPOINT`: Perplexity endpoint. Default: `https://api.perplexity.ai/chat/completions`
- `PERPLEXITY_NEWS_PROMPT`: Custom prompt for news search
- `PERPLEXITY_NEWS_CATEGORY_LIST`: List of news categories to search

### Coinstats
- `COINSTATS_API_KEY`: Coinstats API key

### Discord
- `DISCORD_BOT_TOKEN`: Discord bot token
- `DISCORD_CHANNEL_ID`: Discord channel ID

### YouTube
- `YOUTUBE_API_KEY`: YouTube API key
- `YOUTUBE_PLAYLIST_ID`: YouTube playlist ID

### WhatsApp
- `WHATSAPP_ID_INSTANCE`: WhatsApp instance ID
- `WHATSAPP_API_TOKEN`: WhatsApp API token 