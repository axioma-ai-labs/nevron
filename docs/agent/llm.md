# **LLM Integration**

Large Language Models are the backbone of the Autonomous Agent. They are the core component that allows the agent to understand and respond to natural language.

## Implementation

The LLM integration is primarily handled through the `src/llm` directory, which provides:

- API interaction with OpenAI/Anthropic/xAI models
- Embeddings generation for memory storage
- Context management
- Response processing & generation

## Overview

### 1. Embeddings

For memory storage, the agent uses OpenAI's embedding models to generate vector representations of the memories. These vectors are then stored in a vector database for efficient retrieval and semantic search. To generate embeddings, the agent uses the `src/llm/embeddings.py` module.

For embeddings generation we recommend using OpenAI's [`text-embedding-3-large`](https://openai.com/index/new-embedding-models-and-api-updates/) model.

### 2. Response Processing & Generation

The agent uses the LLM class to generate responses through different providers. The `src/llm/llm.py` module provides:

- Unified interface for multiple LLM providers through the `LLM` class
- Automatic system message injection with agent personality and goals
- Async response generation via `generate_response()` method
- Support for additional parameters like model and temperature
- OpenAI client initialization helper via `get_oai_client()`

-----

## Configuration

Currently, the agent is configured to use OpenAI's `gpt-4o` model, but it can be easily configured to use other models (e.g. `gpt-4o-mini`, `gpt-4`, Anthropic's models like `claude-3-5-sonnet` or xAI's `grok-2-latest` model).

### Environment Variables
To choose model of your choice, set the following environment variables:
```
OPENAI_API_KEY=your-api-key
OPENAI_MODEL=gpt-4  # or other supported models (e.g. gpt-4o-mini, gpt-4o, claude-3-5-sonnet, grok-2-latest)
OPENAI_EMBEDDING_MODEL=text-embedding-3-large # or other supported embedding models
```

-----

## Best Practices

1. **Token Management**
   Monitor and track token consumption across API calls. Implement rate limiting mechanisms to prevent exceeding quotas. Establish proper API quota management systems to maintain service availability.

2. **Error Handling**
   Implement graceful fallback mechanisms when API calls fail. Set up automatic retry logic with exponential backoff. Maintain comprehensive error logging to track and debug issues.

3. **Cost Optimization**
   Select appropriate model tiers based on task requirements. Implement response caching for frequently requested prompts. Track and analyze API usage patterns to optimize costs.

-----

## Future Enhancements

We're planning to add support for additional LLM providers, advanced prompt engineering, fine-tuning capabilities, and enhanced error handling in the nearest future.

-----

If you have any questions or need further assistance, please refer to the [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).
