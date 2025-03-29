from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.memory.memory_module import MemoryModule
from src.workflows.analyze_signal import analyze_signal


@pytest.fixture
def mock_memory():
    memory = AsyncMock(spec=MemoryModule)
    memory.search.return_value = []
    return memory


@pytest.mark.asyncio
async def test_analyze_signal_new_signal(mock_memory):
    # Mock dependencies
    mock_signal = {"status": "new_signal", "content": "Test signal content"}

    with (
        patch("src.workflows.analyze_signal.CoinstatsTool") as mock_coinstats,
        patch("src.workflows.analyze_signal.TwitterTool") as mock_twitter,
        patch("src.workflows.analyze_signal.LLM") as mock_llm,
    ):
        # Setup mocks with proper async handling
        mock_coinstats_instance = mock_coinstats.return_value
        mock_coinstats_instance.fetch_signal = AsyncMock(return_value=mock_signal)

        mock_twitter_instance = mock_twitter.return_value
        mock_twitter_instance.post_thread = AsyncMock(return_value=[12345])

        mock_llm_instance = mock_llm.return_value
        mock_llm_instance.generate_response = AsyncMock(return_value="Test analysis")

        # Execute
        result = await analyze_signal(memory=mock_memory)

        # Assertions
        assert result == "12345"
        mock_memory.store.assert_called_once()
        mock_twitter_instance.post_thread.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_signal_already_processed(mock_memory):
    # Mock dependencies
    mock_signal = {"status": "new_signal", "content": "Test signal content"}
    mock_memory.search.return_value = [{"event": "Test signal content"}]

    with patch("src.workflows.analyze_signal.CoinstatsTool") as mock_coinstats:
        # Setup mocks
        mock_coinstats.return_value.fetch_signal.return_value = mock_signal

        # Execute
        result = await analyze_signal(memory=mock_memory)

        # Assertions
        assert result is None
        mock_memory.store.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_signal_no_data(mock_memory):
    # Mock dependencies
    mock_signal = {"status": "no_data"}

    with patch("src.workflows.analyze_signal.CoinstatsTool") as mock_coinstats:
        # Setup mocks
        mock_coinstats.return_value.fetch_signal.return_value = mock_signal

        # Execute
        result = await analyze_signal(memory=mock_memory)

        # Assertions
        assert result is None
        mock_memory.store.assert_not_called()


@pytest.mark.asyncio
async def test_analyze_signal_with_link(mock_memory):
    # Mock dependencies
    mock_signal = {"status": "new_signal", "content": "Test link content"}

    with (
        patch("src.workflows.analyze_signal.LinkParserTool") as mock_link_parser,
        patch("src.workflows.analyze_signal.TwitterTool") as mock_twitter,
        patch("src.workflows.analyze_signal.LLM") as mock_llm,
    ):
        # Setup mocks with proper async handling
        mock_link_parser_instance = mock_link_parser.return_value
        mock_link_parser_instance.fetch_signal_link = MagicMock(return_value=mock_signal)

        mock_twitter_instance = mock_twitter.return_value
        mock_twitter_instance.post_thread = AsyncMock(return_value=[12345])

        mock_llm_instance = mock_llm.return_value
        mock_llm_instance.generate_response = AsyncMock(return_value="Test analysis")

        # Mock memory search to return empty list (indicating new signal)
        mock_memory.search.return_value = []

        # Execute
        result = await analyze_signal(memory=mock_memory, link="http://test.com")

        # Assertions
        assert result == "12345"
        mock_memory.store.assert_called_once()
        mock_twitter_instance.post_thread.assert_called_once()
        mock_link_parser_instance.fetch_signal_link.assert_called_once_with("http://test.com")
