from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from src.core.defs import MemoryBackendType
from src.llm.embeddings import EmbeddingGenerator
from src.memory.backends.chroma import ChromaBackend
from src.memory.backends.qdrant import QdrantBackend
from src.memory.memory_module import MemoryModule


@pytest.fixture
def mock_embedding_generator():
    """Mock the EmbeddingGenerator."""
    generator = AsyncMock(spec=EmbeddingGenerator)
    # Return a numpy array instead of a list
    generator.get_embedding.return_value = np.array([[0.1, 0.2, 0.3]])
    return generator


@pytest.fixture
def mock_qdrant_backend():
    """Mock the QdrantBackend."""
    backend = AsyncMock(spec=QdrantBackend)
    return backend


@pytest.fixture
def mock_chroma_backend():
    """Mock the ChromaBackend."""
    backend = AsyncMock(spec=ChromaBackend)
    return backend


@pytest.fixture
def memory_module_qdrant(mock_embedding_generator, mock_qdrant_backend):
    """Create a MemoryModule instance with QdrantBackend."""
    with (
        patch("src.memory.memory_module.QdrantBackend", return_value=mock_qdrant_backend),
        patch("src.memory.memory_module.EmbeddingGenerator", return_value=mock_embedding_generator),
    ):
        return MemoryModule(backend_type=MemoryBackendType.QDRANT)


@pytest.fixture
def memory_module_chroma(mock_embedding_generator, mock_chroma_backend):
    """Create a MemoryModule instance with ChromaBackend."""
    with (
        patch("src.memory.memory_module.ChromaBackend", return_value=mock_chroma_backend),
        patch("src.memory.memory_module.EmbeddingGenerator", return_value=mock_embedding_generator),
    ):
        return MemoryModule(backend_type=MemoryBackendType.CHROMA)


def test_memory_module_init_qdrant(mock_embedding_generator, mock_qdrant_backend):
    """Test MemoryModule initialization with QdrantBackend."""
    with (
        patch("src.memory.memory_module.QdrantBackend", return_value=mock_qdrant_backend),
        patch("src.memory.memory_module.EmbeddingGenerator", return_value=mock_embedding_generator),
    ):
        module = MemoryModule(backend_type=MemoryBackendType.QDRANT)
        assert isinstance(module.backend, QdrantBackend)


def test_memory_module_init_chroma(mock_embedding_generator, mock_chroma_backend):
    """Test MemoryModule initialization with ChromaBackend."""
    with (
        patch("src.memory.memory_module.ChromaBackend", return_value=mock_chroma_backend),
        patch("src.memory.memory_module.EmbeddingGenerator", return_value=mock_embedding_generator),
    ):
        module = MemoryModule(backend_type=MemoryBackendType.CHROMA)
        assert isinstance(module.backend, ChromaBackend)


def test_memory_module_init_invalid_backend():
    """Test MemoryModule initialization with an invalid backend."""
    with pytest.raises(ValueError, match="Unsupported backend type"):
        MemoryModule(backend_type="invalid_backend")


@pytest.mark.asyncio
async def test_store_memory_qdrant(memory_module_qdrant, mock_qdrant_backend):
    """Test storing a memory with QdrantBackend."""
    event = "Test Event"
    action = "Test Action"
    outcome = "Test Outcome"
    metadata = {"key": "value"}

    await memory_module_qdrant.store(event, action, outcome, metadata)

    memory_module_qdrant.embedding_generator.get_embedding.assert_called_once_with(
        f"{event} {action} {outcome}"
    )
    mock_qdrant_backend.store.assert_called_once_with(
        event=event,
        action=action,
        outcome=outcome,
        embedding=[0.1, 0.2, 0.3],
        metadata=metadata,
    )


@pytest.mark.asyncio
async def test_store_memory_chroma(memory_module_chroma, mock_chroma_backend):
    """Test storing a memory with ChromaBackend."""
    event = "Test Event"
    action = "Test Action"
    outcome = "Test Outcome"
    metadata = {"key": "value"}

    await memory_module_chroma.store(event, action, outcome, metadata)

    memory_module_chroma.embedding_generator.get_embedding.assert_called_once_with(
        f"{event} {action} {outcome}"
    )
    mock_chroma_backend.store.assert_called_once_with(
        event=event,
        action=action,
        outcome=outcome,
        embedding=[0.1, 0.2, 0.3],
        metadata=metadata,
    )


@pytest.mark.asyncio
async def test_search_memory_qdrant(memory_module_qdrant, mock_qdrant_backend):
    """Test searching memory with QdrantBackend."""
    query = "Test Query"
    top_k = 5
    mock_qdrant_backend.search.return_value = [{"event": "result_event"}]

    results = await memory_module_qdrant.search(query, top_k)

    memory_module_qdrant.embedding_generator.get_embedding.assert_called_once_with(query)
    mock_qdrant_backend.search.assert_called_once_with(
        query_vector=[0.1, 0.2, 0.3], top_k=top_k, filters=None
    )
    assert results == [{"event": "result_event"}]


