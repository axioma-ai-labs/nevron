from unittest.mock import MagicMock, patch

import pytest
from loguru import logger

from src.main import async_main, main


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger for testing."""
    # arrange:
    mock_info = MagicMock()
    mock_critical = MagicMock()
    monkeypatch.setattr(logger, "info", mock_info)
    monkeypatch.setattr(logger, "critical", mock_critical)
    monkeypatch.setattr(logger, "add", MagicMock())  # Mock logger.add
    return mock_info, mock_critical


@pytest.fixture
def mock_agent():
    """Mock Agent class for testing."""
    # arrange:
    with patch("src.main.Agent") as mock:
        agent_instance = MagicMock()
        mock.return_value = agent_instance
        yield agent_instance


@pytest.mark.asyncio
async def test_async_main_success(mock_logger, mock_agent):
    """Test successful execution of async_main."""
    # arrange:
    mock_info, mock_critical = mock_logger

    # act:
    await async_main()

    # assert:
    mock_info.assert_any_call("Starting the agent runtime...")
    mock_info.assert_any_call("Agent runtime has stopped.")
    mock_agent.start_runtime_loop.assert_called_once()


@pytest.mark.asyncio
async def test_async_main_error(mock_logger, mock_agent):
    """Test async_main with runtime error."""
    # arrange:
    mock_info, mock_critical = mock_logger
    mock_agent.start_runtime_loop.side_effect = Exception("Test error")

    # act:
    await async_main()

    # assert:
    mock_info.assert_any_call("Starting the agent runtime...")
    mock_info.assert_any_call("Agent runtime has stopped.")
    mock_critical.assert_called_once_with("Fatal error in the runtime: Test error")


def test_main_success(mock_logger):
    """Test successful execution of main."""
    # arrange:
    mock_info, mock_critical = mock_logger

    with patch("asyncio.run") as mock_run:
        # act:
        main()

        # assert:
        mock_run.assert_called_once()
        mock_critical.assert_not_called()


def test_main_keyboard_interrupt(mock_logger):
    """Test main with KeyboardInterrupt."""
    # arrange:
    mock_info, mock_critical = mock_logger

    with patch("asyncio.run", side_effect=KeyboardInterrupt):
        # act:
        main()

        # assert:
        mock_info.assert_called_with(
            "Agent runtime interrupted by user. Shutting down gracefully..."
        )
        mock_critical.assert_not_called()


def test_main_error(mock_logger):
    """Test main with runtime error."""
    # arrange:
    mock_info, mock_critical = mock_logger

    with patch("asyncio.run", side_effect=Exception("Test error")):
        # act:
        main()

        # assert:
        mock_critical.assert_called_with("Fatal error in the main runtime: Test error")
