# Telegram Tool

## Overview

The Telegram Tool enables Nevron agents to interact with the Telegram messaging platform, allowing them to send messages to channels, groups, and individual users. This integration leverages the Telegram Bot API to provide a seamless communication channel for autonomous agents.

## Features

- **Send Messages**: Send text messages to channels, groups, or users
- **HTML Formatting**: Support for rich text formatting using HTML
- **Media Support**: Send images, documents, and other media types
- **Channel/Group Support**: Send messages to public or private channels and groups
- **Error Handling**: Robust error handling for API issues

## Configuration

To use the Telegram Tool, you need to configure the following environment variables in your `.env` file:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_default_chat_id
```

### How to Obtain Telegram Bot Credentials

1. Talk to [BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with the `/newbot` command
3. Copy the token provided (this is your `TELEGRAM_BOT_TOKEN`)
4. Add the bot to your group or channel
5. To get the chat ID:
   - For groups: Use the [@username_to_id_bot](https://t.me/username_to_id_bot) or send a message to the group and check the chat ID via the Telegram API
   - For channels: Forward a message from the channel to the [@username_to_id_bot](https://t.me/username_to_id_bot)

## Methods

### `send_message`

Sends a text message to a Telegram chat.

**Arguments**:
- `text` (str): The content of the message
- `chat_id` (Optional[str]): The chat ID to send the message to (defaults to `TELEGRAM_CHAT_ID` from environment)
- `parse_mode` (Optional[str]): The parsing mode for the message ('HTML' or 'Markdown', default is 'HTML')

**Returns**:
- `Dict[str, Any]`: Response from Telegram API containing message details

**Example**:
```python
result = await telegram_tool.send_message(
    text="<b>Important update</b>: New features have been added to Nevron!",
    parse_mode="HTML"
)
```

### `send_photo`

Sends an image with optional caption to a Telegram chat.

**Arguments**:
- `photo_path` (str): Path to the image file
- `caption` (Optional[str]): Caption for the image
- `chat_id` (Optional[str]): The chat ID to send the message to (defaults to `TELEGRAM_CHAT_ID` from environment)
- `parse_mode` (Optional[str]): The parsing mode for the caption ('HTML' or 'Markdown', default is 'HTML')

**Returns**:
- `Dict[str, Any]`: Response from Telegram API containing message details

**Example**:
```python
result = await telegram_tool.send_photo(
    photo_path="path/to/image.jpg",
    caption="<i>Chart showing recent performance</i>",
    parse_mode="HTML"
)
```

### `send_document`

Sends a document file to a Telegram chat.

**Arguments**:
- `document_path` (str): Path to the document file
- `caption` (Optional[str]): Caption for the document
- `chat_id` (Optional[str]): The chat ID to send the message to (defaults to `TELEGRAM_CHAT_ID` from environment)
- `parse_mode` (Optional[str]): The parsing mode for the caption ('HTML' or 'Markdown', default is 'HTML')

**Returns**:
- `Dict[str, Any]`: Response from Telegram API containing message details

**Example**:
```python
result = await telegram_tool.send_document(
    document_path="path/to/report.pdf",
    caption="<b>Monthly Report</b> - January 2024",
    parse_mode="HTML"
)
```

## Implementation Details

The Telegram Tool is implemented in `src/tools/telegram_tool.py` and uses the `python-telegram-bot` library to interact with the Telegram API. The tool handles authentication, message formatting, and error handling to ensure reliable operation.

### Authentication Flow

1. The tool initializes with the bot token from environment variables
2. The Telegram client is created with appropriate authentication
3. API calls are made through the client with error handling

### HTML Formatting

The Telegram Tool supports HTML formatting for rich text messages. Supported tags include:

- `<b>` and `</b>` for bold text
- `<i>` and `</i>` for italic text
- `<u>` and `</u>` for underlined text
- `<s>` and `</s>` for strikethrough text
- `<a href="...">` and `</a>` for links
- `<code>` and `</code>` for monospace text
- `<pre>` and `</pre>` for pre-formatted text

## Best Practices

1. **Message Length**: Keep messages under 4096 characters
2. **Media Handling**: Supported formats include JPG, PNG, GIF, and PDF
3. **Rate Limits**: Be mindful of Telegram API rate limits
4. **Content Guidelines**: Ensure content complies with Telegram's terms of service
5. **Error Handling**: Implement proper error handling in your agent's workflow

## Example Agent Workflow

Here's an example of how an agent might use the Telegram Tool in a workflow:

```python
async def telegram_report_workflow(agent, research_topic):
    # Research the topic using Perplexity
    research_results = await agent.tools.perplexity.search(research_topic)
    
    # Generate a report based on research
    report_content = await agent.llm.generate_content(
        prompt=f"Create a detailed report about {research_topic} based on this research: {research_results}",
    )
    
    # Format the report with HTML
    formatted_report = f"<b>Research Report: {research_topic}</b>\n\n{report_content}"
    
    # Send to Telegram
    try:
        result = await agent.tools.telegram.send_message(text=formatted_report)
        return f"Successfully sent report to Telegram"
    except Exception as e:
        return f"Failed to send report: {str(e)}"
```

## Limitations

- Maximum message length of 4096 characters
- Media file size limits (10MB for photos, 50MB for files)
- Rate limiting by Telegram API
- Bot must be added to channels/groups before sending messages

## Troubleshooting

Common issues and their solutions:

1. **Authentication Failed**: Verify your bot token in the `.env` file
2. **Chat Not Found**: Ensure the chat ID is correct and the bot is a member of the chat
3. **Permission Denied**: Make sure the bot has permission to post in the channel/group
4. **Media Upload Failed**: Check file formats and sizes

For more help, visit our [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).