@pytest.mark.asyncio
async def test_search_memory_chroma(memory_module_chroma, mock_chroma_backend):
    """Test searching memory with ChromaBackend."""
    query = "Test Query"
    top_k = 5
    mock_chroma_backend.search.return_value = [{"event": "result_event"}]

    results = await memory_module_chroma.search(query, top_k)

    memory_module_chroma.embedding_generator.get_embedding.assert_called_once_with(query)
    mock_chroma_backend.search.assert_called_once_with(
        query_vector=[0.1, 0.2, 0.3], top_k=top_k, filters=None
    )
    assert results == [{"event": "result_event"}]


@pytest.mark.asyncio
async def test_llm_filter_with_metadata(memory_module_qdrant):
    """Test llm_filter with metadata filters."""
    raw_data = "Project X is progressing well, with 80% completion."
    metadata_filters = {"project": "Project X", "status": "progress"}

    with patch.object(
        memory_module_qdrant.llm,
        "generate_response",
        AsyncMock(return_value="Project X is 80% complete"),
    ):
        result = await memory_module_qdrant.llm_filter(raw_data, metadata_filters)
        assert result == "Project X is 80% complete"


@pytest.mark.asyncio
async def test_llm_filter_no_metadata(memory_module_qdrant):
    """Test llm_filter without metadata filters."""
    raw_data = "Project X is progressing well, with 80% completion."

    with patch.object(
        memory_module_qdrant.llm,
        "generate_response",
        AsyncMock(return_value="Project X is 80% complete"),
    ):
        result = await memory_module_qdrant.llm_filter(raw_data)
        assert result == "Project X is 80% complete"


@pytest.mark.asyncio
async def test_llm_filter_irrelevant_data(memory_module_qdrant):
    """Test llm_filter with irrelevant data."""
    raw_data = "The weather is nice today."

    with patch.object(
        memory_module_qdrant.llm, "generate_response", AsyncMock(return_value="None")
    ):
        result = await memory_module_qdrant.llm_filter(raw_data)
        assert result is None


@pytest.mark.asyncio
async def test_filter_and_store_relevant(memory_module_qdrant, mock_qdrant_backend):
    """Test filter_and_store with relevant data."""
    raw_data = "Project X is progressing well, with 80% completion."
    data_type = "project_update"
    metadata = {"project": "Project X"}

    with patch.object(
        memory_module_qdrant.llm,
        "generate_response",
        AsyncMock(return_value="Project X is 80% complete"),
    ):
        await memory_module_qdrant.filter_and_store(raw_data, data_type, metadata)

        mock_qdrant_backend.store.assert_called_once()
        stored_metadata = mock_qdrant_backend.store.call_args[1]["metadata"]
        assert stored_metadata["project"] == "Project X"
        assert stored_metadata["type"] == "project_update"
        assert "timestamp" in stored_metadata


@pytest.mark.asyncio
async def test_filter_and_store_irrelevant(memory_module_qdrant, mock_qdrant_backend):
    """Test filter_and_store with irrelevant data."""
    raw_data = "The weather is nice today."
    data_type = "weather_update"

    with patch.object(
        memory_module_qdrant.llm, "generate_response", AsyncMock(return_value="None")
    ):
        await memory_module_qdrant.filter_and_store(raw_data, data_type)

        mock_qdrant_backend.store.assert_not_called()


@pytest.mark.asyncio
async def test_search_memory_qdrant_with_filters(memory_module_qdrant, mock_qdrant_backend):
    """Test searching memory with QdrantBackend with filters."""
    query = "Test Query"
    top_k = 5
    filters = {"type": "project_update", "project": "Project X"}
    mock_qdrant_backend.search.return_value = [{"event": "result_event"}]

    results = await memory_module_qdrant.search(query, top_k, filters)

    memory_module_qdrant.embedding_generator.get_embedding.assert_called_once_with(query)
    mock_qdrant_backend.search.assert_called_once_with(
        query_vector=[0.1, 0.2, 0.3], top_k=top_k, filters=filters
    )
    assert results == [{"event": "result_event"}]


@pytest.mark.asyncio
async def test_search_memory_chroma_with_filters(memory_module_chroma, mock_chroma_backend):
    """Test searching memory with ChromaBackend with filters."""
    query = "Test Query"
    top_k = 5
    filters = {"type": "project_update", "project": "Project X"}
    mock_chroma_backend.search.return_value = [{"event": "result_event"}]

    results = await memory_module_chroma.search(query, top_k, filters)

    memory_module_chroma.embedding_generator.get_embedding.assert_called_once_with(query)
    mock_chroma_backend.search.assert_called_once_with(
        query_vector=[0.1, 0.2, 0.3], top_k=top_k, filters=filters
    )
    assert results == [{"event": "result_event"}]
