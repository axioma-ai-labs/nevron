import unittest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import DiscordError, LensError, SlackError, WhatsAppError
from src.execution.social_media_executors import (
    FetchLensExecutor,
    ListenDiscordMessagesExecutor,
    ListenSlackMessagesExecutor,
    ListenWhatsAppMessagesExecutor,
    PostLensExecutor,
    PostTweetExecutor,
    SendDiscordMessageExecutor,
    SendSlackMessageExecutor,
    SendTelegramMessageExecutor,
    SendWhatsAppMessageExecutor,
)


class TestPostTweetExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Twitter client
        self.patcher = patch("src.execution.social_media_executors.TwitterTool")
        self.mock_twitter_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_twitter_tool.return_value = self.mock_client
        self.executor = PostTweetExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["tweet_text"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful tweet posting."""
        # Set up mock return value
        tweet_ids: List[int] = [123456789]
        self.mock_client.post_thread = AsyncMock(return_value=tweet_ids)

        # Test with valid context
        context: Dict[str, str] = {"tweet_text": "This is a test tweet"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Tweet posted: This is a test tweet...")
        self.mock_client.post_thread.assert_called_once_with({"tweet1": "This is a test tweet"})

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.post_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_empty_tweet_text(self):
        """Test execution with empty tweet text."""
        # Test with empty tweet text
        context: Dict[str, str] = {"tweet_text": ""}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No tweet text provided")
        self.mock_client.post_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_error(self):
        """Test handling of Twitter errors."""
        # Set up mock to raise Exception
        error_message: str = "Twitter API rate limit exceeded"
        self.mock_client.post_thread = AsyncMock(side_effect=Exception(error_message))

        # Test with valid context
        context = {"tweet_text": "This is a test tweet"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, f"Failed to post tweet: {error_message}")
        self.mock_client.post_thread.assert_called_once()


class TestListenDiscordMessagesExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Discord client
        self.patcher = patch("src.execution.social_media_executors.DiscordTool")
        self.mock_discord_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_discord_tool.return_value = self.mock_client
        self.executor = ListenDiscordMessagesExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["channel_id", "message_handler"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Discord message listening."""
        # Set up mock
        self.mock_client.listen_to_messages = AsyncMock()

        # Create a message handler function
        async def message_handler(message):
            pass

        # Test with valid context
        context: Dict[str, Any] = {"channel_id": "123456789", "message_handler": message_handler}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully started listening for Discord messages")
        self.mock_client.listen_to_messages.assert_called_once_with("123456789", message_handler)

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing message handler
        context: Dict[str, str] = {
            "channel_id": "123456789"
            # Missing "message_handler"
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.listen_to_messages.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_discord_error(self):
        """Test handling of Discord errors."""
        # Set up mock to raise DiscordError
        error_message: str = "Invalid channel ID"
        self.mock_client.listen_to_messages = AsyncMock(side_effect=DiscordError(error_message))

        # Create a message handler function
        async def message_handler(message):
            pass

        # Test with valid context
        context = {"channel_id": "invalid_channel", "message_handler": message_handler}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to listen for Discord messages", str(message))
        self.assertIn("Invalid channel ID", str(message))
        self.mock_client.listen_to_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Network error"
        self.mock_client.listen_to_messages = AsyncMock(side_effect=Exception(error_message))

        # Create a message handler function
        async def message_handler(message):
            pass

        # Test with valid context
        context = {"channel_id": "123456789", "message_handler": message_handler}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while listening for Discord messages", str(message))
        self.assertIn("Network error", str(message))
        self.mock_client.listen_to_messages.assert_called_once()


class TestSendDiscordMessageExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Discord client
        self.patcher = patch("src.execution.social_media_executors.DiscordTool")
        self.mock_discord_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_discord_tool.return_value = self.mock_client
        self.executor = SendDiscordMessageExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["channel_id", "message_content"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Discord message sending."""
        # Set up mock return value
        message_id: str = "message_id_123"
        self.mock_client.send_message = AsyncMock(return_value=message_id)

        # Test with valid context
        context: Dict[str, str] = {"channel_id": "123456789", "message_content": "Hello, Discord!"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, f"Successfully sent Discord message with ID: {message_id}")
        self.mock_client.send_message.assert_called_once_with("123456789", "Hello, Discord!")

    @pytest.mark.asyncio
    async def test_execute_no_message_id(self):
        """Test when no message ID is returned."""
        # Set up mock to return None
        self.mock_client.send_message = AsyncMock(return_value=None)

        # Test with valid context
        context: Dict[str, str] = {"channel_id": "123456789", "message_content": "Hello, Discord!"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Failed to send Discord message: No message ID returned")
        self.mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing message content
        context: Dict[str, str] = {
            "channel_id": "123456789"
            # Missing "message_content"
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_discord_error(self):
        """Test handling of Discord errors."""
        # Set up mock to raise DiscordError
        error_message: str = "Permission denied"
        self.mock_client.send_message = AsyncMock(side_effect=DiscordError(error_message))

        # Test with valid context
        context = {"channel_id": "123456789", "message_content": "Hello, Discord!"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to send Discord message", str(message))
        self.assertIn("Permission denied", str(message))
        self.mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Server error"
        self.mock_client.send_message = AsyncMock(side_effect=Exception(error_message))

        # Test with valid context
        context = {"channel_id": "123456789", "message_content": "Hello, Discord!"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while sending Discord message", str(message))
        self.assertIn("Server error", str(message))
        self.mock_client.send_message.assert_called_once()


class TestSendTelegramMessageExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Telegram client
        self.patcher = patch("src.execution.social_media_executors.TelegramTool")
        self.mock_telegram_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_telegram_tool.return_value = self.mock_client
        self.executor = SendTelegramMessageExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["message_text"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Telegram message sending."""
        # Set up mock return value
        self.mock_client.post_summary = AsyncMock(return_value=[123456789])

        # Test with valid context
        context = {"message_text": "Hello, Telegram!"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Telegram message sent: Hello, Telegram!...")
        self.mock_client.post_summary.assert_called_once_with("Hello, Telegram!")

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No message text provided")
        self.mock_client.post_summary.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_empty_message(self):
        """Test execution with empty message text."""
        # Test with empty message text
        context: Dict[str, str] = {"message_text": ""}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No message text provided")
        self.mock_client.post_summary.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_error(self):
        """Test handling of Telegram errors."""
        # Set up mock to raise Exception
        error_message: str = "Telegram API error"
        self.mock_client.post_summary = AsyncMock(side_effect=Exception(error_message))

        # Test with valid context
        context: Dict[str, str] = {"message_text": "Hello, Telegram!"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, f"Failed to send Telegram message: {error_message}")
        self.mock_client.post_summary.assert_called_once()


class TestPostLensExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Lens client
        self.patcher = patch("src.execution.social_media_executors.LensProtocolTool")
        self.mock_lens_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_lens_tool.return_value = self.mock_client
        self.executor = PostLensExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["content", "profile_id"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Lens content posting."""
        # Set up mock return value
        self.mock_client.publish_content = MagicMock(
            return_value={
                "id": "lens-post-123",
                "content": "Test content",
                "timestamp": "2023-01-01T12:00:00Z",
            }
        )

        # Test with valid context
        context = {"content": "Hello, Lens Protocol!", "profile_id": "lens-profile-123"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully posted to Lens with ID: lens-post-123")
        self.mock_client.publish_content.assert_called_once_with(
            "Hello, Lens Protocol!", "lens-profile-123"
        )

    @pytest.mark.asyncio
    async def test_execute_no_result(self):
        """Test when no result is returned."""
        # Set up mock to return None
        self.mock_client.publish_content = MagicMock(return_value=None)

        # Test with valid context
        context = {"content": "Hello, Lens Protocol!", "profile_id": "lens-profile-123"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Failed to post to Lens: No result returned")
        self.mock_client.publish_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing content
        context = {
            "profile_id": "lens-profile-123"
            # Missing "content"
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.publish_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_lens_error(self):
        """Test handling of Lens errors."""
        # Set up mock to raise LensError
        error_message: str = "Authentication failed"
        self.mock_client.publish_content = MagicMock(side_effect=LensError(error_message))

        # Test with valid context
        context: Dict[str, str] = {
            "content": "Hello, Lens Protocol!",
            "profile_id": "lens-profile-123",
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to post to Lens", str(message))
        self.assertIn("Authentication failed", str(message))
        self.mock_client.publish_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Server error"
        self.mock_client.publish_content = MagicMock(side_effect=Exception(error_message))

        # Test with valid context
        context: Dict[str, str] = {
            "content": "Hello, Lens Protocol!",
            "profile_id": "lens-profile-123",
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while posting to Lens", str(message))
        self.assertIn("Server error", str(message))
        self.mock_client.publish_content.assert_called_once()


class TestFetchLensExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Lens client
        self.patcher = patch("src.execution.social_media_executors.LensProtocolTool")
        self.mock_lens_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_lens_tool.return_value = self.mock_client
        self.executor = FetchLensExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["query_params"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Lens content fetching."""
        # Set up mock return value
        mock_results = [
            {"id": "lens-post-1", "content": "Content 1"},
            {"id": "lens-post-2", "content": "Content 2"},
        ]
        self.mock_client.fetch_content = MagicMock(return_value=mock_results)

        # Test with valid context
        context = {"query_params": {"limit": 10, "orderBy": "LATEST"}}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully fetched 2 items from Lens")
        self.mock_client.fetch_content.assert_called_once_with(context["query_params"])

    @pytest.mark.asyncio
    async def test_execute_no_results(self):
        """Test when no results are found."""
        # Set up mock to return empty list
        self.mock_client.fetch_content = MagicMock(return_value=[])

        # Test with valid context
        context = {"query_params": {"limit": 10, "orderBy": "LATEST"}}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No content found matching the query")
        self.mock_client.fetch_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.fetch_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_lens_error(self):
        """Test handling of Lens errors."""
        # Set up mock to raise LensError
        error_message: str = "Invalid query parameters"
        self.mock_client.fetch_content = MagicMock(side_effect=LensError(error_message))

        # Test with valid context
        context: Dict[str, Dict[str, Any]] = {"query_params": {"limit": 10, "orderBy": "LATEST"}}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to fetch from Lens", str(message))
        self.assertIn("Invalid query parameters", str(message))
        self.mock_client.fetch_content.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Connection error"
        self.mock_client.fetch_content = MagicMock(side_effect=Exception(error_message))

        # Test with valid context
        context: Dict[str, Dict[str, Any]] = {"query_params": {"limit": 10, "orderBy": "LATEST"}}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while fetching from Lens", str(message))
        self.assertIn("Connection error", str(message))
        self.mock_client.fetch_content.assert_called_once()


class TestListenWhatsAppMessagesExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked WhatsApp client
        self.patcher = patch("src.execution.social_media_executors.WhatsAppTool")
        self.mock_whatsapp_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_whatsapp_tool.return_value = self.mock_client
        self.executor = ListenWhatsAppMessagesExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["message_handler"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful WhatsApp message listening."""
        # Set up mock
        self.mock_client.listen_to_messages = AsyncMock()

        # Create a message handler function
        async def message_handler(message):
            pass

        # Test with valid context
        context = {"message_handler": message_handler}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully started listening for WhatsApp messages")
        self.mock_client.listen_to_messages.assert_called_once_with(message_handler)

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.listen_to_messages.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_whatsapp_error(self):
        """Test handling of WhatsApp errors."""
        # Set up mock to raise WhatsAppError
        self.mock_client.listen_to_messages = AsyncMock(
            side_effect=WhatsAppError("Authentication failed")
        )

        # Create a message handler function
        async def message_handler(message):
            pass

        # Test with valid context
        context = {"message_handler": message_handler}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to listen for WhatsApp messages", str(message))
        self.assertIn("Authentication failed", str(message))
        self.mock_client.listen_to_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        self.mock_client.listen_to_messages = AsyncMock(
            side_effect=Exception("Server connection error")
        )

        # Create a message handler function
        async def message_handler(message):
            pass

        # Test with valid context
        context = {"message_handler": message_handler}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while listening for WhatsApp messages", str(message))
        self.assertIn("Server connection error", str(message))
        self.mock_client.listen_to_messages.assert_called_once()


class TestSendWhatsAppMessageExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked WhatsApp client
        self.patcher = patch("src.execution.social_media_executors.WhatsAppTool")
        self.mock_whatsapp_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_whatsapp_tool.return_value = self.mock_client
        self.executor = SendWhatsAppMessageExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["recipient_id", "message_content"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful WhatsApp message sending."""
        # Set up mock return value
        self.mock_client.send_message = AsyncMock(return_value="message_id_123")

        # Test with valid context
        context = {"recipient_id": "+1234567890", "message_content": "Hello, WhatsApp!"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully sent WhatsApp message with ID: message_id_123")
        self.mock_client.send_message.assert_called_once_with("+1234567890", "Hello, WhatsApp!")

    @pytest.mark.asyncio
    async def test_execute_no_message_id(self):
        """Test when no message ID is returned."""
        # Set up mock to return None
        self.mock_client.send_message = AsyncMock(return_value=None)

        # Test with valid context
        context = {"recipient_id": "+1234567890", "message_content": "Hello, WhatsApp!"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Failed to send WhatsApp message: No message ID returned")
        self.mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing message content
        context = {
            "recipient_id": "+1234567890"
            # Missing "message_content"
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_whatsapp_error(self):
        """Test handling of WhatsApp errors."""
        # Set up mock to raise WhatsAppError
        self.mock_client.send_message = AsyncMock(side_effect=WhatsAppError("Invalid phone number"))

        # Test with valid context
        context = {"recipient_id": "invalid_number", "message_content": "Hello, WhatsApp!"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to send WhatsApp message", str(message))
        self.assertIn("Invalid phone number", str(message))
        self.mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        self.mock_client.send_message = AsyncMock(side_effect=Exception("Connection timeout"))

        # Test with valid context
        context = {"recipient_id": "+1234567890", "message_content": "Hello, WhatsApp!"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while sending WhatsApp message", str(message))
        self.assertIn("Connection timeout", str(message))
        self.mock_client.send_message.assert_called_once()


class TestListenSlackMessagesExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Slack client
        self.patcher = patch("src.execution.social_media_executors.SlackTool")
        self.mock_slack_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_slack_tool.return_value = self.mock_client
        self.executor = ListenSlackMessagesExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["message_handler"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Slack message listening."""
        # Set up mock
        self.mock_client.listen_for_messages = AsyncMock()

        # Create a message handler function
        async def message_handler(message):
            pass

        # Test with valid context
        context = {"message_handler": message_handler}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully started listening for Slack messages")
        self.mock_client.listen_for_messages.assert_called_once_with(message_handler)

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with empty context
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.listen_for_messages.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_slack_error(self):
        """Test handling of Slack errors."""
        # Set up mock to raise SlackError
        self.mock_client.listen_for_messages = AsyncMock(
            side_effect=SlackError("Authentication failed")
        )

        # Create a message handler function
        async def message_handler(message):
            pass

        # Test with valid context
        context = {"message_handler": message_handler}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to listen for Slack messages", str(message))
        self.assertIn("Authentication failed", str(message))
        self.mock_client.listen_for_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        self.mock_client.listen_for_messages = AsyncMock(
            side_effect=Exception("Server connection error")
        )

        # Create a message handler function
        async def message_handler(message):
            pass

        # Test with valid context
        context = {"message_handler": message_handler}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while listening for Slack messages", str(message))
        self.assertIn("Server connection error", str(message))
        self.mock_client.listen_for_messages.assert_called_once()


class TestSendSlackMessageExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Slack client
        self.patcher = patch("src.execution.social_media_executors.SlackTool")
        self.mock_slack_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_slack_tool.return_value = self.mock_client
        self.executor = SendSlackMessageExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["channel_id", "message_content", "thread_ts"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Slack message sending."""
        # Set up mock
        self.mock_client.send_message = AsyncMock()

        # Test with valid context
        context = {
            "channel_id": "C123456789",
            "message_content": "Hello, Slack!",
            "thread_ts": "1234567890.123456",  # Optional in implementation but required in context
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully sent Slack message")
        self.mock_client.send_message.assert_called_once_with(
            "C123456789", "Hello, Slack!", "1234567890.123456"
        )

    @pytest.mark.asyncio
    async def test_execute_success_without_thread(self):
        """Test successful Slack message sending without thread."""
        # Set up mock
        self.mock_client.send_message = AsyncMock()

        # Test with valid context but null thread_ts
        context = {
            "channel_id": "C123456789",
            "message_content": "Hello, Slack!",
            "thread_ts": None,  # Optional but present
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Successfully sent Slack message")
        self.mock_client.send_message.assert_called_once_with("C123456789", "Hello, Slack!", None)

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing message content
        context = {
            "channel_id": "C123456789",
            # Missing "message_content" and "thread_ts"
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_slack_error(self):
        """Test handling of Slack errors."""
        # Set up mock to raise SlackError
        self.mock_client.send_message = AsyncMock(side_effect=SlackError("Channel not found"))

        # Test with valid context
        context = {
            "channel_id": "invalid_channel",
            "message_content": "Hello, Slack!",
            "thread_ts": "1234567890.123456",
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to send Slack message", str(message))
        self.assertIn("Channel not found", str(message))
        self.mock_client.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        self.mock_client.send_message = AsyncMock(side_effect=Exception("Connection timeout"))

        # Test with valid context
        context = {
            "channel_id": "C123456789",
            "message_content": "Hello, Slack!",
            "thread_ts": "1234567890.123456",
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while sending Slack message", str(message))
        self.assertIn("Connection timeout", str(message))
        self.mock_client.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
