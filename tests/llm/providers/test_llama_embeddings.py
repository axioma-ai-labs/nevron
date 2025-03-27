from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from src.llm.providers.llama_embeddings import (
    generate_embedding_api,
    generate_llama_embedding_local,
)


@pytest.mark.asyncio
async def test_generate_llama_embedding_local_success():
    """Test successful local embedding generation."""
    # Mock the Llama model
    mock_model = MagicMock()
    mock_model.embed.return_value = [0.1, 0.2, 0.3]

    # Test with a single string
    result = await generate_llama_embedding_local(mock_model, "test text")

    # Verify results
    assert isinstance(result, np.ndarray)
    assert result.shape[0] == 1  # One embedding
    mock_model.embed.assert_called_once_with("test text", normalize=True)

    # Reset mock
    mock_model.reset_mock()

    # Test with a list of strings
    texts = ["text1", "text2"]
    result = await generate_llama_embedding_local(mock_model, texts)

    # Verify results
    assert isinstance(result, np.ndarray)
    assert result.shape[0] == 2  # Two embeddings
    assert mock_model.embed.call_count == 2


@pytest.mark.asyncio
async def test_generate_llama_embedding_local_error():
    """Test error handling in local embedding generation."""
    # Mock the Llama model to raise an exception
    mock_model = MagicMock()
    mock_model.embed.side_effect = Exception("Embedding error")

    # Test with a single string
    with pytest.raises(Exception) as excinfo:
        await generate_llama_embedding_local(mock_model, "test text")

    assert "Embedding error" in str(excinfo.value)


@pytest.mark.asyncio
async def test_generate_embedding_api_error():
    """Test error handling in API embedding generation."""
    # Mock the OpenAI client
    mock_client = AsyncMock()
    mock_client.embeddings.create.side_effect = Exception("API error")

    # Test with a single string
    with pytest.raises(Exception) as excinfo:
        await generate_embedding_api(mock_client, "test text", "text-embedding-3-small")

    assert "API error" in str(excinfo.value)
    mock_client.embeddings.create.assert_called_once()
