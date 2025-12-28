"""Tests for HumanHandoff module."""

import asyncio

import pytest

from src.metacognition.human_handoff import (
    HandoffChannel,
    HumanHandoff,
    HumanRequest,
    HumanResponse,
    RequestUrgency,
)


class TestHumanRequest:
    """Tests for HumanRequest dataclass."""

    def test_request_creation(self):
        """Test creating a request."""
        request = HumanRequest(
            id="req-001",
            question="What should I do?",
            context={"goal": "test"},
            urgency=RequestUrgency.HIGH,
            options=["Option A", "Option B"],
        )

        assert request.id == "req-001"
        assert request.urgency == RequestUrgency.HIGH
        assert len(request.options) == 2

    def test_to_dict(self):
        """Test converting to dict."""
        request = HumanRequest(
            id="req-002",
            question="Test question",
            context={"key": "value"},
        )

        result = request.to_dict()

        assert result["id"] == "req-002"
        assert result["question"] == "Test question"
        assert "created_at" in result

    def test_format_message(self):
        """Test formatting as message."""
        request = HumanRequest(
            id="req-003",
            question="What option should I choose?",
            context={"task": "decision"},
            urgency=RequestUrgency.CRITICAL,
            options=["A", "B", "C"],
        )

        message = request.format_message()

        assert "CRITICAL" in message
        assert "What option should I choose?" in message
        assert "[1] A" in message
        assert "task: decision" in message


class TestHumanResponse:
    """Tests for HumanResponse dataclass."""

    def test_response_creation(self):
        """Test creating a response."""
        response = HumanResponse(
            request_id="req-001",
            response="Go with option A",
            selected_option=1,
            responder="admin",
        )

        assert response.request_id == "req-001"
        assert response.selected_option == 1
        assert response.responder == "admin"

    def test_to_dict(self):
        """Test converting to dict."""
        response = HumanResponse(
            request_id="req-001",
            response="Test response",
        )

        result = response.to_dict()

        assert result["request_id"] == "req-001"
        assert "responded_at" in result


class TestHumanHandoff:
    """Tests for HumanHandoff class."""

    def test_handoff_creation(self):
        """Test creating handoff handler."""
        handoff = HumanHandoff()
        assert handoff is not None

    def test_handoff_with_channel(self):
        """Test creating with specific channel."""
        handoff = HumanHandoff(default_channel=HandoffChannel.TELEGRAM)
        assert handoff._default_channel == HandoffChannel.TELEGRAM

    def test_register_channel_handler(self):
        """Test registering channel handler."""
        handoff = HumanHandoff()

        async def mock_handler(message: str) -> None:
            pass

        handoff.register_channel_handler(HandoffChannel.TELEGRAM, mock_handler)

        assert HandoffChannel.TELEGRAM in handoff._channel_handlers

    @pytest.mark.asyncio
    async def test_request_help_timeout(self):
        """Test request help with timeout."""
        handoff = HumanHandoff(default_timeout=0.1)  # Very short timeout

        result = await handoff.request_help(
            question="Test question",
            context={"test": True},
            timeout=0.1,
        )

        # Should timeout and return None
        assert result is None

    def test_provide_response(self):
        """Test providing response to request."""
        handoff = HumanHandoff()

        # Create a pending request
        import uuid

        request_id = str(uuid.uuid4())[:8]
        request = HumanRequest(
            id=request_id,
            question="Test",
            context={},
        )
        handoff._pending_requests[request_id] = request
        handoff._callbacks[request_id] = asyncio.Event()

        # Provide response
        result = handoff.provide_response(
            request_id=request_id,
            response="Test response",
            selected_option=1,
        )

        assert result is True
        assert request_id in handoff._responses

    def test_provide_response_unknown_request(self):
        """Test providing response to unknown request."""
        handoff = HumanHandoff()

        result = handoff.provide_response(
            request_id="unknown",
            response="Test",
        )

        assert result is False

    def test_get_pending_requests(self):
        """Test getting pending requests."""
        handoff = HumanHandoff()

        request = HumanRequest(
            id="test",
            question="Test",
            context={},
        )
        handoff._pending_requests["test"] = request

        pending = handoff.get_pending_requests()

        assert len(pending) == 1
        assert pending[0].id == "test"

    def test_cancel_request(self):
        """Test cancelling request."""
        handoff = HumanHandoff()

        request = HumanRequest(
            id="test",
            question="Test",
            context={},
        )
        handoff._pending_requests["test"] = request
        handoff._callbacks["test"] = asyncio.Event()

        result = handoff.cancel_request("test")

        assert result is True
        assert "test" not in handoff._pending_requests

    def test_cancel_unknown_request(self):
        """Test cancelling unknown request."""
        handoff = HumanHandoff()
        result = handoff.cancel_request("unknown")
        assert result is False

    def test_clear(self):
        """Test clearing handoff."""
        handoff = HumanHandoff()

        request = HumanRequest(
            id="test",
            question="Test",
            context={},
        )
        handoff._pending_requests["test"] = request
        handoff._callbacks["test"] = asyncio.Event()

        handoff.clear()

        assert len(handoff._pending_requests) == 0

    def test_get_statistics(self):
        """Test getting statistics."""
        handoff = HumanHandoff()

        stats = handoff.get_statistics()

        assert stats["pending_requests"] == 0
        assert "default_channel" in stats

    @pytest.mark.asyncio
    async def test_report_uncertainty(self):
        """Test reporting uncertainty."""
        handoff = HumanHandoff()

        # Should not raise any errors
        await handoff.report_uncertainty(
            what_im_doing="Testing something",
            what_im_unsure_about="The outcome",
            options_im_considering=["Option A", "Option B"],
        )

    @pytest.mark.asyncio
    async def test_send_status_update(self):
        """Test sending status update."""
        handoff = HumanHandoff()

        # Should not raise any errors
        await handoff.send_status_update(
            status="Task completed",
            details={"result": "success"},
        )


class TestHumanHandoffIntegration:
    """Integration tests for HumanHandoff."""

    @pytest.mark.asyncio
    async def test_full_request_response_flow(self):
        """Test full request-response flow."""
        handoff = HumanHandoff()

        # Start request in background
        async def make_request():
            return await handoff.request_help(
                question="What should I do?",
                context={"task": "test"},
                options=["A", "B"],
                timeout=1.0,
            )

        # Start request task
        request_task = asyncio.create_task(make_request())

        # Wait a bit for request to be created
        await asyncio.sleep(0.1)

        # Find the request and respond
        pending = handoff.get_pending_requests()
        if pending:
            handoff.provide_response(
                request_id=pending[0].id,
                response="Choose A",
                selected_option=1,
            )

        # Get result
        result = await request_task

        if result:
            assert result.response == "Choose A"
            assert result.selected_option == 1

    @pytest.mark.asyncio
    async def test_custom_channel_handler(self):
        """Test with custom channel handler."""
        handoff = HumanHandoff()
        messages_sent = []

        async def custom_handler(message: str) -> None:
            messages_sent.append(message)

        handoff.register_channel_handler(HandoffChannel.CALLBACK, custom_handler)

        request = HumanRequest(
            id="test",
            question="Test",
            context={},
            channel=HandoffChannel.CALLBACK,
        )

        await handoff._send_request(request)

        assert len(messages_sent) == 1
