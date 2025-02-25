# Perplexity Tool

## Overview

The Perplexity Tool enables Nevron agents to perform advanced web searches and research using the Perplexity AI API. This integration allows agents to gather up-to-date information from the internet, analyze data, and generate insights based on comprehensive web searches.

## Features

- **Advanced Search**: Perform sophisticated web searches with natural language queries
- **Research Capabilities**: Conduct in-depth research on specific topics
- **Contextual Answers**: Get detailed, contextual answers to complex questions
- **Source Attribution**: Access sources for verification and further exploration
- **Customizable Search Parameters**: Configure search depth, focus, and other parameters

## Configuration

To use the Perplexity Tool, you need to configure the following environment variables in your `.env` file:

```bash
PERPLEXITY_API_KEY=your_api_key
PERPLEXITY_ENDPOINT=https://api.perplexity.ai/chat/completions
PERPLEXITY_MODEL=llama-3.1-sonar-small-128k-online
PERPLEXITY_NEWS_PROMPT=your_custom_prompt_for_news_search
PERPLEXITY_NEWS_CATEGORY_LIST=comma,separated,categories
```

### How to Obtain Perplexity API Credentials

1. Sign up for [Perplexity AI](https://www.perplexity.ai/)
2. Navigate to the API section in your account settings
3. Generate an API key

## Methods

### `search`

Performs a general search query using Perplexity AI.

**Arguments**:
- `query` (str): The search query or question
- `model` (Optional[str]): The model to use for search (defaults to environment variable)
- `temperature` (Optional[float]): Temperature for response generation (default: 0.7)
- `max_tokens` (Optional[int]): Maximum tokens in the response (default: 1024)

**Returns**:
- `str`: The search results with relevant information

**Example**:
```python
results = await perplexity_tool.search(
    query="What are the latest developments in quantum computing?",
    temperature=0.5
)
```

### `search_news`

Searches for recent news on specific topics or categories.

**Arguments**:
- `query` (str): The news topic to search for
- `categories` (Optional[List[str]]): Specific news categories to focus on
- `model` (Optional[str]): The model to use for search (defaults to environment variable)
- `temperature` (Optional[float]): Temperature for response generation (default: 0.7)
- `max_tokens` (Optional[int]): Maximum tokens in the response (default: 1024)

**Returns**:
- `str`: The news search results with relevant information

**Example**:
```python
news_results = await perplexity_tool.search_news(
    query="cryptocurrency market trends",
    categories=["finance", "technology", "blockchain"]
)
```

### `research`

Conducts in-depth research on a specific topic with detailed analysis.

**Arguments**:
- `topic` (str): The research topic
- `focus_areas` (Optional[List[str]]): Specific aspects to focus on
- `model` (Optional[str]): The model to use for research (defaults to environment variable)
- `temperature` (Optional[float]): Temperature for response generation (default: 0.7)
- `max_tokens` (Optional[int]): Maximum tokens in the response (default: 2048)

**Returns**:
- `str`: Comprehensive research results with analysis and sources

**Example**:
```python
research_results = await perplexity_tool.research(
    topic="Impact of artificial intelligence on job markets",
    focus_areas=["automation risks", "new job creation", "skill requirements"]
)
```

## Implementation Details

The Perplexity Tool is implemented in `src/tools/perplexity_tool.py` and uses the Perplexity API to perform searches and research. The tool handles authentication, query formatting, and response parsing to provide clean, usable results.

### Search Process

1. The tool formats the query with appropriate system instructions
2. The query is sent to the Perplexity API with configured parameters
3. The response is parsed and formatted for easy consumption
4. Sources are extracted and included when available

### Model Selection

The Perplexity Tool supports various models through the Perplexity API:

- `llama-3.1-sonar-small-128k-online` (default): Good balance of speed and quality
- `llama-3.1-sonar-medium-128k-online`: Higher quality but slower
- `claude-3.5-sonnet`: High quality for complex research

## Best Practices

1. **Specific Queries**: Formulate clear, specific queries for better results
2. **Appropriate Model**: Choose the right model based on complexity and depth needed
3. **Temperature Setting**: Lower temperature (0.1-0.5) for factual searches, higher (0.6-0.9) for creative exploration
4. **Source Verification**: Always verify important information from sources provided
5. **Rate Limiting**: Be mindful of API rate limits in high-volume applications

## Example Agent Workflow

Here's an example of how an agent might use the Perplexity Tool in a research workflow:

```python
async def market_research_workflow(agent, topic):
    # Initial broad search
    general_results = await agent.tools.perplexity.search(
        query=f"Overview of {topic} market trends"
    )
    
    # Extract key points for focused research
    key_points = await agent.llm.extract_key_points(general_results)
    
    # Detailed research on each key point
    detailed_insights = []
    for point in key_points:
        research = await agent.tools.perplexity.research(
            topic=point,
            focus_areas=["current developments", "future projections", "key players"]
        )
        detailed_insights.append(research)
    
    # Compile final report
    final_report = await agent.llm.compile_report(
        general_overview=general_results,
        detailed_insights=detailed_insights
    )
    
    # Share results via Telegram
    await agent.tools.telegram.send_message(text=final_report)
    
    return "Market research completed and report sent"
```

## Limitations

- Subject to Perplexity API rate limits
- Search results depend on Perplexity's index freshness
- Complex queries may require multiple searches for comprehensive results
- API costs associated with usage

## Troubleshooting

Common issues and their solutions:

1. **Authentication Failed**: Verify your API key in the `.env` file
2. **Rate Limit Exceeded**: Implement rate limiting in your application
3. **Incomplete Results**: Break complex queries into multiple focused searches
4. **Model Unavailable**: Check if the specified model is available in your subscription tier

For more help, visit our [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).
