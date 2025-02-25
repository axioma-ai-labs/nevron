# Slack Integration

## Setup

1. Create a Slack App
   - Go to [Slack API Apps page](https://api.slack.com/apps)
   - Click "Create New App" > "From scratch"
   - Choose an app name and workspace
   - Save the app configuration

2. Configure Bot Token and Permissions
   - Navigate to "OAuth & Permissions" in your app settings
   - Under "Scopes", add these Bot Token Scopes:
     - `chat:write` (Send messages)
     - `channels:history` (View messages in channels)
     - `channels:read` (View basic channel info)
     - `im:history` (View direct messages)
     - `users:read` (View basic user info)
   - Click "Install to Workspace"
   - Copy the "Bot User OAuth Token"

3. Configure Environment Variables
   Add these to your `.env` file:
   ```bash
   SLACK_BOT_TOKEN=xoxb-your-bot-token-here
   SLACK_APP_TOKEN=xapp-your-app-token-here
   SLACK_SIGNING_SECRET=your-signing-secret-here
   ```

### Basic Setup
```python
from src.tools.slack import SlackClient

# Initialize Slack client
slack = SlackClient()

# Send a message to a channel
response = slack.send_message(
    channel="#general",
    text="Hello from your AI assistant!"
)

# Listen for messages
@slack.event("message")
def handle_message(event):
    channel = event["channel"]
    text = event["text"]
    slack.send_message(channel=channel, text=f"Received: {text}")
```

## Features
- Real-time message handling with event subscriptions
- Send and receive messages in channels and DMs
- Process message threads and replies
- Support for rich message formatting and blocks
- Message history and context management
- User and channel information retrieval
- Efficient caching of API client

## TODOs for Future Enhancements:
- Add support for Slack modals and interactive components
- Implement slash commands
- Add support for message reactions
- Implement file management features
- Add support for user presence tracking
- Implement workspace analytics
- Add support for app home customization
- Implement message scheduling features
- Manage interactive components such as buttons and menus
- Enhance error handling and retry mechanisms for API interactions

## Reference
For implementation details, see: `src/tools/slack.py`

The implementation uses the official Slack Bolt Framework. For more information, refer to:
- [Slack API Documentation](https://api.slack.com/docs)
- [Slack Bolt Python Framework](https://slack.dev/bolt-python/concepts)

### Bot Memory
The Slack integration maintains conversation history through a message store that:
- Tracks message threads and their context
- Stores recent interactions per channel/user
- Maintains conversation state for ongoing dialogues
- Implements memory cleanup for older messages
- Supports context retrieval for follow-up responses

Example of history usage:
```python
# Access conversation history
history = slack.get_conversation_history(channel_id)

# Get context for a specific thread
thread_context = slack.get_thread_context(thread_ts)

# Store custom context
slack.store_context(
    channel_id=channel,
    thread_ts=thread,
    context={"key": "value"}
)
```
