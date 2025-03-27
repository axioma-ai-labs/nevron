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


def test_init_with_provided_client(mock_openai_client):
    """Test EmbeddingGenerator initialization with custom values."""
    generator = EmbeddingGenerator(
        provider=EmbeddingProviderType.OPENAI,
        embedding_client=mock_openai_client,
    )
    assert generator.client == mock_openai_client
    assert generator.model_name == settings.OPENAI_EMBEDDING_MODEL


# @pytest.mark.skip(reason="Skipping test_get_embedding_single_text")
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


# @pytest.mark.skip(reason="Skipping test_get_embedding_multiple_texts")
@pytest.mark.asyncio
async def test_get_embedding_multiple_texts(embedding_generator, mock_logger, monkeypatch):
    """Test getting embeddings for multiple texts."""
    # arrange:
    mock_debug, _ = mock_logger
    texts = ["text1", "text2", "text3"]
    mock_embeddings = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

    # Set up mocking for the generate_embedding_api function instead of directly mocking client
    mock_generate_api = AsyncMock(return_value=np.array(mock_embeddings))
    monkeypatch.setattr("src.llm.embeddings.generate_embedding_api", mock_generate_api)

    # act:
    result = await embedding_generator.get_embedding(texts)

    # assert:
    mock_generate_api.assert_called_once_with(
        embedding_generator.client, texts, embedding_generator.model_name
    )
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


@pytest.mark.asyncio
async def test_init_without_embedding_client(monkeypatch):
    """Test EmbeddingGenerator initialization without providing embedding_client."""

    # Use the provider from settings
    provider = settings.EMBEDDING_PROVIDER

    # Skip test if provider is LLAMA_LOCAL as it's tested separately
    if provider == EmbeddingProviderType.LLAMA_LOCAL:
        pytest.skip("LLAMA_LOCAL provider is tested separately")

    # Mock the get_embedding_client function
    mock_client = AsyncMock(spec=AsyncOpenAI)
    mock_get_client = MagicMock(return_value=mock_client)
    monkeypatch.setattr("src.llm.embeddings.get_embedding_client", mock_get_client)

    # Create generator without providing client
    generator = EmbeddingGenerator(provider=provider)

    # Assert get_embedding_client was called with correct provider
    mock_get_client.assert_called_once_with(provider)
    # Assert the client was set correctly
    assert generator.client == mock_client
    # Assert the model name was set correctly based on provider
    if provider == EmbeddingProviderType.OPENAI:
        assert generator.model_name == settings.OPENAI_EMBEDDING_MODEL
    elif provider == EmbeddingProviderType.LLAMA_API:
        assert generator.model_name == settings.LLAMA_EMBEDDING_MODEL


def test_init_with_unsupported_provider(monkeypatch):
    """Test EmbeddingGenerator initialization with unsupported provider."""

    # Use the invalid provider
    with pytest.raises(ValueError, match="Unsupported embedding provider"):
        EmbeddingGenerator(provider=EmbeddingProviderType.UNSUPPORTED_PROVIDER)


@pytest.mark.asyncio
async def test_init_with_llama_local_provider(monkeypatch):
    """Test EmbeddingGenerator initialization with LLAMA_LOCAL provider."""
    # Mock the get_llama_model function
    mock_llama_model = MagicMock()
    mock_get_llama_model = MagicMock(return_value=mock_llama_model)
    monkeypatch.setattr("src.llm.embeddings.get_llama_model", mock_get_llama_model)

    # Create generator with LLAMA_LOCAL provider
    generator = EmbeddingGenerator(provider=EmbeddingProviderType.LLAMA_LOCAL)

    # Assert get_llama_model was called with correct path
    mock_get_llama_model.assert_called_once_with(settings.LLAMA_MODEL_PATH)
    # Assert the llama_model was set correctly
    assert generator.llama_model == mock_llama_model
