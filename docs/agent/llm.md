# **LLM Integration**

Large Language Models are the backbone of the Autonomous Agent. They are the core component that allows the agent to understand and respond to natural language, make decisions, and learn from feedback.

## Overview

Nevron supports multiple LLM providers, giving you flexibility to choose the model that best fits your needs, budget, and performance requirements. The framework is designed with a modular architecture that allows easy switching between different providers.

### Supported Providers

Nevron currently supports the following LLM providers:

1. **OpenAI** - GPT-4o, GPT-4, GPT-3.5-Turbo models
2. **Anthropic** - Claude 3 Opus, Claude 3 Sonnet, Claude 2 models
3. **xAI** - Grok models
4. **Llama** - Via multiple deployment options:
   - API (api.llama-api.com)
   - OpenRouter
   - Fireworks
   - Local deployment with Ollama
5. **DeepSeek** - DeepSeek models
6. **Qwen** - Qwen models
7. **Venice** - Venice models

## Implementation

The LLM integration is primarily handled through the `src/llm` directory, which provides:

- A unified interface for all LLM providers
- Provider-specific API interaction modules
- Embeddings generation for memory storage
- Context management
- Response processing & generation

### Core Components

#### 1. LLM Class

The `LLM` class in `src/llm/llm.py` serves as the main interface for generating responses:

```python
class LLM:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        
    async def generate_response(self, messages, **kwargs):
        # Add system message with agent's personality and goal if not present
        if not messages or messages[0].get("role") != "system":
            system_message = {
                "role": "system",
                "content": f"{settings.AGENT_PERSONALITY}\n\n{settings.AGENT_GOAL}",
            }
            messages = [system_message] + messages
            
        # Route to appropriate provider
        if self.provider == LLMProviderType.OPENAI:
            return await call_openai(messages, **kwargs)
        elif self.provider == LLMProviderType.ANTHROPIC:
            return await call_anthropic(messages, **kwargs)
        # ... other providers
```

#### 2. Embeddings

For memory storage, the agent uses embedding models to generate vector representations of memories. These vectors are stored in a vector database (ChromaDB or Qdrant) for efficient retrieval and semantic search.

Nevron supports multiple embedding providers:

- **OpenAI** - Using text-embedding-3-small/large models
- **Llama API** - Using Llama models via API
- **Local Llama** - Using locally deployed Llama models

## Configuration

### Basic Provider Selection

To select your LLM provider, set the `LLM_PROVIDER` environment variable in your `.env` file:

```bash
# Choose one of: openai, anthropic, xai, llama, deepseek, qwen, venice
LLM_PROVIDER=openai
```

### Provider-Specific Configuration

#### OpenAI

```bash
# Required
OPENAI_API_KEY=your_api_key_here

# Optional (defaults shown)
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

**Recommended Models:**
- `gpt-4o` - Best performance, higher cost
- `gpt-4o-mini` - Good balance of performance and cost
- `gpt-3.5-turbo` - Fastest, lowest cost

#### Anthropic

```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional (default shown)
ANTHROPIC_MODEL=claude-2
```

**Recommended Models:**
- `claude-3-opus-20240229` - Highest capability
- `claude-3-sonnet-20240229` - Good balance
- `claude-2` - Faster, lower cost

#### xAI (Grok)

```bash
# Required
XAI_API_KEY=your_api_key_here

# Optional (default shown)
XAI_MODEL=grok-2-latest
```

#### DeepSeek

```bash
# Required
DEEPSEEK_API_KEY=your_api_key_here

# Optional (defaults shown)
DEEPSEEK_MODEL=deepseek-reasoner
DEEPSEEK_API_BASE_URL=https://api.deepseek.com
```

#### Qwen

```bash
# Required
QWEN_API_KEY=your_api_key_here

# Optional (defaults shown)
QWEN_MODEL=qwen-max
QWEN_API_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1
```

#### Venice

```bash
# Required
VENICE_API_KEY=your_api_key_here

# Optional (defaults shown)
VENICE_MODEL=venice-2-13b
VENICE_API_BASE_URL=https://api.venice.ai/api/v1
```

#### Llama

Llama models can be accessed through various providers. First, set the main provider:

```bash
LLM_PROVIDER=llama
```

Then, configure the specific Llama provider:

##### Option 1: Llama API

```bash
# Required
LLAMA_PROVIDER=llama-api
LLAMA_API_KEY=your_api_key_here

# Optional (defaults shown)
LLAMA_API_BASE_URL=https://api.llama-api.com
LLAMA_API_MODEL=llama3.1-70b
```

##### Option 2: OpenRouter

```bash
# Required
LLAMA_PROVIDER=openrouter
LLAMA_API_KEY=your_api_key_here

