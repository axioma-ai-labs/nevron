import asyncio
from typing import Callable, Optional

import urllib3
from loguru import logger
from whatsapp_api_client_python.API import GreenAPI

from src.core.config import settings
from src.core.exceptions import WhatsAppError


# Disable SSL warning for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def format_phone_number(phone: str) -> str:
    """Format phone number to WhatsApp API format."""
    # Remove any non-digit characters
    clean_number = "".join(filter(str.isdigit, phone))
    # Add required suffix for WhatsApp API
    return f"{clean_number}@c.us"


class WhatsAppClient:
    def __init__(self):
        self.id_instance = settings.WHATSAPP_ID_INSTANCE
        self.api_token = settings.WHATSAPP_API_TOKEN
        self._callback = None

    async def initialize(self) -> None:
        """Initialize WhatsApp client with authentication credentials."""
        try:
            self.client = GreenAPI(idInstance=self.id_instance, apiTokenInstance=self.api_token)
            # Patch the session to disable SSL verification
            if hasattr(self.client, "session"):
                self.client.session.verify = False
            logger.info("WhatsApp client initialized successfully")
        except Exception as e:
            error_msg = f"Failed to initialize WhatsApp client: {str(e)}"
            logger.error(error_msg)
            raise WhatsAppError(error_msg) from e

    async def listen_to_messages(self, callback: Callable) -> None:
        """Listen for incoming WhatsApp messages."""
        self._callback = callback

        try:
            while True:  # Continuous polling
                try:
                    notification = self.client.receiving.receiveNotification()
                    logger.debug(f"Received notification: {notification}")
                    if notification and isinstance(notification, dict):
                        if (
                            notification.get("body", {}).get("typeWebhook")
                            == "incomingMessageReceived"
                            and notification.get("body", {})
                            .get("messageData", {})
                            .get("typeMessage")
                            == "textMessage"
                        ):
                            message_data = {
                                "phone": format_phone_number(
                                    notification["body"]["senderData"]["sender"]
                                ),
                                "content": notification["body"]["messageData"]["textMessageData"][
                                    "textMessage"
                                ],
                                "timestamp": notification["body"].get("timestamp"),
                            }
                            await callback(message_data)

                            # Delete the processed notification
                            receipt_id = notification.get("receiptId")
                            if receipt_id:
                                self.client.receiving.deleteNotification(receipt_id)

                    await asyncio.sleep(1)  # Add delay between polls

                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
                    await asyncio.sleep(5)  # Longer delay on error

        except Exception as e:
            error_msg = f"Error in message listening: {str(e)}"
            logger.error(error_msg)
            raise WhatsAppError(error_msg) from e

    async def send_message(self, recipient_id: str, content: str) -> Optional[str]:
        """
        Send a message to a specific WhatsApp user.

        Args:
            recipient_id (str): Phone number or WhatsApp ID of recipient
            content (str): Message content to send

        Returns:
            Optional[str]: Message ID if successful
        """
        try:
            formatted_id = format_phone_number(recipient_id)
            response = await self.client.sending.sendMessage(chatId=formatted_id, message=content)

            if response.status_code != 200:
                raise WhatsAppError(f"Failed to send message: {response.text}")

            message_id = response.data.get("idMessage")
            logger.debug(f"Message sent successfully to WhatsApp with ID: {message_id}")
            return message_id

        except Exception as e:
            error_msg = f"Failed to send message to WhatsApp: {str(e)}"
            logger.error(error_msg)
            raise WhatsAppError(error_msg) from e
