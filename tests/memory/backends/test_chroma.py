import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.memory.backends.chroma import ChromaBackend


@pytest.fixture
def mock_chroma_client():
    """Mock the ChromaDB client."""
    client = MagicMock()
    return client


@pytest.fixture
def mock_chroma_collection():
    """Mock the ChromaDB collection."""
    collection = MagicMock()
    return collection


@pytest.fixture
def mock_chroma_backend(mock_chroma_client, mock_chroma_collection):
    """Create a ChromaBackend instance with mocked client and collection."""
    with patch("src.memory.backends.chroma.chromadb.Client", return_value=mock_chroma_client):
        mock_chroma_client.get_or_create_collection.return_value = mock_chroma_collection
        backend = ChromaBackend(
            collection_name="test_collection",
            persist_directory="/mock/directory",
        )
    backend.collection = mock_chroma_collection  # Explicitly set the mocked collection
    return backend


def test_chroma_backend_init(mock_chroma_client, mock_chroma_collection):
    """Test ChromaBackend initialization with mocked client and collection."""
    with patch("src.memory.backends.chroma.chromadb.Client", return_value=mock_chroma_client):
        mock_chroma_client.get_or_create_collection.return_value = mock_chroma_collection
        backend = ChromaBackend(
            collection_name="test_collection",
            persist_directory="/mock/directory",
        )

    mock_chroma_client.get_or_create_collection.assert_called_once_with(
        name="test_collection", metadata={"hnsw:space": "cosine"}
    )
    assert backend.collection == mock_chroma_collection


@pytest.mark.asyncio
async def test_store_memory(mock_chroma_backend, mock_chroma_collection):
    """Test storing a memory in ChromaDB with mocked collection."""
    event = "Test Event"
    action = "Test Action"
    outcome = "Test Outcome"
    embedding = [0.1, 0.2, 0.3]
    metadata = {"key": "value"}

    with patch("uuid.uuid4", return_value=uuid.UUID("12345678123456781234567812345678")):
        await mock_chroma_backend.store(event, action, outcome, embedding, metadata)

    mock_chroma_collection.add.assert_called_once()


@pytest.mark.asyncio
async def test_store_memory_error(mock_chroma_backend, mock_chroma_collection):
    """Test handling errors when storing a memory in ChromaDB."""
    mock_chroma_collection.add.side_effect = Exception("Add failed")

    event = "Test Event"
    action = "Test Action"
    outcome = "Test Outcome"
    embedding = [0.1, 0.2, 0.3]

    with pytest.raises(Exception, match="Add failed"):
        await mock_chroma_backend.store(event, action, outcome, embedding)


@pytest.mark.asyncio
async def test_search_memory(mock_chroma_backend, mock_chroma_collection):
    """Test searching for memories in ChromaDB."""
    query_vector = [0.1, 0.2, 0.3]
    mock_results = {"metadatas": [[{"event": "Event1"}, {"event": "Event2"}, {"event": "Event3"}]]}
    mock_chroma_collection.query.return_value = mock_results

    results = await mock_chroma_backend.search(query_vector, top_k=3)

    mock_chroma_collection.query.assert_called_once_with(
        query_embeddings=[query_vector], n_results=3, where=None
    )
    assert results == [{"event": "Event1"}, {"event": "Event2"}, {"event": "Event3"}]


@pytest.mark.asyncio
async def test_search_memory_no_results(mock_chroma_backend, mock_chroma_collection):
    """Test searching for memories in ChromaDB with no results."""
    query_vector = [0.1, 0.2, 0.3]
    mock_chroma_collection.query.return_value = {"metadatas": [[]]}

    results = await mock_chroma_backend.search(query_vector, top_k=3)

    mock_chroma_collection.query.assert_called_once_with(
        query_embeddings=[query_vector], n_results=3, where=None
    )
    assert results == []


@pytest.mark.asyncio
async def test_search_memory_error(mock_chroma_backend, mock_chroma_collection):
    """Test handling errors when searching in ChromaDB."""
    mock_chroma_collection.query.side_effect = Exception("Query failed")

    query_vector = [0.1, 0.2, 0.3]

    results = await mock_chroma_backend.search(query_vector, top_k=3)
    assert results == []
