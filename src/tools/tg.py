from typing import List

from loguru import logger
from telegram import Bot
from telegram.constants import MessageLimit, ParseMode
from telegram.error import TelegramError

from src.core.config import settings
from src.core.exceptions import TelegramError as TelegramPostError


class TelegramTool:
    """Tool for interacting with the Telegram API."""

    def __init__(self):
        """Initialize the Telegram tool with bot instance."""
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

    def _split_long_message(
        self, message: str, chunk_size: int = MessageLimit.MAX_TEXT_LENGTH
    ) -> List[str]:
        """Split a long message into chunks that fit within Telegram's message size limit."""
        if len(message) <= chunk_size:
            return [message]

        chunks = []
        while len(message) > chunk_size:
            chunks.append(message[:chunk_size])
            message = message[chunk_size:]
        chunks.append(message)
        return chunks

    async def post_summary(self, summary_html: str) -> List[int]:
        """Post an HTML-formatted message to the Telegram channel."""
        try:
            message_chunks = self._split_long_message(summary_html)
            message_ids = []

            for chunk in message_chunks:
                message = await self.bot.send_message(
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
