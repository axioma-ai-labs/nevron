# Twitter (X) Tool

## Overview

The Twitter (X) Tool enables Nevron agents to interact with the Twitter/X platform, allowing them to post tweets, create threads, and engage with the platform programmatically. This integration leverages the Twitter API v1.1 to provide a seamless experience for autonomous agents.

## Features

- **Post Tweets**: Create and publish tweets with text content
- **Media Support**: Attach images to tweets
- **Thread Creation**: Create multi-tweet threads for longer content
- **Error Handling**: Robust error handling for API rate limits and other issues

## Configuration

To use the Twitter Tool, you need to configure the following environment variables in your `.env` file:

```bash
TWITTER_API_KEY=your_api_key
TWITTER_API_SECRET_KEY=your_api_secret_key
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
```

### How to Obtain Twitter API Credentials

1. Create a developer account at [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new project and app
3. Apply for Elevated access to use the v1.1 API (required for posting)
4. Generate consumer keys (API key and secret) and access tokens in the app settings
5. Ensure your app has Read and Write permissions

## Methods

### `post_tweet`

Posts a single tweet to Twitter.

**Arguments**:
- `text` (str): The content of the tweet (max 280 characters)
- `media_paths` (Optional[List[str]]): List of paths to media files to attach (optional)

**Returns**:
- `Dict[str, Any]`: Response from Twitter API containing tweet details

**Example**:
```python
result = await twitter_tool.post_tweet(
    text="Exploring the latest developments in AI with #Nevron! Check out our autonomous agent framework: https://github.com/axioma-ai-labs/nevron",
)
```

### `create_thread`

Creates a thread of multiple tweets.

**Arguments**:
- `tweets` (List[str]): List of tweet texts to post as a thread
- `media_paths` (Optional[List[str]]): List of paths to media files to attach to the first tweet (optional)

**Returns**:
- `List[Dict[str, Any]]`: List of responses from Twitter API for each tweet in the thread

**Example**:
```python
thread_tweets = [
    "1/4 Introducing Nevron: An open-source framework for building autonomous AI agents in Python.",
    "2/4 Nevron features modular architecture with planning, memory, feedback, and execution components.",
    "3/4 Integrate with various services like Twitter, Discord, Telegram, and more using our tool system.",
    "4/4 Get started today: https://github.com/axioma-ai-labs/nevron #AI #Agents #Python"
]

results = await twitter_tool.create_thread(tweets=thread_tweets)
```

## Implementation Details

The Twitter Tool is implemented in `src/tools/twitter_tool.py` and uses the `tweepy` library to interact with the Twitter API. The tool handles authentication, rate limiting, and error handling to ensure reliable operation.

### Authentication Flow

1. The tool initializes with API credentials from environment variables
2. Tweepy client is created with appropriate authentication
3. API calls are made through the client with error handling

### Error Handling

The tool implements comprehensive error handling for common Twitter API issues:

- Rate limiting: Implements exponential backoff
- Authentication errors: Provides clear error messages
- Content policy violations: Reports specific violation details
- Network issues: Implements retries with timeout

## Best Practices

1. **Character Limits**: Keep tweets under 280 characters
2. **Media Handling**: Supported formats include JPG, PNG, GIF, and MP4
3. **Rate Limits**: Be mindful of Twitter API rate limits (300 tweets per 3 hours)
4. **Content Guidelines**: Ensure content complies with Twitter's terms of service
5. **Error Handling**: Implement proper error handling in your agent's workflow

## Example Agent Workflow

Here's an example of how an agent might use the Twitter Tool in a workflow:

```python
async def twitter_workflow(agent, topic):
    # Research the topic using Perplexity
    research_results = await agent.tools.perplexity.search(topic)
    
    # Generate a tweet based on research
    tweet_content = await agent.llm.generate_content(
        prompt=f"Create a tweet about {topic} based on this research: {research_results}",
        max_length=280
    )
    
    # Post to Twitter
    try:
        result = await agent.tools.twitter.post_tweet(text=tweet_content)
        return f"Successfully posted tweet: {result['data']['id']}"
    except Exception as e:
        return f"Failed to post tweet: {str(e)}"
```

## Limitations

- Requires Twitter API v1.1 access (Elevated access)
- Subject to Twitter API rate limits
- Media uploads limited to 4 per tweet
- No support for Twitter Spaces or other advanced features

## Troubleshooting

Common issues and their solutions:

1. **Authentication Failed**: Verify your API credentials in the `.env` file
2. **Rate Limit Exceeded**: Reduce posting frequency or implement longer delays
3. **Media Upload Failed**: Check file formats and sizes (under 5MB for images)
4. **Tweet Creation Failed**: Ensure content doesn't violate Twitter's policies

For more help, visit our [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).
