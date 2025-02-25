# Tavily Integration

## Setup

1. Get Tavily API Key
   - Go to [Tavily Dashboard](https://tavily.com/)
   - Sign up or log in to your account
   - Navigate to API section
   - Copy your API key

2. Configure Environment Variables
   Add this to your `.env` file:
   ```bash
   TAVILY_API_KEY=your_api_key_here
   ```

### Basic Setup
```python
from src.tools.tavily import initialize_tavily_client, execute_search, parse_search_results

# Initialize Tavily client
tavily_client = await initialize_tavily_client(api_key="your_api_key_here")

# Execute search
results = await execute_search(
    client=tavily_client,
    query="Python programming"
)

# Parse results
parsed_results = parse_search_results(results)
```

## Features
- Execute web searches with customizable filters
- Support for both basic and advanced search depths
- Domain filtering (include/exclude specific domains)
- Configurable maximum results
- Relevance scoring for search results
- Published date information when available
- Asynchronous search execution
- SSL verification handling for development

## TODOs for Future Enhancements:
- Add support for image search
- Implement news-specific search
- Add support for time-based filtering
- Implement search analytics
- Add support for custom search engines
- Implement batch search capabilities
- Add support for semantic search
- Implement result caching

## Reference
For implementation details, see: `src/tools/tavily.py`

The implementation uses the official Tavily API. For more information, refer to:
- [Tavily API Documentation](https://docs.tavily.com/)
- [Tavily Python SDK](https://github.com/tavily-ai/tavily-python)
