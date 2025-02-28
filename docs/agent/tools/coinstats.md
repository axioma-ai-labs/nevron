# Coinstats Tool

## Overview

The Coinstats Tool enables Nevron agents to access cryptocurrency market data, news, and portfolio information through the Coinstats API. This integration allows agents to track market trends, monitor specific cryptocurrencies, and gather the latest news in the crypto space.

## Features

- **Market Data**: Access real-time and historical price data for cryptocurrencies
- **News Aggregation**: Retrieve the latest news from various crypto news sources
- **Portfolio Tracking**: Monitor cryptocurrency portfolios and performance
- **Market Trends**: Analyze market trends and sentiment
- **Coin Information**: Get detailed information about specific cryptocurrencies

## Configuration

To use the Coinstats Tool, you need to configure the following environment variable in your `.env` file:

```bash
COINSTATS_API_KEY=your_api_key
```

### How to Obtain Coinstats API Credentials

1. Register at [Coinstats](https://coinstats.app/)
2. Go to the developer section
3. Create a new API key

## Methods

### `get_news`

Retrieves the latest cryptocurrency news articles.

**Arguments**:
- `limit` (Optional[int]): Maximum number of news articles to retrieve (default: 10)
- `skip` (Optional[int]): Number of articles to skip (for pagination) (default: 0)
- `categories` (Optional[List[str]]): Specific news categories to filter by

**Returns**:
- `List[Dict[str, Any]]`: List of news articles with title, source, url, and content

**Example**:
```python
news = await coinstats_tool.get_news(
    limit=5,
    categories=["bitcoin", "ethereum"]
)
```

### `get_coin_data`

Retrieves detailed information about a specific cryptocurrency.

**Arguments**:
- `coin_id` (str): The ID of the cryptocurrency (e.g., "bitcoin", "ethereum")
- `currency` (Optional[str]): The currency for price data (default: "USD")

**Returns**:
- `Dict[str, Any]`: Detailed information about the cryptocurrency including price, market cap, and volume

**Example**:
```python
bitcoin_data = await coinstats_tool.get_coin_data(
    coin_id="bitcoin",
    currency="USD"
)
```

### `get_market_data`

Retrieves market data for multiple cryptocurrencies.

**Arguments**:
- `limit` (Optional[int]): Maximum number of coins to retrieve (default: 20)
- `skip` (Optional[int]): Number of coins to skip (for pagination) (default: 0)
- `currency` (Optional[str]): The currency for price data (default: "USD")
- `sort` (Optional[str]): Sorting criteria (e.g., "market_cap", "volume", "price") (default: "market_cap")

**Returns**:
- `List[Dict[str, Any]]`: List of cryptocurrencies with market data

**Example**:
```python
market_data = await coinstats_tool.get_market_data(
    limit=10,
    sort="volume",
    currency="EUR"
)
```

### `get_trending_coins`

Retrieves currently trending cryptocurrencies.

**Arguments**:
- `limit` (Optional[int]): Maximum number of trending coins to retrieve (default: 5)
- `currency` (Optional[str]): The currency for price data (default: "USD")

**Returns**:
- `List[Dict[str, Any]]`: List of trending cryptocurrencies with market data

**Example**:
```python
trending_coins = await coinstats_tool.get_trending_coins(
    limit=3,
    currency="USD"
)
```

## Implementation Details

The Coinstats Tool is implemented in `src/tools/coinstats_tool.py` and uses the Coinstats API to retrieve cryptocurrency data and news. The tool handles authentication, request formatting, and response parsing to provide clean, usable results.

### API Interaction

1. The tool authenticates with the Coinstats API using the provided API key
2. Requests are sent to the appropriate endpoints based on the method called
3. Responses are parsed and formatted for easy consumption
4. Error handling is implemented for API issues

## Best Practices

1. **Rate Limiting**: Be mindful of API rate limits in high-frequency applications
2. **Data Freshness**: Consider the timestamp of market data for time-sensitive analyses
3. **News Filtering**: Use categories to filter news for more relevant results
4. **Error Handling**: Implement proper error handling for API connectivity issues
5. **Data Validation**: Validate important data points before making decisions based on them

## Example Agent Workflow

Here's an example of how an agent might use the Coinstats Tool in a market analysis workflow:

```python
async def crypto_market_analysis_workflow(agent):
    # Get trending coins
    trending_coins = await agent.tools.coinstats.get_trending_coins(limit=5)
    
    # Get latest news
    latest_news = await agent.tools.coinstats.get_news(
        limit=10,
        categories=["market", "bitcoin", "ethereum"]
    )
    
    # Analyze market sentiment based on news
    news_texts = [article["content"] for article in latest_news]
    sentiment_analysis = await agent.llm.analyze_sentiment(news_texts)
    
    # Get detailed data for top trending coins
    detailed_data = []
    for coin in trending_coins:
        coin_data = await agent.tools.coinstats.get_coin_data(
            coin_id=coin["id"],
            currency="USD"
        )
        detailed_data.append(coin_data)
    
    # Generate market report
    market_report = await agent.llm.generate_market_report(
        trending_coins=trending_coins,
        detailed_data=detailed_data,
        news=latest_news,
        sentiment=sentiment_analysis
    )
    
    # Share report via Twitter and Telegram
    await agent.tools.twitter.post_tweet(text=f"📊 Daily Crypto Market Report 📊\n\nCheck out our latest analysis!")
    await agent.tools.telegram.send_message(text=market_report)
    
    return "Crypto market analysis completed and reports shared"
```

## Limitations

- Subject to Coinstats API rate limits
- Data may have slight delays compared to real-time market movements
- Limited historical data availability depending on API tier
- News sources are limited to those aggregated by Coinstats

## Troubleshooting

Common issues and their solutions:

1. **Authentication Failed**: Verify your API key in the `.env` file
2. **Rate Limit Exceeded**: Implement rate limiting in your application
3. **Coin Not Found**: Check that you're using the correct coin ID
4. **API Timeout**: Implement retry logic for temporary API issues

For more help, visit our [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).
