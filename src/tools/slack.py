import asyncio
from datetime import datetime
from typing import Callable, Dict, List, Optional

from slack_sdk.errors import SlackApiError
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.async_listeners import AsyncSocketModeRequestListener
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.web.async_client import AsyncWebClient

from src.core.config import settings


class SlackTool:
    def __init__(
        self, bot_token: str = settings.SLACK_BOT_TOKEN, app_token: str = settings.SLACK_APP_TOKEN
    ):
        """Initialize the Slack integration with both bot and app tokens.

        Args:
            bot_token: The bot user OAuth token, defaults to settings.SLACK_BOT_TOKEN
            app_token: The app-level token starting with 'xapp-', defaults to settings.SLACK_APP_TOKEN
        """
        # Initialize with default SSL context instead of bool
        ssl_context = None

        self.web_client = AsyncWebClient(token=bot_token, ssl=ssl_context)
        self.socket_client = SocketModeClient(app_token=app_token, web_client=self.web_client)
        self.message_callback: Optional[Callable] = None

        # Message storage (Bot's memory)
        self.message_history: List[Dict] = []
        self.max_history_size = 1000  # Adjust this value as needed

    async def connect(self) -> None:
        """Establish connection to Slack"""
        try:
            # Test the connection
            await self.web_client.auth_test()
            print("Successfully connected to Slack!")
        except SlackApiError as e:
            print(f"Error connecting to Slack: {e.response['error']}")
            raise

    async def listen_for_messages(self, callback: Callable) -> None:
        """Set up message listening with Socket Mode.

        Args:
            callback: Function to call when messages are received
        """
        self.message_callback = callback

        # Type-cast the handler to match expected type

        handler: AsyncSocketModeRequestListener = self._handle_socket_message  # type: ignore
        self.socket_client.socket_mode_request_listeners.append(handler)

        # Start the Socket Mode client
        await self.socket_client.connect()
        print("Listening for messages...")

    async def _handle_socket_message(self, client: SocketModeClient, req: SocketModeRequest):
        """Internal handler for socket mode messages"""
        print(f"Received request type: {req.type}")  # Debug print

        if req.type == "events_api":
            # Acknowledge the request
            response = SocketModeResponse(envelope_id=req.envelope_id)
            await client.send_socket_mode_response(response)

            # Process the event
            event = req.payload["event"]
            print(f"Received event type: {event['type']}")  # Debug print

            if event["type"] == "message" and "subtype" not in event:
                print(f"Processing message: {event['text']}")  # Debug print
                # Store message in history if it's not from a bot
                if "bot_id" not in event:
                    self.add_to_history(event)

                # Call the callback if set
                if self.message_callback:
                    await self.message_callback(event)

    async def send_message(
        self, channel_id: str, message: str, thread_ts: Optional[str] = None
    ) -> None:
        """Send a message to a Slack channel or thread.

        Args:
            channel_id: The channel ID to send the message to
            message: The message text to send
            thread_ts: Optional thread timestamp to reply in a thread
        """
        try:
            if thread_ts:
                await self.web_client.chat_postMessage(
                    channel=channel_id, text=message, thread_ts=thread_ts
                )
            else:
                await self.web_client.chat_postMessage(channel=channel_id, text=message)
        except SlackApiError as e:
            print(f"Error sending message: {e.response['error']}")
            raise

    def add_to_history(self, message_event: Dict) -> None:
        """Store a message in the bot's memory.

        Args:
            message_event: The Slack message event to store
        """
        # Create a message structure record
        message_record = {
            "text": message_event["text"],
            "user": message_event["user"],
            "channel": message_event["channel"],
            "timestamp": message_event["ts"],
            "thread_ts": message_event.get("thread_ts"),
            "time": datetime.now().isoformat(),
        }

        # Add to history
        self.message_history.append(message_record)

        # Maintain size
        if len(self.message_history) > self.max_history_size:
            self.message_history.pop(0)  # Remove oldest message

    def get_user_message_history(self, user_id: str) -> List[Dict]:
        """Get all messages from a specific user.

        Args:
            user_id: The Slack user ID to filter messages for

        Returns:
            List of message records from the specified user
        """
        return [msg for msg in self.message_history if msg["user"] == user_id]

    def get_channel_history(self, channel_id: str) -> List[Dict]:
        """Get all messages from a specific channel.

        Args:
            channel_id: The Slack channel ID to filter messages for

        Returns:
            List of message records from the specified channel
        """
        return [msg for msg in self.message_history if msg["channel"] == channel_id]

    async def close(self):
        """Close the Slack connection and cleanup resources"""
        # First disconnect the socket client
        if hasattr(self, "socket_client") and self.socket_client:
            await self.socket_client.disconnect()
            # Cancel any pending tasks
            for task in asyncio.all_tasks():
                if "process_messages" in str(task):
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        # Then close the web client session
        if hasattr(self, "web_client") and self.web_client:
            if hasattr(self.web_client, "session") and self.web_client.session:
                await self.web_client.session.close()
