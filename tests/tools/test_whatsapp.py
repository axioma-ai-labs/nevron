# from unittest.mock import AsyncMock, MagicMock, patch

# import pytest

# from src.core.exceptions import WhatsAppError
# from src.tools.whatsapp import WhatsAppClient, format_phone_number


# # Test constants
# ID_INSTANCE = "test-instance"
# API_TOKEN = "test-token"
# PHONE_NUMBER = "1234567890"
# FORMATTED_PHONE = "1234567890@c.us"


# @pytest.fixture
# def mock_settings(monkeypatch):
#     """Fixture to mock settings for the tests."""
#     monkeypatch.setattr("src.tools.whatsapp.settings.WHATSAPP_ID_INSTANCE", ID_INSTANCE)
#     monkeypatch.setattr("src.tools.whatsapp.settings.WHATSAPP_API_TOKEN", API_TOKEN)


# @pytest.fixture
# def mock_green_api():
#     """Fixture to mock the GreenAPI client."""
#     mock_instance = MagicMock()
#     mock_instance.sending = MagicMock()
#     mock_instance.sending.sendMessage = AsyncMock()
#     mock_instance.receiving = MagicMock()
#     mock_instance.receiving.receiveNotification = MagicMock()
#     mock_instance.receiving.deleteNotification = MagicMock()
#     mock_instance.session = MagicMock()
#     return mock_instance


# @pytest.fixture
# async def whatsapp_client(mock_settings, mock_green_api):
#     """Fixture to create a WhatsAppClient instance with mocked dependencies."""
#     with patch("src.tools.whatsapp.GreenAPI", return_value=mock_green_api):
#         client = WhatsAppClient()
#         await client.initialize()
#         yield client


# @pytest.mark.asyncio
# async def test_initialize_success(whatsapp_client):
#     """Test successful initialization of WhatsApp client."""
#     # Act
#     await whatsapp_client.initialize()

#     # Assert
#     assert whatsapp_client.client is not None
#     assert hasattr(whatsapp_client.client, "session")
#     assert not whatsapp_client.client.session.verify


# @pytest.mark.asyncio
# async def test_initialize_failure(mock_settings):
#     """Test initialization failure of WhatsApp client."""
#     # Arrange
#     with patch("src.tools.whatsapp.GreenAPI", side_effect=Exception("Initialization failed")):
#         client = WhatsAppClient()

#         # Act & Assert
#         with pytest.raises(
#             WhatsAppError, match="Failed to initialize WhatsApp client: Initialization failed"
#         ):
#             await client.initialize()


# @pytest.mark.asyncio
# async def test_send_message_success(whatsapp_client):
#     """Test successfully sending a WhatsApp message."""
#     # Arrange
#     content = "Hello, WhatsApp!"
#     mock_response = MagicMock()
#     mock_response.status_code = 200
#     mock_response.data = {"idMessage": "test-message-id"}
#     whatsapp_client.client.sending.sendMessage.return_value = mock_response

#     # Act
#     message_id = await whatsapp_client.send_message(PHONE_NUMBER, content)

#     # Assert
#     assert message_id == "test-message-id"
#     whatsapp_client.client.sending.sendMessage.assert_awaited_once_with(
#         chatId=FORMATTED_PHONE, message=content
#     )


# @pytest.mark.asyncio
# async def test_listen_to_messages(whatsapp_client):
#     """Test listening to WhatsApp messages."""
#     # Arrange
#     mock_callback = AsyncMock()
#     mock_notification = {
#         "body": {
#             "typeWebhook": "incomingMessageReceived",
#             "messageData": {
#                 "typeMessage": "textMessage",
#                 "textMessageData": {"textMessage": "Test message"},
#             },
#             "senderData": {"sender": PHONE_NUMBER},
#             "timestamp": 1234567890,
#         },
#         "receiptId": "test-receipt-id",
#     }

#     # Change AsyncMock to MagicMock for synchronous methods
#     whatsapp_client.client.receiving.receiveNotification = MagicMock(
#         side_effect=[
#             mock_notification,  # First call returns the notification
#             KeyboardInterrupt,  # Second call raises KeyboardInterrupt
#         ]
#     )
#     whatsapp_client.client.receiving.deleteNotification = MagicMock()

#     # Act
#     try:
#         await whatsapp_client.listen_to_messages(mock_callback)
#     except KeyboardInterrupt:
#         pass  # Expected to break the loop

#     # Assert
#     mock_callback.assert_awaited_once_with(
#         {"phone": FORMATTED_PHONE, "content": "Test message", "timestamp": 1234567890}
#     )
#     whatsapp_client.client.receiving.deleteNotification.assert_called_once_with("test-receipt-id")


# def test_format_phone_number():
#     """Test phone number formatting function."""
#     # Test cases
#     assert format_phone_number("1234567890") == FORMATTED_PHONE
#     assert format_phone_number("+1-234-567-890") == FORMATTED_PHONE
#     assert format_phone_number(" 123.456.7890 ") == FORMATTED_PHONE
