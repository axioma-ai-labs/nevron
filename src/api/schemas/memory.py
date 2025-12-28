"""Memory-related schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Episode(BaseModel):
    """Episodic memory entry."""

    id: str
    timestamp: datetime
    event: str
    action: str
    outcome: str
    emotional_valence: float = 0.0
    importance: float = 0.5
    context: Dict[str, Any] = Field(default_factory=dict)


class Fact(BaseModel):
    """Semantic fact entry."""

    id: str
    subject: str
    predicate: str
    object: str
    confidence: float = 1.0
    source: str = ""
    created_at: datetime


class Concept(BaseModel):
    """Semantic concept entry."""

    id: str
    name: str
    concept_type: str
    description: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class Skill(BaseModel):
    """Procedural skill entry."""

    id: str
    name: str
    description: str
    trigger_pattern: str
    confidence: float = 0.5
    execution_count: int = 0
    success_count: int = 0
    action_sequence: List[Dict[str, Any]] = Field(default_factory=list)


class MemoryRecallRequest(BaseModel):
    """Request for memory recall."""

    query: str
    top_k: int = 5
    include_episodes: bool = True
    include_facts: bool = True
    include_concepts: bool = True
    include_skills: bool = True


class MemoryRecallResponse(BaseModel):
    """Response from memory recall."""

    query: str
    timestamp: datetime
    episodes: List[Episode] = Field(default_factory=list)
    facts: List[Fact] = Field(default_factory=list)
    concepts: List[Concept] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    has_results: bool = False


class MemoryStatistics(BaseModel):
    """Memory system statistics."""

    consolidation_enabled: bool
    consolidation_running: bool
    last_consolidation: Optional[datetime] = None
    total_skills: int = 0
    total_concepts: int = 0
    total_episodes: int = 0
    total_facts: int = 0


class ConsolidationResult(BaseModel):
    """Result from memory consolidation."""

    episodes_processed: int
    facts_created: int
    skills_updated: int
    duration_seconds: float
