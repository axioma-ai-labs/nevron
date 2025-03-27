import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from loguru import logger

from src.tools.slack import SlackTool


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger for testing."""
    mock_debug = Mock()
    mock_error = Mock()
    monkeypatch.setattr(logger, "debug", mock_debug)
    monkeypatch.setattr(logger, "error", mock_error)
    return mock_debug, mock_error


@pytest.fixture
async def mock_slack():
    """Fixture to create a SlackIntegration instance with mocked clients"""
    with (
        patch("slack_sdk.web.async_client.AsyncWebClient"),
        patch("slack_sdk.socket_mode.aiohttp.SocketModeClient"),
    ):
        # Create instance with dummy tokens
        slack = SlackTool(bot_token="xoxb-dummy-bot-token", app_token="xapp-dummy-app-token")

        # Setup mock web client
        slack.web_client = AsyncMock()
        # Setup mock socket client
        slack.socket_client = Mock()
        slack.socket_client.connect = AsyncMock()
        slack.socket_client.disconnect = AsyncMock()

        yield slack


@pytest.mark.asyncio
async def test_initialization(mock_slack, mock_logger):
    """Test successful client initialization"""
    mock_debug, mock_error = mock_logger
    mock_slack.web_client.auth_test = AsyncMock(return_value={"ok": True})

    await mock_slack.connect()
    mock_slack.web_client.auth_test.assert_called_once()
    mock_error.assert_not_called()


@pytest.mark.asyncio
async def test_send_message(mock_slack, mock_logger):
    """Test sending messages to channels"""
    mock_debug, mock_error = mock_logger
    mock_slack.web_client.chat_postMessage = AsyncMock(
        return_value={"ok": True, "ts": "1234567890.123456"}
    )

    await mock_slack.send_message("C123456", "Test message")

    mock_slack.web_client.chat_postMessage.assert_called_once_with(
        channel="C123456", text="Test message"
    )
    mock_error.assert_not_called()


@pytest.mark.asyncio
async def test_message_handling(mock_slack, mock_logger):
    """Test receiving and processing messages"""
    mock_debug, mock_error = mock_logger

    # Create a mock callback
    callback_mock = AsyncMock()
    await mock_slack.listen_for_messages(callback_mock)

    # Simulate receiving a message
    test_event = {
        "type": "message",
        "text": "Hello, bot!",
        "user": "U123456",
        "channel": "C123456",
        "ts": "1234567890.123456",
    }

    # Create mock request
    mock_request = Mock()
    mock_request.type = "events_api"
    mock_request.envelope_id = "test-envelope"
    mock_request.payload = {"event": test_event}

    # Create mock client
    mock_client = Mock()
    mock_client.send_socket_mode_response = AsyncMock()

    # Process the mock message
    await mock_slack._handle_socket_message(mock_client, mock_request)

    # Verify callback was called with the event
    callback_mock.assert_called_once_with(test_event)
    mock_error.assert_not_called()


def test_add_to_history(mock_slack, mock_logger):
    """Test adding messages to history"""
    mock_debug, mock_error = mock_logger
    test_message = {
        "text": "Test message",
        "user": "U123456",
        "channel": "C123456",
        "ts": "1234567890.123456",
    }

    mock_slack.add_to_history(test_message)

    assert len(mock_slack.message_history) == 1
    assert mock_slack.message_history[0]["text"] == "Test message"
    assert mock_slack.message_history[0]["user"] == "U123456"
    mock_error.assert_not_called()


def test_get_user_history(mock_slack, mock_logger):
    """Test retrieving user message history"""
    mock_debug, mock_error = mock_logger
    messages = [
        {"text": "User1 message", "user": "U111", "channel": "C123", "ts": "1234567890.123456"},
        {"text": "User2 message", "user": "U222", "channel": "C123", "ts": "1234567890.123457"},
    ]

    for msg in messages:
        mock_slack.add_to_history(msg)

    user_history = mock_slack.get_user_message_history("U111")
    assert len(user_history) == 1
    assert user_history[0]["text"] == "User1 message"
    mock_error.assert_not_called()


def test_get_channel_history(mock_slack, mock_logger):
    """Test retrieving channel message history"""
    mock_debug, mock_error = mock_logger
    messages = [
        {"text": "Channel1 message", "user": "U111", "channel": "C111", "ts": "1234567890.123456"},
        {"text": "Channel2 message", "user": "U111", "channel": "C222", "ts": "1234567890.123457"},
    ]

    for msg in messages:
        mock_slack.add_to_history(msg)

    channel_history = mock_slack.get_channel_history("C111")
    assert len(channel_history) == 1
    assert channel_history[0]["text"] == "Channel1 message"
    mock_error.assert_not_called()


@pytest.mark.asyncio
async def test_close(mock_slack, mock_logger):
    """Test closing the Slack connection"""
    mock_debug, mock_error = mock_logger

    await mock_slack.close()

    mock_slack.socket_client.disconnect.assert_called_once()
    mock_error.assert_not_called()


@pytest.mark.asyncio
async def test_close_cleanup(mock_slack, mock_logger):
    """Test proper cleanup during Slack connection closure"""
    mock_debug, mock_error = mock_logger

    # Setup mock session for web client cleanup
    mock_session = AsyncMock()
    mock_slack.web_client.session = mock_session
    mock_session.close = AsyncMock()

    # Call close
    await mock_slack.close()

    # Verify both clients are properly cleaned up
    mock_slack.socket_client.disconnect.assert_called_once()
    mock_session.close.assert_called_once()
    mock_error.assert_not_called()
