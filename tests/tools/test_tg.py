from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Bot, Message
from telegram.constants import MessageLimit, ParseMode
from telegram.error import TelegramError

from src.core.exceptions import TelegramError as TelegramPostError
from src.tools.tg import TelegramTool


@pytest.fixture
def telegram_tool(mock_bot):
    """Fixture to create a TelegramTool instance with mocked bot."""
    with patch("src.tools.tg.Bot", return_value=mock_bot):
        return TelegramTool()


@pytest.fixture
def mock_bot():
    """Mock the Telegram Bot instance."""
    return AsyncMock(spec=Bot)


@pytest.mark.parametrize(
    "message,chunk_size,expected",
    [
        ("Short message", MessageLimit.MAX_TEXT_LENGTH, ["Short message"]),
        (
            "A" * (MessageLimit.MAX_TEXT_LENGTH + 10),
            MessageLimit.MAX_TEXT_LENGTH,
            ["A" * MessageLimit.MAX_TEXT_LENGTH, "A" * 10],
        ),
        ("", MessageLimit.MAX_TEXT_LENGTH, [""]),
    ],
)
def test_split_long_message(telegram_tool, message, chunk_size, expected):
    """Test splitting long messages into chunks."""
    result = telegram_tool._split_long_message(message, chunk_size=chunk_size)
    assert result == expected


@pytest.mark.asyncio
async def test_post_summary_success(telegram_tool, mock_bot):
    """Test successfully posting a message to Telegram."""
    # Arrange
    summary_html = "<b>Test message</b>"
    mock_message = MagicMock(spec=Message)
    mock_message.message_id = 12345

    with (
        patch.object(telegram_tool, "bot", mock_bot),
        patch("src.tools.tg.settings.TELEGRAM_CHAT_ID", "1234567890"),
    ):
        mock_bot.send_message.return_value = mock_message

        # Act
        result = await telegram_tool.post_summary(summary_html)

        # Assert
        assert result == [12345]
        mock_bot.send_message.assert_called_once_with(
            chat_id="1234567890",
            text=summary_html,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=False,
        )


@pytest.mark.asyncio
async def test_post_summary_long_message(telegram_tool, mock_bot):
    """Test posting a long message split into multiple chunks."""
    # Arrange
    summary_html = "<b>" + "A" * (MessageLimit.MAX_TEXT_LENGTH + 50) + "</b>"
    message_chunks = telegram_tool._split_long_message(summary_html)

    # Create mock messages with proper message_id attributes
    mock_messages = [
        MagicMock(spec=Message, message_id=i + 1)  # message_id starts from 1
        for i in range(len(message_chunks))
    ]

    with (
        patch.object(telegram_tool, "bot", mock_bot),
        patch("src.tools.tg.settings.TELEGRAM_CHAT_ID", "1234567890"),
    ):
        mock_bot.send_message.side_effect = mock_messages

        # Act
        result = await telegram_tool.post_summary(summary_html)

        # Assert
        assert result == [msg.message_id for msg in mock_messages]
        assert mock_bot.send_message.call_count == len(message_chunks)
        for i, chunk in enumerate(message_chunks):
            mock_bot.send_message.assert_any_call(
                chat_id="1234567890",
                text=chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )


@pytest.mark.asyncio
async def test_post_summary_no_message_id(telegram_tool, mock_bot):
    """Test handling when no message ID is returned."""
    # Arrange
    summary_html = "<b>Test message</b>"

    with (
        patch.object(telegram_tool, "bot", mock_bot),
        patch("src.tools.tg.settings.TELEGRAM_CHAT_ID", "1234567890"),
    ):
        mock_bot.send_message.return_value = None

        # Act & Assert
        with pytest.raises(TelegramPostError, match="No message ID returned from Telegram"):
            await telegram_tool.post_summary(summary_html)


@pytest.mark.asyncio
async def test_post_summary_telegram_error(telegram_tool, mock_bot):
    """Test handling a TelegramError during message posting."""
    # Arrange
    summary_html = "<b>Test message</b>"

    with (
        patch.object(telegram_tool, "bot", mock_bot),
        patch("src.tools.tg.settings.TELEGRAM_CHAT_ID", "1234567890"),
    ):
        mock_bot.send_message.side_effect = TelegramError("Mock Telegram error")

        # Act & Assert
        with pytest.raises(TelegramPostError, match="Failed to send message to Telegram"):
            await telegram_tool.post_summary(summary_html)
