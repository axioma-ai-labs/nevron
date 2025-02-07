from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.core.exceptions import DiscordError, LensError, SlackError, WhatsAppError
from src.execution.base import ActionExecutor
from src.tools.discord import DiscordTool
from src.tools.lens_protocol import LensProtocolTool
from src.tools.slack import SlackTool
from src.tools.tg import TelegramTool
from src.tools.twitter import TwitterTool
from src.tools.whatsapp import WhatsAppTool


class PostTweetExecutor(ActionExecutor):
    """Executor for posting tweets."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> TwitterTool:
        """Initialize Discord tool client."""
        return TwitterTool()

    def get_required_context(self) -> List[str]:
        return ["tweet_text"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not self.validate_context(context):
            return False, "Missing required arguments in context"
        tweet_text = context.get("tweet_text")
        twitter_thread = {"tweet1": tweet_text}
        try:
            if tweet_text:
                await self.client.post_thread(twitter_thread)
                return True, f"Tweet posted: {tweet_text[:50]}..."
            return False, "No tweet text provided"
        except Exception as e:
            return False, f"Failed to post tweet: {str(e)}"


class ListenDiscordMessagesExecutor(ActionExecutor):
    """Executor for listening to Discord messages."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> DiscordTool:
        """Initialize Discord tool client."""
        return DiscordTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["channel_id", "message_handler"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Discord message listening."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            channel_id = context.get("channel_id")
            message_handler = context.get("message_handler")

            logger.info(f"Starting to listen for Discord messages in channel {channel_id}")
            await self.client.listen_to_messages(channel_id, message_handler)

            return True, "Successfully started listening for Discord messages"

        except DiscordError as e:
            error_msg = f"Failed to listen for Discord messages: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while listening for Discord messages: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class SendDiscordMessageExecutor(ActionExecutor):
    """Executor for sending Discord messages."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> DiscordTool:
        """Initialize Discord tool client."""
        return DiscordTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["channel_id", "message_content"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Discord message sending."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            channel_id = context.get("channel_id")
            message_content = context.get("message_content")

            logger.info(f"Sending Discord message to channel {channel_id}")
            message_id = await self.client.send_message(channel_id, message_content)

            if message_id:
                return True, f"Successfully sent Discord message with ID: {message_id}"
            return False, "Failed to send Discord message: No message ID returned"

        except DiscordError as e:
            error_msg = f"Failed to send Discord message: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while sending Discord message: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class SendTelegramMessageExecutor(ActionExecutor):
    """Executor for sending Telegram messages."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> TelegramTool:
        """Initialize Discord tool client."""
        return TelegramTool()

    def get_required_context(self) -> List[str]:
        return ["message_text"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        message = context.get("message_text")
        if not message:
            return False, "No message text provided"
        try:
            await self.client.post_summary(message)
            return True, f"Telegram message sent: {message[:50]}..."
        except Exception as e:
            return False, f"Failed to send Telegram message: {str(e)}"


class PostLensExecutor(ActionExecutor):
    """Executor for posting content to Lens Protocol."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> LensProtocolTool:
        """Initialize Lens Protocol tool client."""
        return LensProtocolTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["content", "profile_id"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Lens content posting."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            content = context.get("content")
            profile_id = context.get("profile_id")  # Optional, will use default if not provided

            logger.info("Posting content to Lens Protocol")
            result = self.client.publish_content(content, profile_id)

            if result:
                return True, f"Successfully posted to Lens with ID: {result['id']}"
            return False, "Failed to post to Lens: No result returned"

        except LensError as e:
            error_msg = f"Failed to post to Lens: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while posting to Lens: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class FetchLensExecutor(ActionExecutor):
    """Executor for fetching content from Lens Protocol."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> LensProtocolTool:
        """Initialize Lens Protocol tool client."""
        return LensProtocolTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["query_params"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Lens content fetching."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            query_params = context.get("query_params")

            logger.info("Fetching content from Lens Protocol")
            results = self.client.fetch_content(query_params)

            if results:
                return True, f"Successfully fetched {len(results)} items from Lens"
            return False, "No content found matching the query"

        except LensError as e:
            error_msg = f"Failed to fetch from Lens: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while fetching from Lens: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class ListenWhatsAppMessagesExecutor(ActionExecutor):
    """Executor for listening to WhatsApp messages."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> WhatsAppTool:
        """Initialize WhatsApp tool client."""
        return WhatsAppTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["message_handler"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute WhatsApp message listening."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            message_handler = context.get("message_handler")

            logger.info("Starting to listen for WhatsApp messages")
            await self.client.listen_to_messages(message_handler)

            return True, "Successfully started listening for WhatsApp messages"

        except WhatsAppError as e:
            error_msg = f"Failed to listen for WhatsApp messages: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while listening for WhatsApp messages: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class SendWhatsAppMessageExecutor(ActionExecutor):
    """Executor for sending WhatsApp messages."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> WhatsAppTool:
        """Initialize WhatsApp tool client."""
        return WhatsAppTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["recipient_id", "message_content"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute WhatsApp message sending."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            recipient_id = context.get("recipient_id")
            message_content = context.get("message_content")

            logger.info(f"Sending WhatsApp message to {recipient_id}")
            message_id = await self.client.send_message(recipient_id, message_content)

            if message_id:
                return True, f"Successfully sent WhatsApp message with ID: {message_id}"
            return False, "Failed to send WhatsApp message: No message ID returned"

        except WhatsAppError as e:
            error_msg = f"Failed to send WhatsApp message: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while sending WhatsApp message: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class ListenSlackMessagesExecutor(ActionExecutor):
    """Executor for listening to Slack messages."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> SlackTool:
        """Initialize Slack tool client."""
        return SlackTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["message_handler"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Slack message listening."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            message_handler = context.get("message_handler")

            logger.info("Starting to listen for Slack messages")
            await self.client.listen_for_messages(message_handler)

            return True, "Successfully started listening for Slack messages"

        except SlackError as e:
            error_msg = f"Failed to listen for Slack messages: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while listening for Slack messages: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class SendSlackMessageExecutor(ActionExecutor):
    """Executor for sending Slack messages."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> SlackTool:
        """Initialize Slack tool client."""
        return SlackTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["channel_id", "message_content", "thread_ts"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Slack message sending."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            channel_id = context.get("channel_id")
            message_content = context.get("message_content")
            thread_ts = context.get("thread_ts")  # Optional thread timestamp

            logger.info(f"Sending Slack message to channel {channel_id}")
            await self.client.send_message(channel_id, message_content, thread_ts)

            return True, "Successfully sent Slack message"

        except SlackError as e:
            error_msg = f"Failed to send Slack message: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while sending Slack message: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
