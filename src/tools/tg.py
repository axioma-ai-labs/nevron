from typing import List

from loguru import logger
from telegram import Bot
from telegram.constants import MessageLimit, ParseMode
from telegram.error import TelegramError

from src.core.config import settings
from src.core.exceptions import TelegramError as TelegramPostError


# Initialize the bot
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)


def split_long_message(message: str, chunk_size: int = MessageLimit.MAX_TEXT_LENGTH) -> List[str]:
    """
    Split a long message into chunks that fit within Telegram's message size limit.

    Args:
        message (str): The message to split
        chunk_size (int): Maximum size of each chunk (default: Telegram's limit)

    Returns:
        List[str]: List of message chunks
    """
    # If message is short enough, return it as a single chunk
    if len(message) <= chunk_size:
        return [message]

    chunks = []
    while len(message) > chunk_size:
        chunks.append(message[:chunk_size])
        message = message[chunk_size:]
    chunks.append(message)
    return chunks


async def post_summary_to_telegram(summary_html: str, bot: Bot = bot) -> List[int]:
    """
    Post an HTML-formatted message to the Telegram channel.
    If the message is too long, it will be split into multiple messages.

    Args:
        summary_html (str): The summary text in HTML format.

    Returns:
        List[int]: List of message IDs of the posted messages.

    Raises:
        TelegramPostError: If any message fails to send or if no message ID is returned.
    """
    try:
        message_chunks = split_long_message(summary_html)
        message_ids = []

        for chunk in message_chunks:
            message = await bot.send_message(
                chat_id=settings.TELEGRAM_CHAT_ID,
                text=chunk,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=False,
            )
            if not message or not message.message_id:
                raise TelegramPostError("No message ID returned from Telegram")
            message_ids.append(message.message_id)
            logger.debug(
                f"Message chunk sent successfully to Telegram with ID: {message.message_id}"
            )

        return message_ids

    except TelegramError as e:
        error_msg = f"Failed to send message to Telegram: {str(e)}"
        raise TelegramPostError(error_msg) from e
