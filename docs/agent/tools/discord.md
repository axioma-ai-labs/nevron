# Discord Integration

## Setup

1. Create a Discord Application and Bot 
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a "New Application" 
   - Go to the "Bot" section and create a bot
   - Choose appropriate bot rights (actions to perform) and copy the bot token

2. Configure Environment Variables
   Add these to your `.env` file:
   ```bash
   DISCORD_BOT_TOKEN=your_bot_token_here
   DISCORD_CHANNEL_ID=your_channel_id
   ```

3. Invite Bot to Server
   - Go to OAuth2 > URL Generator
   - Select scopes: `bot`
   - Select permissions: 
     - Read Messages/View Channels
     - Send Messages
     - Add Reactions
   - Copy and use the generated URL to invite the bot


### Basic Bot Setup
```python
from src.tools.discord import DiscordTool

# Initialize and start bot
discord = DiscordTool()
await discord.initialize_bot()
```

## Example Usage
A bot that responds to greetings and adds reactions:

```python
async def handle_message(message_data):
    if message_data['content'].lower() in ['hi', 'hello']:
        # Send response
        msg_id = await discord.send_message(
            channel_id=settings.DISCORD_CHANNEL_ID,
            content=f"Hello {message_data['username']}! 👋"
        )
        # Add reaction
        await discord.add_reaction(
            channel_id=settings.DISCORD_CHANNEL_ID,
            message_id=msg_id,
            emoji="👋"
        )

# Start listening
await discord.listen_to_messages(
    channel_id=settings.DISCORD_CHANNEL_ID,
    callback=handle_message
)
```

This example demonstrates:
- Message sending
- Message listening
- Adding reactions
- Basic interaction flow

## Features
- Send messages to specific channels
- Listen for incoming messages
- Add reactions to messages
- Handle reaction events
- Error handling and logging

 ## TODOs for Future Enhancements:

Support advanced message commands.
Add the ability to send/receive attachments.
Add reaction support for messages.
Implement permission-based access control.

## Reference
For implementation details, see: tools/discord.py
