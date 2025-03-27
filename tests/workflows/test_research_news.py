from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.memory.memory_module import MemoryModule
from src.workflows.research_news import analyze_news_workflow


@pytest.fixture
def mock_memory_module():
    memory = AsyncMock(spec=MemoryModule)
    memory.store = AsyncMock()
    return memory


@pytest.fixture
def mock_link_parser():
    with patch("src.workflows.research_news.LinkParserTool") as mock:
        link_parser_instance = MagicMock()
        link_parser_instance.search_links.return_value = [
            {
                "title": "Test Crypto News",
                "description": "This is a test description",
                "content": "This is test content for crypto news",
            }
        ]
        mock.return_value = link_parser_instance
        yield mock


@pytest.fixture
def mock_perplexity():
    with patch("src.workflows.research_news.PerplexityTool") as mock:
        perplexity_instance = MagicMock()
        perplexity_instance.search = AsyncMock(return_value="Test perplexity search results")
        mock.return_value = perplexity_instance
        yield mock


@pytest.fixture
def mock_llm():
    with patch("src.workflows.research_news.LLM") as mock:
        llm_instance = MagicMock()
        llm_instance.generate_response = AsyncMock(return_value="Test analysis of crypto news")
        mock.return_value = llm_instance
        yield mock


@pytest.fixture
def mock_twitter():
    with patch("src.workflows.research_news.TwitterTool") as mock:
        twitter_instance = MagicMock()
        twitter_instance.post_thread = AsyncMock(return_value=["12345"])
        mock.return_value = twitter_instance
        yield mock


@pytest.mark.asyncio
async def test_analyze_news_with_link(mock_memory_module, mock_link_parser, mock_llm, mock_twitter):
    """Test analyze_news_workflow with a link provided."""

    # Test data
    news = "Important crypto news happened today"
    link = "https://example.com/crypto-news"

    # Run the workflow
    result = await analyze_news_workflow(news=news, memory=mock_memory_module, link=link)

    # Assertions
    assert result == "12345"
    mock_link_parser.return_value.search_links.assert_called_once_with(
        "Latest crypto news", gl="DE", hl="de", num=5
    )
    mock_llm.return_value.generate_response.assert_called_once()
    mock_twitter.return_value.post_thread.assert_called_once()
    mock_memory_module.store.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_news_without_link(
    mock_memory_module, mock_perplexity, mock_llm, mock_twitter
):
    """Test analyze_news_workflow without a link."""

    # Test data
    news = "Important crypto news happened today"

    # Run the workflow
    result = await analyze_news_workflow(news=news, memory=mock_memory_module)

    # Assertions
    assert result == "12345"
    mock_perplexity.return_value.search.assert_called_once_with("Latest crypto news")
    mock_llm.return_value.generate_response.assert_called_once()
    mock_twitter.return_value.post_thread.assert_called_once()
    mock_memory_module.store.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_news_error_handling(mock_memory_module):
    """Test error handling in analyze_news_workflow."""

    # Create a mock that raises an exception
    with patch("src.workflows.research_news.PerplexityTool") as mock_perplexity:
        perplexity_instance = MagicMock()
        perplexity_instance.search = AsyncMock(side_effect=Exception("Test error"))
        mock_perplexity.return_value = perplexity_instance

        # Run the workflow with an error
        result = await analyze_news_workflow(news="Test news", memory=mock_memory_module)

        # Assertions
        assert result is None
