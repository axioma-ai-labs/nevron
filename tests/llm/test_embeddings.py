from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from loguru import logger
from openai import AsyncOpenAI
from openai.types.create_embedding_response import CreateEmbeddingResponse

from src.core.config import settings
from src.core.defs import EmbeddingProviderType
from src.llm.embeddings import EmbeddingGenerator


@pytest.fixture
def mock_logger(monkeypatch):
    """Mock logger for testing."""
    mock_debug = MagicMock()
    mock_error = MagicMock()
    monkeypatch.setattr(logger, "debug", mock_debug)
    monkeypatch.setattr(logger, "error", mock_error)
    return mock_debug, mock_error


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = AsyncMock(spec=AsyncOpenAI)
    # Create embeddings attribute with create method
    embeddings = AsyncMock()
    embeddings.create = AsyncMock()
    client.embeddings = embeddings
    return client


@pytest.fixture
def embedding_generator(mock_openai_client):
    """Create an EmbeddingGenerator instance with mocked client."""
    return EmbeddingGenerator(
        provider=EmbeddingProviderType.OPENAI,
        embedding_client=mock_openai_client,
    )


def create_mock_embedding_response(embeddings_data):
    """Helper function to create mock embedding responses."""
    mock_embeddings = []
    for emb in embeddings_data:
        mock_embedding = MagicMock()
        mock_embedding.embedding = emb
        mock_embeddings.append(mock_embedding)

    mock_response = MagicMock(spec=CreateEmbeddingResponse)
    mock_response.data = mock_embeddings
    return mock_response


def test_init_custom_values(mock_openai_client):
    """Test EmbeddingGenerator initialization with custom values."""
    generator = EmbeddingGenerator(
        provider=EmbeddingProviderType.OPENAI,
        embedding_client=mock_openai_client,
    )
    assert generator.client == mock_openai_client
    assert generator.model_name == settings.OPENAI_EMBEDDING_MODEL


@pytest.mark.skip(reason="Skipping test_get_embedding_single_text")
@pytest.mark.asyncio
async def test_get_embedding_single_text(embedding_generator, mock_logger):
    """Test getting embeddings for a single text."""
    # arrange:
    mock_debug, _ = mock_logger
    text = "test text"
    mock_embedding = [0.1, 0.2, 0.3]
    embedding_generator.client.embeddings.create.return_value = create_mock_embedding_response(
        [mock_embedding]
    )

    # act:
    result = await embedding_generator.get_embedding(text)

    # assert:
    embedding_generator.client.embeddings.create.assert_called_once_with(
        model=embedding_generator.model_name, input=[text]
    )
    mock_debug.assert_called_once_with("Getting embeddings for 1 texts")
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_equal(result, np.array([mock_embedding]))


@pytest.mark.skip(reason="Skipping test_get_embedding_multiple_texts")
@pytest.mark.asyncio
async def test_get_embedding_multiple_texts(embedding_generator, mock_logger):
    """Test getting embeddings for multiple texts."""
    # arrange:
    mock_debug, _ = mock_logger
    texts = ["text1", "text2", "text3"]
    mock_embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]
    embedding_generator.client.embeddings.create.return_value = create_mock_embedding_response(
        mock_embeddings
    )

    # act:
    result = await embedding_generator.get_embedding(texts)

    # assert:
    embedding_generator.client.embeddings.create.assert_called_once_with(
        model=embedding_generator.model_name, input=texts
    )
    mock_debug.assert_called_once_with("Getting embeddings for 3 texts")
    assert isinstance(result, np.ndarray)
    np.testing.assert_array_equal(result, np.array(mock_embeddings))


@pytest.mark.asyncio
async def test_get_embedding_empty_input(embedding_generator, mock_logger):
    """Test error handling for empty input."""
    # arrange:
    _, mock_error = mock_logger

    # act/assert:
    with pytest.raises(ValueError, match="Input text cannot be empty"):
        await embedding_generator.get_embedding("")

    embedding_generator.client.embeddings.create.assert_not_called()


@pytest.mark.skip(reason="Skipping test_get_embedding_api_error")
@pytest.mark.asyncio
async def test_get_embedding_api_error(embedding_generator, mock_logger):
    """Test error handling for API errors."""
    # arrange:
    _, mock_error = mock_logger
    text = "test text"
    error_message = "API Error"
    embedding_generator.client.embeddings.create.side_effect = Exception(error_message)

    # act/assert:
    with pytest.raises(Exception, match=error_message):
        await embedding_generator.get_embedding(text)

    mock_error.assert_called_once()
    assert error_message in mock_error.call_args[0][0]


@pytest.mark.asyncio
async def test_get_embedding_response_processing(embedding_generator):
    """Test proper processing of API response structure."""
    # arrange:
    text = "test text"
    mock_embedding = [0.1, 0.2, 0.3]
    embedding_generator.client.embeddings.create.return_value = create_mock_embedding_response(
        [mock_embedding]
    )

    # act:
    result = await embedding_generator.get_embedding(text)

    # assert:
    assert isinstance(result, np.ndarray)
    assert result.shape == (1, len(mock_embedding))
    np.testing.assert_array_equal(result[0], np.array(mock_embedding))
