import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.memory.backends.qdrant import QdrantBackend


@pytest.fixture
def mock_qdrant_client():
    """Mock the QdrantClient."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_qdrant_backend(mock_qdrant_client):
    """Create a QdrantBackend instance with a mocked QdrantClient."""
    with patch("src.memory.backends.qdrant.QdrantClient", return_value=mock_qdrant_client):
        backend = QdrantBackend(
            collection_name="test_collection",
            host="mock_host",
            port=9999,
            vector_size=768,
        )
    backend.client = mock_qdrant_client  # Explicitly set the mocked client
    return backend


def test_qdrant_backend_init(mock_qdrant_client):
    """Test QdrantBackend initialization with mocked client."""
    with patch("src.memory.backends.qdrant.QdrantClient", return_value=mock_qdrant_client):
        backend = QdrantBackend(
            collection_name="test_collection",
            host="mock_host",
            port=9999,
            vector_size=768,
        )

    mock_qdrant_client.get_collection.assert_called_once_with("test_collection")
    assert backend.collection_name == "test_collection"
    assert backend.vector_size == 768


@pytest.mark.asyncio
async def test_store_memory(mock_qdrant_backend, mock_qdrant_client):
    """Test storing a memory in Qdrant with mocked client."""
    event = "Test Event"
    action = "Test Action"
    outcome = "Test Outcome"
    embedding = [0.1, 0.2, 0.3]
    metadata = {"key": "value"}

    with patch("uuid.uuid4", return_value=uuid.UUID("12345678123456781234567812345678")):
        await mock_qdrant_backend.store(event, action, outcome, embedding, metadata)

    mock_qdrant_client.upsert.assert_called_once()


@pytest.mark.asyncio
async def test_store_memory_error(mock_qdrant_backend, mock_qdrant_client):
    """Test handling errors when storing a memory in Qdrant."""
    mock_qdrant_client.upsert.side_effect = Exception("Upsert failed")

    event = "Test Event"
    action = "Test Action"
    outcome = "Test Outcome"
    embedding = [0.1, 0.2, 0.3]

    with pytest.raises(Exception, match="Upsert failed"):
        await mock_qdrant_backend.store(event, action, outcome, embedding)


@pytest.mark.asyncio
async def test_search_memory(mock_qdrant_backend, mock_qdrant_client):
    """Test searching for memories in Qdrant."""
    query_vector = [0.1, 0.2, 0.3]
    mock_results = [
        MagicMock(payload={"event": "Event1"}),
        MagicMock(payload={"event": "Event2"}),
        MagicMock(payload={"event": "Event3"}),
    ]
    mock_qdrant_client.search.return_value = mock_results

    results = await mock_qdrant_backend.search(query_vector, top_k=3)

    mock_qdrant_client.search.assert_called_once_with(
        collection_name="test_collection", query_vector=query_vector, limit=3, query_filter=None
    )
    assert results == [{"event": "Event1"}, {"event": "Event2"}, {"event": "Event3"}]


@pytest.mark.asyncio
async def test_search_memory_no_results(mock_qdrant_backend, mock_qdrant_client):
    """Test searching for memories in Qdrant with no results."""
    query_vector = [0.1, 0.2, 0.3]
    mock_qdrant_client.search.return_value = []

    results = await mock_qdrant_backend.search(query_vector, top_k=3)

    mock_qdrant_client.search.assert_called_once_with(
        collection_name="test_collection", query_vector=query_vector, limit=3, query_filter=None
    )
    assert results == []
