from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from src.core.exceptions import DiscordError
from src.tools.discord import DiscordBot, DiscordTool


# Test constants
TOKEN = "mock-token"
CHANNEL_ID = 123456789
MESSAGE_ID = 987654321


@pytest.fixture
def mock_settings(monkeypatch):
    """Fixture to mock settings for the tests."""
    monkeypatch.setattr("src.tools.discord.settings.DISCORD_BOT_TOKEN", TOKEN)
    monkeypatch.setattr("src.tools.discord.settings.DISCORD_CHANNEL_ID", CHANNEL_ID)


@pytest.fixture
def mock_discord_bot():
    """Fixture to mock the DiscordBot."""
    with patch("src.tools.discord.DiscordBot", autospec=True) as mock_bot_class:
        mock_bot_instance = AsyncMock(spec=DiscordBot)
        mock_bot_instance.start = AsyncMock()
        mock_bot_instance.close = AsyncMock()

        # Create a mock channel that inherits from TextChannel
        mock_channel = MagicMock(spec=discord.TextChannel)
        mock_channel.send = AsyncMock(return_value=MagicMock(id=MESSAGE_ID))
        mock_channel.fetch_message = AsyncMock()

        mock_bot_instance.get_channel = MagicMock(return_value=mock_channel)
        mock_bot_class.return_value = mock_bot_instance
        yield mock_bot_instance


@pytest.fixture
def discord_tool(mock_discord_bot, mock_settings):
    """Fixture to create a DiscordTool instance with a mocked DiscordBot."""
    return DiscordTool()


@pytest.mark.asyncio
async def test_initialize_bot_success(discord_tool, mock_discord_bot):
    """Test successful initialization of the Discord bot."""
    # Act
    await discord_tool.initialize_bot()

    # Assert
    mock_discord_bot.start.assert_awaited_once_with(TOKEN)


@pytest.mark.asyncio
async def test_initialize_bot_failure(discord_tool, mock_discord_bot):
    """Test initialization of the Discord bot with an exception."""
    # Arrange
    mock_discord_bot.start = AsyncMock(side_effect=Exception("Initialization failed"))

    # Act & Assert
    with pytest.raises(
        DiscordError, match="Failed to initialize Discord bot: Initialization failed"
    ):
        await discord_tool.initialize_bot()
    mock_discord_bot.start.assert_awaited_once_with(TOKEN)


@pytest.mark.asyncio
async def test_send_message_success(discord_tool, mock_discord_bot):
    """Test successfully sending a message to a Discord channel."""
    # Arrange
    content = "Hello, Bot!"
    mock_channel = mock_discord_bot.get_channel.return_value
    mock_channel.send.return_value = MagicMock(id=MESSAGE_ID)

    # Act
    message_id = await discord_tool.send_message(CHANNEL_ID, content)

    # Assert
    mock_discord_bot.get_channel.assert_called_once_with(CHANNEL_ID)
    mock_channel.send.assert_awaited_once_with(content)
    assert message_id == MESSAGE_ID


@pytest.mark.asyncio
async def test_send_message_channel_not_found(discord_tool, mock_discord_bot):
    """Test sending a message to a non-existent Discord channel."""
    # Arrange
    content = "Hello, Discord!"
    mock_discord_bot.get_channel.return_value = None

    # Act & Assert
    with pytest.raises(DiscordError, match=f"Channel {CHANNEL_ID} not found"):
        await discord_tool.send_message(CHANNEL_ID, content)
    mock_discord_bot.get_channel.assert_called_once_with(CHANNEL_ID)


@pytest.mark.asyncio
async def test_send_message_api_error(discord_tool, mock_discord_bot):
    """Test handling an API error when sending a message."""
    # Arrange
    content = "Hello, Discord!"
    mock_channel = mock_discord_bot.get_channel.return_value
    mock_channel.send = AsyncMock(side_effect=Exception("API failure"))

    # Act & Assert
    with pytest.raises(DiscordError, match="Failed to send message to Discord: API failure"):
        await discord_tool.send_message(CHANNEL_ID, content)
    mock_discord_bot.get_channel.assert_called_once_with(CHANNEL_ID)
    mock_channel.send.assert_awaited_once_with(content)


@pytest.mark.asyncio
async def test_listen_to_messages(discord_tool, mock_discord_bot):
    """Test listening to messages in a specific Discord channel and invoking the callback."""
    # Arrange
    channel_id = CHANNEL_ID
    callback = AsyncMock()

    # Act
    await discord_tool.listen_to_messages(channel_id, callback)

    # Assert
    assert discord_tool._callback == callback

    # Simulate receiving a message
    mock_message = MagicMock()
    mock_message.channel.id = channel_id
    mock_message.author.bot = False
    mock_message.author.name = "TestUser"
    mock_message.content = "Hello Bot"

    # Get the on_message event handler and call it
    on_message = discord_tool.bot.event.call_args_list[0][0][0]
    await on_message(mock_message)

    # Assert callback was called with correct data
    callback.assert_awaited_once_with({"username": "TestUser", "content": "Hello Bot"})


@pytest.mark.asyncio
async def test_listen_to_messages_with_bot_message(discord_tool, mock_discord_bot):
    """Test that the callback is not invoked when the message is from a bot."""
    # Arrange
    channel_id = CHANNEL_ID
    callback = AsyncMock()

    await discord_tool.listen_to_messages(channel_id, callback)
    # Assert
    assert discord_tool._callback == callback

    # Simulate receiving a message from a bot
    mock_message = AsyncMock()
    mock_message.channel.id = channel_id
    mock_message.author.bot = True
    mock_message.content = "Bot message"

    # Trigger the on_message event
    event_handler = AsyncMock()
    with patch.object(discord_tool.bot, "event", return_value=event_handler):
        await event_handler(mock_message)
        callback.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_reaction_success(discord_tool, mock_discord_bot):
    """Test successfully adding a reaction to a message."""
    # Arrange
    emoji = "👍"
    mock_channel = mock_discord_bot.get_channel.return_value
    mock_message = MagicMock()
    mock_message.add_reaction = AsyncMock()
    mock_channel.fetch_message = AsyncMock(return_value=mock_message)

    # Act
    result = await discord_tool.add_reaction(CHANNEL_ID, MESSAGE_ID, emoji)

    # Assert
    mock_discord_bot.get_channel.assert_called_once_with(CHANNEL_ID)
    mock_channel.fetch_message.assert_awaited_once_with(MESSAGE_ID)
    mock_message.add_reaction.assert_awaited_once_with(emoji)
    assert result is True


@pytest.mark.asyncio
async def test_close_bot(discord_tool, mock_discord_bot):
    """Test closing the Discord bot."""
    # Act
    await discord_tool.bot.close()
    # Assert
    mock_discord_bot.close.assert_awaited_once()
