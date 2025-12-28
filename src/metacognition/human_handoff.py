"""Human Handoff - Handle requests for human assistance.

Provides mechanisms to request help from humans when the agent
is uncertain or stuck.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class HandoffChannel(Enum):
    """Channels for human communication."""

    TELEGRAM = "telegram"
    SLACK = "slack"
    DISCORD = "discord"
    EMAIL = "email"
    CONSOLE = "console"
    CALLBACK = "callback"


class RequestUrgency(Enum):
    """Urgency levels for human requests."""

    LOW = "low"  # Can wait indefinitely
    MEDIUM = "medium"  # Should respond within hours
    HIGH = "high"  # Should respond within minutes
    CRITICAL = "critical"  # Immediate response needed


@dataclass
class HumanRequest:
    """Represents a request for human assistance."""

    id: str
    question: str
    context: Dict[str, Any]
    urgency: RequestUrgency = RequestUrgency.MEDIUM
    options: List[str] = field(default_factory=list)
    timeout_seconds: float = 3600.0  # 1 hour default
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    channel: HandoffChannel = HandoffChannel.CONSOLE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "question": self.question,
            "context": self.context,
            "urgency": self.urgency.value,
            "options": self.options,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat(),
            "channel": self.channel.value,
        }

    def format_message(self) -> str:
        """Format as human-readable message."""
        msg = f"[{self.urgency.value.upper()}] Help Request\n\n"
        msg += f"Question: {self.question}\n"

        if self.options:
            msg += "\nOptions:\n"
            for i, opt in enumerate(self.options, 1):
                msg += f"  [{i}] {opt}\n"

        if self.context:
            msg += "\nContext:\n"
            for key, value in self.context.items():
                msg += f"  - {key}: {value}\n"

        return msg


@dataclass
class HumanResponse:
    """Represents a response from a human."""

    request_id: str
    response: str
    selected_option: Optional[int] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    responded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    responder: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "response": self.response,
            "selected_option": self.selected_option,
            "additional_context": self.additional_context,
            "responded_at": self.responded_at.isoformat(),
            "responder": self.responder,
        }


class HumanHandoff:
    """Handle requests for human assistance.

    Provides async mechanisms to:
    - Send help requests via configured channels
    - Wait for responses with timeout
    - Handle response callbacks
    - Track pending requests
    """

    def __init__(
        self,
        default_channel: HandoffChannel = HandoffChannel.CONSOLE,
        default_timeout: float = 3600.0,
    ):
        """Initialize human handoff handler.

        Args:
            default_channel: Default communication channel
            default_timeout: Default timeout in seconds
        """
        self._default_channel = default_channel
        self._default_timeout = default_timeout

        # Pending requests
        self._pending_requests: Dict[str, HumanRequest] = {}

        # Response callbacks
        self._callbacks: Dict[str, asyncio.Event] = {}
        self._responses: Dict[str, HumanResponse] = {}

        # Channel handlers
        self._channel_handlers: Dict[HandoffChannel, Callable] = {}

        # Request history
        self._request_history: List[HumanRequest] = []
        self._response_history: List[HumanResponse] = []

        logger.debug(f"HumanHandoff initialized with default channel: {default_channel.value}")

    def register_channel_handler(
        self,
        channel: HandoffChannel,
        handler: Callable,
    ) -> None:
        """Register a handler for a communication channel.

        Args:
            channel: The channel to handle
            handler: Async function to send messages
        """
        self._channel_handlers[channel] = handler
        logger.debug(f"Registered handler for channel: {channel.value}")

    async def request_help(
        self,
        question: str,
        context: Dict[str, Any],
        urgency: RequestUrgency = RequestUrgency.MEDIUM,
        options: Optional[List[str]] = None,
        timeout: Optional[float] = None,
        channel: Optional[HandoffChannel] = None,
    ) -> Optional[HumanResponse]:
        """Send request for human help and wait for response.

        Args:
            question: Question to ask
            context: Context information
            urgency: Request urgency
            options: Optional list of choices
            timeout: Timeout in seconds (None = default)
            channel: Communication channel (None = default)

        Returns:
            HumanResponse or None if timed out
        """
        import uuid

        request_id = str(uuid.uuid4())[:8]
        channel = channel or self._default_channel
        timeout = timeout or self._default_timeout

        # Create request
        request = HumanRequest(
            id=request_id,
            question=question,
            context=context,
            urgency=urgency,
            options=options or [],
            timeout_seconds=timeout,
            channel=channel,
        )

        # Store request
        self._pending_requests[request_id] = request
        self._request_history.append(request)

        # Create event for response
        self._callbacks[request_id] = asyncio.Event()

        # Send via channel
        await self._send_request(request)

        # Wait for response
        try:
            await asyncio.wait_for(
                self._callbacks[request_id].wait(),
                timeout=timeout,
            )

            response = self._responses.get(request_id)
            if response:
                self._response_history.append(response)
                return response

        except asyncio.TimeoutError:
            logger.warning(f"Human response timed out for request {request_id}")

        finally:
            # Cleanup
            self._pending_requests.pop(request_id, None)
            self._callbacks.pop(request_id, None)

        return None

    async def _send_request(self, request: HumanRequest) -> bool:
        """Send request via configured channel.

        Args:
            request: Request to send

        Returns:
            True if sent successfully
        """
        channel = request.channel
        handler = self._channel_handlers.get(channel)

        if handler:
            try:
                await handler(request.format_message())
                logger.info(f"Sent help request via {channel.value}: {request.id}")
                return True
            except Exception as e:
                logger.error(f"Failed to send request via {channel.value}: {e}")
                return False

        # Fallback to console
        if channel == HandoffChannel.CONSOLE or not handler:
            logger.info(f"Help request ({request.id}):\n{request.format_message()}")
            return True

        return False

    def provide_response(
        self,
        request_id: str,
        response: str,
        selected_option: Optional[int] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        responder: Optional[str] = None,
    ) -> bool:
        """Provide a response to a pending request.

        Args:
            request_id: ID of the request
            response: Response text
            selected_option: Index of selected option (1-based)
            additional_context: Additional context
            responder: Identifier of the responder

        Returns:
            True if response was accepted
        """
        if request_id not in self._pending_requests:
            logger.warning(f"No pending request found: {request_id}")
            return False

        # Create response
        human_response = HumanResponse(
            request_id=request_id,
            response=response,
            selected_option=selected_option,
            additional_context=additional_context or {},
            responder=responder,
        )

        # Store and signal
        self._responses[request_id] = human_response

        event = self._callbacks.get(request_id)
        if event:
            event.set()
            logger.info(f"Human response received for request {request_id}")
            return True

        return False

    async def report_uncertainty(
        self,
        what_im_doing: str,
        what_im_unsure_about: str,
        options_im_considering: List[str],
        channel: Optional[HandoffChannel] = None,
    ) -> None:
        """Proactively inform human of uncertainty.

        Args:
            what_im_doing: Current task description
            what_im_unsure_about: What is unclear
            options_im_considering: Possible approaches
            channel: Communication channel
        """
        channel = channel or self._default_channel

        message = (
            f"[UNCERTAINTY REPORT]\n\n"
            f"I'm working on: {what_im_doing}\n\n"
            f"I'm unsure about: {what_im_unsure_about}\n\n"
            f"Options I'm considering:\n"
        )

        for i, option in enumerate(options_im_considering, 1):
            message += f"  [{i}] {option}\n"

        handler = self._channel_handlers.get(channel)
        if handler:
            try:
                await handler(message)
                logger.info(f"Sent uncertainty report via {channel.value}")
            except Exception as e:
                logger.error(f"Failed to send uncertainty report: {e}")
        else:
            logger.info(f"Uncertainty report:\n{message}")

    async def send_status_update(
        self,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        channel: Optional[HandoffChannel] = None,
    ) -> None:
        """Send a status update to the human.

        Args:
            status: Status message
            details: Optional details
            channel: Communication channel
        """
        channel = channel or self._default_channel

        message = f"[STATUS UPDATE] {status}"
        if details:
            message += "\n\nDetails:\n"
            for key, value in details.items():
                message += f"  - {key}: {value}\n"

        handler = self._channel_handlers.get(channel)
        if handler:
            try:
                await handler(message)
            except Exception as e:
                logger.error(f"Failed to send status update: {e}")
        else:
            logger.info(message)

    def get_pending_requests(self) -> List[HumanRequest]:
        """Get all pending requests.

        Returns:
            List of pending HumanRequest
        """
        return list(self._pending_requests.values())

    def cancel_request(self, request_id: str) -> bool:
        """Cancel a pending request.

        Args:
            request_id: Request to cancel

        Returns:
            True if cancelled
        """
        if request_id in self._pending_requests:
            del self._pending_requests[request_id]

            event = self._callbacks.get(request_id)
            if event:
                event.set()  # Unblock any waiters
                del self._callbacks[request_id]

            logger.info(f"Cancelled request: {request_id}")
            return True

        return False

    def clear(self) -> None:
        """Clear all pending requests."""
        for event in self._callbacks.values():
            event.set()  # Unblock all waiters

        self._pending_requests.clear()
        self._callbacks.clear()
        self._responses.clear()
        logger.debug("HumanHandoff cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get handoff statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "pending_requests": len(self._pending_requests),
            "total_requests": len(self._request_history),
            "total_responses": len(self._response_history),
            "registered_channels": list(self._channel_handlers.keys()),
            "default_channel": self._default_channel.value,
        }
