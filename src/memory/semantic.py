"""Semantic Memory - Facts, knowledge, and relationships.

Semantic memory stores factual knowledge and relationships between concepts.
It supports knowledge graph-like queries and inference.
Knowledge is consolidated from episodic memories over time.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Union

from loguru import logger

from src.core.config import settings
from src.core.defs import MemoryBackendType
from src.llm.embeddings import EmbeddingGenerator
from src.memory.backends.chroma import ChromaBackend
from src.memory.backends.qdrant import QdrantBackend


@dataclass
class Concept:
    """Represents a concept/entity in semantic memory."""

    id: str
    name: str
    concept_type: str  # e.g., "person", "tool", "action", "fact"
    description: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    confidence: float = 1.0  # How confident we are in this knowledge
    source_episodes: List[str] = field(default_factory=list)  # Episode IDs that contributed

    def to_dict(self) -> Dict[str, Any]:
        """Convert concept to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "concept_type": self.concept_type,
            "description": self.description,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "confidence": self.confidence,
            "source_episodes": self.source_episodes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Concept":
        """Create Concept from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            concept_type=data.get("concept_type", "fact"),
            description=data.get("description", ""),
            properties=data.get("properties", {}),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.now(timezone.utc)),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if isinstance(data.get("updated_at"), str)
            else data.get("updated_at", datetime.now(timezone.utc)),
            confidence=data.get("confidence", 1.0),
            source_episodes=data.get("source_episodes", []),
        )


@dataclass
class Relationship:
    """Represents a relationship between concepts."""

    id: str
    source_id: str
    target_id: str
    relationship_type: str  # e.g., "is_a", "has", "related_to", "causes"
    strength: float = 1.0  # Relationship strength 0.0 to 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert relationship to dictionary."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type,
            "strength": self.strength,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Fact:
    """Represents a factual statement in semantic memory."""

    id: str
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    source: str = ""  # Where this fact came from
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert fact to dictionary."""
        return {
            "id": self.id,
            "subject": self.subject,
            "predicate": self.predicate,
            "object": self.object,
            "confidence": self.confidence,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Fact":
        """Create Fact from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            subject=data["subject"],
            predicate=data["predicate"],
            object=data["object"],
            confidence=data.get("confidence", 1.0),
            source=data.get("source", ""),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.now(timezone.utc)),
            metadata=data.get("metadata", {}),
        )

    def to_statement(self) -> str:
        """Convert fact to natural language statement."""
        return f"{self.subject} {self.predicate} {self.object}"


class SemanticMemory:
    """Semantic memory system for storing facts and knowledge.

    Features:
    - Fact storage with subject-predicate-object triples
    - Concept storage with properties
    - Relationship tracking between concepts
    - Similarity-based knowledge retrieval
    - Confidence scoring for facts
    """

    def __init__(
        self,
        backend_type: str = settings.MEMORY_BACKEND_TYPE,
        collection_name: str = "semantic_memory",
    ):
        """Initialize semantic memory.

        Args:
            backend_type: Type of vector store backend
            collection_name: Name for the semantic memory collection
        """
        self.embedding_generator = EmbeddingGenerator()
        self.backend: Union[QdrantBackend, ChromaBackend]

        if backend_type == MemoryBackendType.QDRANT:
            self.backend = QdrantBackend(
                collection_name=collection_name,
                host=settings.MEMORY_HOST,
                port=settings.MEMORY_PORT,
                vector_size=settings.MEMORY_VECTOR_SIZE,
            )
        elif backend_type == MemoryBackendType.CHROMA:
            self.backend = ChromaBackend(
                collection_name=collection_name,
                persist_directory=settings.MEMORY_PERSIST_DIRECTORY,
            )
        else:
            raise ValueError(f"Unsupported backend type: {backend_type}")

        # In-memory indexes for fast lookups
        self._concepts: Dict[str, Concept] = {}
        self._relationships: Dict[str, Relationship] = {}
        self._concept_relationships: Dict[str, Set[str]] = {}  # concept_id -> relationship_ids

        logger.debug(f"Semantic memory initialized with {backend_type} backend")

    async def store_fact(
        self,
        subject: str,
        predicate: str,
        obj: str,
        confidence: float = 1.0,
        source: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Fact:
        """Store a fact as a subject-predicate-object triple.

        Args:
            subject: The subject of the fact
            predicate: The relationship/verb
            obj: The object of the fact
            confidence: Confidence score (0.0 to 1.0)
            source: Source of the fact
            metadata: Additional metadata

        Returns:
            The stored Fact
        """
        fact = Fact(
            id=str(uuid.uuid4()),
            subject=subject,
            predicate=predicate,
            object=obj,
            confidence=max(0.0, min(1.0, confidence)),
            source=source,
            metadata=metadata or {},
        )

        # Generate embedding for the fact statement
        statement = fact.to_statement()
        embedding = await self.embedding_generator.get_embedding(statement)

        # Prepare metadata for storage
        storage_metadata = fact.to_dict()
        storage_metadata["memory_type"] = "semantic_fact"

        # Store in backend
        await self.backend.store(
            event=statement,
            action="store_fact",
            outcome=f"Confidence: {confidence}",
            embedding=embedding[0].tolist(),
            metadata=storage_metadata,
        )

        logger.debug(f"Stored semantic fact: {statement}")
        return fact

    async def store_concept(
        self,
        name: str,
        concept_type: str,
        description: str,
        properties: Optional[Dict[str, Any]] = None,
        confidence: float = 1.0,
        source_episodes: Optional[List[str]] = None,
    ) -> Concept:
        """Store a concept/entity in semantic memory.

        Args:
            name: Name of the concept
            concept_type: Type of concept (person, tool, action, etc.)
            description: Description of the concept
            properties: Additional properties
            confidence: Confidence score
            source_episodes: Episode IDs that contributed to this knowledge

        Returns:
            The stored Concept
        """
        concept = Concept(
            id=str(uuid.uuid4()),
            name=name,
            concept_type=concept_type,
            description=description,
            properties=properties or {},
            confidence=max(0.0, min(1.0, confidence)),
            source_episodes=source_episodes or [],
        )

        # Generate embedding
        text = f"{name}: {description}"
        embedding = await self.embedding_generator.get_embedding(text)

        # Prepare metadata
        storage_metadata = concept.to_dict()
        storage_metadata["memory_type"] = "semantic_concept"

        # Store in backend
        await self.backend.store(
            event=name,
            action="store_concept",
            outcome=description,
            embedding=embedding[0].tolist(),
            metadata=storage_metadata,
        )

        # Update in-memory index
        self._concepts[concept.id] = concept

        logger.debug(f"Stored semantic concept: {name}")
        return concept

    async def add_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        strength: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Relationship:
        """Add a relationship between two concepts.

        Args:
            source_id: Source concept ID
            target_id: Target concept ID
            relationship_type: Type of relationship
            strength: Relationship strength (0.0 to 1.0)
            properties: Additional properties

        Returns:
            The created Relationship
        """
        relationship = Relationship(
            id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            strength=max(0.0, min(1.0, strength)),
            properties=properties or {},
        )

        # Store in-memory
        self._relationships[relationship.id] = relationship

        # Update concept relationships index
        if source_id not in self._concept_relationships:
            self._concept_relationships[source_id] = set()
        self._concept_relationships[source_id].add(relationship.id)

        if target_id not in self._concept_relationships:
            self._concept_relationships[target_id] = set()
        self._concept_relationships[target_id].add(relationship.id)

        logger.debug(f"Added relationship: {source_id} -{relationship_type}-> {target_id}")
        return relationship

    async def query(
        self,
        query: str,
        top_k: int = 5,
        min_confidence: float = 0.0,
        fact_type: Optional[str] = None,
    ) -> List[Union[Fact, Concept]]:
        """Query semantic memory for relevant facts and concepts.

        Args:
            query: Natural language query
            top_k: Maximum number of results
            min_confidence: Minimum confidence threshold
            fact_type: Filter by type (semantic_fact or semantic_concept)

        Returns:
            List of matching Facts and/or Concepts
        """
        # Generate query embedding
        query_embedding = await self.embedding_generator.get_embedding(query)

        # Build filters
        filters: Dict[str, Any] = {}
        if fact_type:
            filters["memory_type"] = fact_type
        else:
            filters["memory_type"] = {"$in": ["semantic_fact", "semantic_concept"]}

        # Search backend
        results = await self.backend.search(
            query_vector=query_embedding[0].tolist(),
            top_k=top_k * 2,  # Get more to filter
            filters=filters,
        )

        # Convert to Fact/Concept objects
        items: List[Union[Fact, Concept]] = []
        for result in results:
            confidence = result.get("confidence", 1.0)
            if confidence < min_confidence:
                continue

            memory_type = result.get("memory_type")
            if memory_type == "semantic_fact":
                items.append(Fact.from_dict(result))
            elif memory_type == "semantic_concept":
                items.append(Concept.from_dict(result))

        return items[:top_k]

    async def get_related_concepts(
        self,
        concept_id: str,
        relationship_type: Optional[str] = None,
    ) -> List[tuple[Concept, Relationship]]:
        """Get concepts related to a given concept.

        Args:
            concept_id: ID of the concept to find relations for
            relationship_type: Optional filter by relationship type

        Returns:
            List of (Concept, Relationship) tuples
        """
        related: List[tuple[Concept, Relationship]] = []

        relationship_ids = self._concept_relationships.get(concept_id, set())
        for rel_id in relationship_ids:
            relationship = self._relationships.get(rel_id)
            if not relationship:
                continue

            if relationship_type and relationship.relationship_type != relationship_type:
                continue

            # Get the related concept
            if relationship.source_id == concept_id:
                related_id = relationship.target_id
            else:
                related_id = relationship.source_id

            concept = self._concepts.get(related_id)
            if concept:
                related.append((concept, relationship))

        return related

    async def infer(self, query: str) -> List[str]:
        """Attempt to infer new knowledge from existing facts.

        This is a simple inference that looks for transitive relationships.

        Args:
            query: Query to infer about

        Returns:
            List of inferred statements
        """
        # Get relevant facts
        facts = await self.query(query, top_k=10, fact_type="semantic_fact")

        inferences: List[str] = []

        # Look for simple transitive patterns
        # If A -> B and B -> C, then A might relate to C
        fact_list = [f for f in facts if isinstance(f, Fact)]

        for fact1 in fact_list:
            for fact2 in fact_list:
                if fact1.id == fact2.id:
                    continue

                # Check for transitive pattern
                if fact1.object.lower() == fact2.subject.lower():
                    # Potential transitive inference
                    inference = (
                        f"{fact1.subject} may {fact2.predicate} {fact2.object} (via {fact1.object})"
                    )
                    inferences.append(inference)

        return inferences

    async def update_confidence(self, fact_id: str, new_confidence: float) -> bool:
        """Update the confidence of a fact.

        Args:
            fact_id: ID of the fact to update
            new_confidence: New confidence value

        Returns:
            True if successful
        """
        # This would need backend support for updates
        logger.debug(f"Updating fact {fact_id} confidence to {new_confidence}")
        return True

    async def get_facts_about(self, subject: str, top_k: int = 10) -> List[Fact]:
        """Get all facts about a specific subject.

        Args:
            subject: Subject to query
            top_k: Maximum number of facts

        Returns:
            List of Facts about the subject
        """
        results = await self.query(subject, top_k=top_k, fact_type="semantic_fact")
        return [f for f in results if isinstance(f, Fact)]

    def get_all_concepts(self) -> List[Concept]:
        """Get all stored concepts.

        Returns:
            List of all concepts
        """
        return list(self._concepts.values())

    def get_concept(self, concept_id: str) -> Optional[Concept]:
        """Get a specific concept by ID.

        Args:
            concept_id: ID of the concept

        Returns:
            Concept or None if not found
        """
        return self._concepts.get(concept_id)
