"""Tests for Semantic Memory."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from src.llm.embeddings import EmbeddingGenerator
from src.memory.backends.chroma import ChromaBackend
from src.memory.semantic import Concept, Fact, Relationship, SemanticMemory


class TestFact:
    """Tests for Fact dataclass."""

    def test_fact_creation(self):
        """Test creating a fact."""
        fact = Fact(
            id="fact-001",
            subject="Python",
            predicate="is",
            object="programming language",
            confidence=0.95,
            source="documentation",
        )

        assert fact.id == "fact-001"
        assert fact.subject == "Python"
        assert fact.predicate == "is"
        assert fact.object == "programming language"
        assert fact.confidence == 0.95

    def test_fact_to_statement(self):
        """Test converting fact to statement."""
        fact = Fact(
            id="fact-002",
            subject="Water",
            predicate="boils at",
            object="100 degrees Celsius",
        )

        statement = fact.to_statement()

        assert statement == "Water boils at 100 degrees Celsius"

    def test_fact_to_dict(self):
        """Test converting fact to dictionary."""
        fact = Fact(
            id="fact-003",
            subject="Test",
            predicate="has",
            object="value",
            confidence=0.8,
        )

        result = fact.to_dict()

        assert result["id"] == "fact-003"
        assert result["subject"] == "Test"
        assert result["confidence"] == 0.8

    def test_fact_from_dict(self):
        """Test creating fact from dictionary."""
        data = {
            "id": "fact-004",
            "subject": "From",
            "predicate": "dict",
            "object": "test",
            "confidence": 0.9,
            "source": "test_source",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        fact = Fact.from_dict(data)

        assert fact.id == "fact-004"
        assert fact.confidence == 0.9
        assert fact.source == "test_source"


class TestConcept:
    """Tests for Concept dataclass."""

    def test_concept_creation(self):
        """Test creating a concept."""
        concept = Concept(
            id="concept-001",
            name="Machine Learning",
            concept_type="field",
            description="A branch of AI",
            properties={"related_to": ["AI", "Statistics"]},
        )

        assert concept.id == "concept-001"
        assert concept.name == "Machine Learning"
        assert concept.concept_type == "field"
        assert "related_to" in concept.properties

    def test_concept_to_dict(self):
        """Test converting concept to dictionary."""
        concept = Concept(
            id="concept-002",
            name="Test Concept",
            concept_type="test",
            description="For testing",
        )

        result = concept.to_dict()

        assert result["id"] == "concept-002"
        assert result["name"] == "Test Concept"
        assert "created_at" in result

    def test_concept_from_dict(self):
        """Test creating concept from dictionary."""
        data = {
            "id": "concept-003",
            "name": "From Dict",
            "concept_type": "test",
            "description": "Created from dict",
            "properties": {"key": "value"},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        concept = Concept.from_dict(data)

        assert concept.id == "concept-003"
        assert concept.properties == {"key": "value"}


class TestRelationship:
    """Tests for Relationship dataclass."""

    def test_relationship_creation(self):
        """Test creating a relationship."""
        rel = Relationship(
            id="rel-001",
            source_id="concept-001",
            target_id="concept-002",
            relationship_type="related_to",
            strength=0.8,
        )

        assert rel.id == "rel-001"
        assert rel.source_id == "concept-001"
        assert rel.target_id == "concept-002"
        assert rel.strength == 0.8

    def test_relationship_to_dict(self):
        """Test converting relationship to dictionary."""
        rel = Relationship(
            id="rel-002",
            source_id="a",
            target_id="b",
            relationship_type="is_a",
        )

        result = rel.to_dict()

        assert result["id"] == "rel-002"
        assert result["relationship_type"] == "is_a"


@pytest.fixture
def mock_embedding_generator():
    """Mock the EmbeddingGenerator."""
    generator = AsyncMock(spec=EmbeddingGenerator)
    # Return a numpy array
    generator.get_embedding.return_value = np.array([[0.1, 0.2, 0.3]])
    return generator


@pytest.fixture
def mock_chroma_backend():
    """Mock the ChromaBackend."""
    backend = AsyncMock(spec=ChromaBackend)
    backend.store = AsyncMock()
    backend.search = AsyncMock(return_value=[])
    return backend


@pytest.fixture
def semantic_memory(mock_embedding_generator, mock_chroma_backend):
    """Create semantic memory for testing with mocked dependencies."""
    with (
        patch("src.memory.semantic.ChromaBackend", return_value=mock_chroma_backend),
        patch("src.memory.semantic.EmbeddingGenerator", return_value=mock_embedding_generator),
    ):
        memory = SemanticMemory(
            backend_type="chroma",
            collection_name="test_semantic_memory",
        )
        # Attach mocks to the instance for test access
        memory._mock_backend = mock_chroma_backend  # type: ignore[attr-defined]
        memory._mock_embedding = mock_embedding_generator  # type: ignore[attr-defined]
        return memory


class TestSemanticMemory:
    """Tests for SemanticMemory class."""

    def test_initialization(self, semantic_memory):
        """Test semantic memory initialization."""
        assert semantic_memory is not None
        assert semantic_memory.embedding_generator is not None

    @pytest.mark.asyncio
    async def test_store_fact(self, semantic_memory):
        """Test storing a fact."""
        fact = await semantic_memory.store_fact(
            subject="Python",
            predicate="is",
            obj="programming language",
            confidence=0.95,
            source="test",
        )

        assert fact is not None
        assert fact.id is not None
        assert fact.subject == "Python"

        # Verify backend was called
        semantic_memory._mock_backend.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_concept(self, semantic_memory):
        """Test storing a concept."""
        concept = await semantic_memory.store_concept(
            name="Neural Network",
            concept_type="technology",
            description="A computing system inspired by biological networks",
            properties={"layers": ["input", "hidden", "output"]},
        )

        assert concept is not None
        assert concept.id is not None
        assert concept.name == "Neural Network"

        # Verify backend was called
        semantic_memory._mock_backend.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_relationship(self, semantic_memory):
        """Test adding a relationship between concepts."""
        # Create two concepts first
        concept1 = await semantic_memory.store_concept(
            name="AI",
            concept_type="field",
            description="Artificial Intelligence",
        )
        concept2 = await semantic_memory.store_concept(
            name="ML",
            concept_type="field",
            description="Machine Learning",
        )

        # Add relationship
        rel = await semantic_memory.add_relationship(
            source_id=concept1.id,
            target_id=concept2.id,
            relationship_type="includes",
            strength=0.9,
        )

        assert rel is not None
        assert rel.source_id == concept1.id
        assert rel.target_id == concept2.id

    @pytest.mark.asyncio
    async def test_query_facts(self, semantic_memory):
        """Test querying for facts."""
        # Store a fact
        await semantic_memory.store_fact(
            subject="Query Test",
            predicate="is",
            obj="working",
        )

        # Query
        results = await semantic_memory.query(
            query="Query Test",
            top_k=5,
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_query_with_results(self, semantic_memory):
        """Test query returning results."""
        # Mock backend to return a fact result
        mock_result = {
            "id": "fact-result",
            "subject": "Test",
            "predicate": "is",
            "object": "found",
            "confidence": 0.9,
            "memory_type": "semantic_fact",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        semantic_memory._mock_backend.search.return_value = [mock_result]

        results = await semantic_memory.query("test query", top_k=5)

        assert len(results) == 1
        assert results[0].subject == "Test"

    @pytest.mark.asyncio
    async def test_get_related_concepts(self, semantic_memory):
        """Test getting related concepts."""
        # Create and relate concepts
        c1 = await semantic_memory.store_concept(
            name="Parent",
            concept_type="test",
            description="Parent concept",
        )
        c2 = await semantic_memory.store_concept(
            name="Child",
            concept_type="test",
            description="Child concept",
        )
        await semantic_memory.add_relationship(
            source_id=c1.id,
            target_id=c2.id,
            relationship_type="has_child",
        )

        # Get related
        related = await semantic_memory.get_related_concepts(c1.id)

        assert isinstance(related, list)
        # Should find the child concept
        if related:
            concept, rel = related[0]
            assert concept.id == c2.id

    def test_get_all_concepts(self, semantic_memory):
        """Test getting all concepts."""
        concepts = semantic_memory.get_all_concepts()
        assert isinstance(concepts, list)

    def test_get_concept_not_found(self, semantic_memory):
        """Test getting non-existent concept."""
        concept = semantic_memory.get_concept("nonexistent-id")
        assert concept is None

    @pytest.mark.asyncio
    async def test_infer(self, semantic_memory):
        """Test inference on semantic memory."""
        # Store some facts
        await semantic_memory.store_fact(
            subject="Cat",
            predicate="is a",
            obj="mammal",
        )

        # Run inference
        inferences = await semantic_memory.infer("What is a cat?")

        assert isinstance(inferences, list)