# Optional (defaults shown)
LLAMA_OPENROUTER_URL=https://openrouter.ai/api/v1
LLAMA_OPENROUTER_MODEL=meta-llama/llama-3.2-1b-instruct

# Optional for rankings
LLAMA_OPENROUTER_SITE_URL=your_site_url
LLAMA_OPENROUTER_SITE_NAME=your_site_name
```

##### Option 3: Fireworks

```bash
# Required
LLAMA_PROVIDER=fireworks
LLAMA_API_KEY=your_api_key_here

# Optional (defaults shown)
LLAMA_FIREWORKS_URL=https://api.fireworks.ai/inference
LLAMA_MODEL_NAME=llama3-8b-8192
```

##### Option 4: Ollama (Local Deployment)

```bash
# Required
LLAMA_PROVIDER=ollama

# Optional (defaults shown)
LLAMA_OLLAMA_URL=http://localhost:11434
LLAMA_OLLAMA_MODEL=llama3.2:latest
```

For Ollama, you'll need to:
1. Install Ollama from [ollama.ai](https://ollama.ai)
2. Pull your desired model: `ollama pull llama3:8b-instruct`
3. Ensure Ollama is running before starting Nevron

### Embedding Configuration

For memory storage, you need to configure the embedding provider:

```bash
# Choose one of: openai, llama_local, llama_api
EMBEDDING_PROVIDER=openai
```

#### OpenAI Embeddings

```bash
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=your_api_key_here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

#### Llama API Embeddings

```bash
EMBEDDING_PROVIDER=llama_api
LLAMA_API_KEY=your_api_key_here
LLAMA_API_BASE_URL=https://api.llama-api.com
```

#### Local Llama Embeddings

```bash
EMBEDDING_PROVIDER=llama_local
LLAMA_MODEL_PATH=/path/to/your/local/llama/model
LLAMA_EMBEDDING_MODEL=llama3.1-8b
EMBEDDING_POOLING_TYPE=MEAN  # Options: NONE, MEAN, CLS, LAST, RANK
```

## Docker Setup

When using Docker Compose, you can easily configure Ollama as your LLM provider:

```bash
# In your .env file
LLM_PROVIDER=llama
LLAMA_PROVIDER=ollama
LLAMA_OLLAMA_MODEL=llama3:8b-instruct
```

The Docker Compose setup includes an Ollama container with a volume for model storage:

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: nevron-ollama
  hostname: nevron-ollama
  ports:
    - "11434:11434"
  volumes:
    - type: bind
      source: ${volumes_basedir:-./volumes}/ollama/models
      target: /root/.ollama
```

## Best Practices

### 1. Provider Selection

- **Development**: Use Ollama for local development to avoid API costs
- **Production**: Use OpenAI or Anthropic for highest reliability and performance
- **Cost-sensitive**: Consider Llama models via OpenRouter or Fireworks

### 2. Token Management

- Monitor and track token consumption across API calls
- Implement rate limiting mechanisms to prevent exceeding quotas
- Establish proper API quota management systems to maintain service availability

### 3. Error Handling

- Implement graceful fallback mechanisms when API calls fail
- Set up automatic retry logic with exponential backoff
- Maintain comprehensive error logging to track and debug issues

### 4. Cost Optimization

- Select appropriate model tiers based on task requirements
- Implement response caching for frequently requested prompts
- Track and analyze API usage patterns to optimize costs

### 5. Security

- Never commit API keys to version control
- Use environment variables or secrets management for API keys
- Regularly rotate API keys following security best practices

## Troubleshooting

### Common Issues

1. **API Key Issues**
   - Ensure your API key is correctly set in the `.env` file
   - Verify the API key has the necessary permissions and quota

2. **Connection Problems**
   - Check your network connection
   - Verify the API endpoint is accessible from your environment

3. **Ollama Issues**
   - Ensure Ollama is running: `ollama list`
   - Verify the model is downloaded: `ollama pull llama3:8b-instruct`
   - Check Ollama logs: `docker logs nevron-ollama`

4. **Model Selection**
   - Ensure you're using a model that exists for your chosen provider
   - Check for typos in model names

## Future Enhancements

We're planning to add:
- Support for additional LLM providers
- Advanced prompt engineering capabilities
- Fine-tuning support for custom models
- Enhanced error handling and fallback mechanisms
- Streaming responses for real-time interaction

-----

If you have any questions or need further assistance, please refer to the [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).
