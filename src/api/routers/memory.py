"""Memory router - endpoints for exploring and managing memory systems."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from src.api.dependencies import get_memory, verify_api_key
from src.api.schemas import (
    APIResponse,
    Concept,
    ConsolidationResult,
    Episode,
    Fact,
    MemoryRecallRequest,
    MemoryRecallResponse,
    MemoryStatistics,
    Skill,
)
from src.memory.tri_memory import TriMemorySystem


router = APIRouter()


@router.get("/statistics", response_model=APIResponse[MemoryStatistics])
async def get_memory_statistics(
    memory: TriMemorySystem = Depends(get_memory),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[MemoryStatistics]:
    """Get memory system statistics.

    Returns consolidation status and memory counts.
    """
    try:
        stats = memory.get_statistics()

        memory_stats = MemoryStatistics(
            consolidation_enabled=stats.get("consolidation_enabled", False),
            consolidation_running=stats.get("consolidation_running", False),
            last_consolidation=(
                datetime.fromisoformat(stats["last_consolidation"])
                if stats.get("last_consolidation")
                else None
            ),
            total_skills=stats.get("total_skills", 0),
            total_concepts=stats.get("total_concepts", 0),
            total_episodes=stats.get("total_episodes", 0),
            total_facts=stats.get("total_facts", 0),
        )

        return APIResponse(
            success=True,
            data=memory_stats,
            message="Memory statistics retrieved",
        )
    except Exception as e:
        logger.error(f"Failed to get memory statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get memory statistics: {str(e)}",
        )


@router.post("/recall", response_model=APIResponse[MemoryRecallResponse])
async def recall_memories(
    request: MemoryRecallRequest,
    memory: TriMemorySystem = Depends(get_memory),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[MemoryRecallResponse]:
    """Query all memory types with a search query.

    Returns relevant episodes, facts, concepts, and skills.
    """
    try:
        result = await memory.recall(
            query=request.query,
            top_k=request.top_k,
            include_episodes=request.include_episodes,
            include_facts=request.include_facts,
            include_concepts=request.include_concepts,
            include_skills=request.include_skills,
        )

        # Convert to response schema
        episodes = [
            Episode(
                id=e.id,
                timestamp=e.timestamp,
                event=e.event,
                action=e.action,
                outcome=e.outcome,
                emotional_valence=e.emotional_valence,
                importance=e.importance,
                context=e.context or {},
            )
            for e in result.episodes
        ]

        facts = [
            Fact(
                id=f.id,
                subject=f.subject,
                predicate=f.predicate,
                object=f.object,
                confidence=f.confidence,
                source=f.source,
                created_at=f.created_at,
            )
            for f in result.facts
        ]

        concepts = [
            Concept(
                id=c.id,
                name=c.name,
                concept_type=c.concept_type,
                description=c.description,
                properties=c.properties or {},
                created_at=c.created_at,
            )
            for c in result.concepts
        ]

        skills = [
            Skill(
                id=s.id,
                name=s.name,
                description=s.description,
                trigger_pattern=s.trigger_pattern,
                confidence=s.confidence,
                execution_count=s.usage_count,  # Use usage_count property
                success_count=s.success_count,
                action_sequence=s.action_sequence or [],
            )
            for s in result.skills
        ]

        response = MemoryRecallResponse(
            query=result.query,
            timestamp=result.timestamp,
            episodes=episodes,
            facts=facts,
            concepts=concepts,
            skills=skills,
            has_results=result.has_results,
        )

        return APIResponse(
            success=True,
            data=response,
            message=f"Recalled {len(episodes) + len(facts) + len(concepts) + len(skills)} memories",
        )
    except Exception as e:
        logger.error(f"Failed to recall memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to recall memories: {str(e)}",
        )


@router.get("/episodes", response_model=APIResponse[List[Episode]])
async def get_episodes(
    limit: int = Query(default=50, le=200),
    time_period: Optional[str] = Query(default=None, description="Natural language time period"),
    memory: TriMemorySystem = Depends(get_memory),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[Episode]]:
    """Get episodic memories.

    Args:
        limit: Maximum number of episodes to return
        time_period: Optional time period filter (e.g., "last hour", "today")
    """
    try:
        if time_period:
            raw_episodes = await memory.recall_temporal(time_period)
        else:
            # Get recent episodes via recall
            result = await memory.recall(
                query="recent experiences",
                top_k=limit,
                include_episodes=True,
                include_facts=False,
                include_concepts=False,
                include_skills=False,
            )
            raw_episodes = result.episodes

        episodes = [
            Episode(
                id=e.id,
                timestamp=e.timestamp,
                event=e.event,
                action=e.action,
                outcome=e.outcome,
                emotional_valence=e.emotional_valence,
                importance=e.importance,
                context=e.context or {},
            )
            for e in raw_episodes[:limit]
        ]

        return APIResponse(
            success=True,
            data=episodes,
            message=f"Retrieved {len(episodes)} episodes",
        )
    except Exception as e:
        logger.error(f"Failed to get episodes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get episodes: {str(e)}",
        )


@router.get("/facts", response_model=APIResponse[List[Fact]])
async def get_facts(
    limit: int = Query(default=50, le=200),
    subject: Optional[str] = Query(default=None),
    memory: TriMemorySystem = Depends(get_memory),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[Fact]]:
    """Get semantic facts.

    Args:
        limit: Maximum number of facts to return
        subject: Optional filter by subject
    """
    try:
        # Query facts
        query = subject if subject else "all known facts"
        result = await memory.recall(
            query=query,
            top_k=limit,
            include_episodes=False,
            include_facts=True,
            include_concepts=False,
            include_skills=False,
        )

        facts = [
            Fact(
                id=f.id,
                subject=f.subject,
                predicate=f.predicate,
                object=f.object,
                confidence=f.confidence,
                source=f.source,
                created_at=f.created_at,
            )
            for f in result.facts
        ]

        return APIResponse(
            success=True,
            data=facts,
            message=f"Retrieved {len(facts)} facts",
        )
    except Exception as e:
        logger.error(f"Failed to get facts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get facts: {str(e)}",
        )


@router.get("/concepts", response_model=APIResponse[List[Concept]])
async def get_concepts(
    limit: int = Query(default=50, le=200),
    concept_type: Optional[str] = Query(default=None),
    memory: TriMemorySystem = Depends(get_memory),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[Concept]]:
    """Get semantic concepts.

    Args:
        limit: Maximum number of concepts to return
        concept_type: Optional filter by concept type
    """
    try:
        # Get all concepts from semantic memory
        raw_concepts = memory.semantic.get_all_concepts()

        if concept_type:
            raw_concepts = [c for c in raw_concepts if c.concept_type == concept_type]

        concepts = [
            Concept(
                id=c.id,
                name=c.name,
                concept_type=c.concept_type,
                description=c.description,
                properties=c.properties or {},
                created_at=c.created_at,
            )
            for c in raw_concepts[:limit]
        ]

        return APIResponse(
            success=True,
            data=concepts,
            message=f"Retrieved {len(concepts)} concepts",
        )
    except Exception as e:
        logger.error(f"Failed to get concepts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get concepts: {str(e)}",
        )


@router.get("/skills", response_model=APIResponse[List[Skill]])
async def get_skills(
    limit: int = Query(default=50, le=200),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    memory: TriMemorySystem = Depends(get_memory),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[List[Skill]]:
    """Get procedural skills.

    Args:
        limit: Maximum number of skills to return
        min_confidence: Minimum confidence threshold
    """
    try:
        # Get all skills from procedural memory
        raw_skills = memory.procedural.get_all_skills()

        # Filter by confidence
        raw_skills = [s for s in raw_skills if s.confidence >= min_confidence]

        # Sort by confidence descending
        raw_skills.sort(key=lambda s: s.confidence, reverse=True)

        skills = [
            Skill(
                id=s.id,
                name=s.name,
                description=s.description,
                trigger_pattern=s.trigger_pattern,
                confidence=s.confidence,
                execution_count=s.usage_count,  # Use usage_count property
                success_count=s.success_count,
                action_sequence=s.action_sequence or [],
            )
            for s in raw_skills[:limit]
        ]

        return APIResponse(
            success=True,
            data=skills,
            message=f"Retrieved {len(skills)} skills",
        )
    except Exception as e:
        logger.error(f"Failed to get skills: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get skills: {str(e)}",
        )


@router.post("/consolidate", response_model=APIResponse[ConsolidationResult])
async def trigger_consolidation(
    memory: TriMemorySystem = Depends(get_memory),
    _auth: bool = Depends(verify_api_key),
) -> APIResponse[ConsolidationResult]:
    """Trigger immediate memory consolidation.

    Consolidates episodic memories into semantic knowledge and skills.
    """
    try:
        import time

        start_time = time.time()

        result = await memory.consolidate_now()

        duration = time.time() - start_time

        consolidation_result = ConsolidationResult(
            episodes_processed=result.episodes_processed,
            facts_created=result.facts_extracted,  # Map from actual attribute
            skills_updated=result.skills_created,  # Map from actual attribute
            duration_seconds=duration,
        )

        return APIResponse(
            success=True,
            data=consolidation_result,
            message="Memory consolidation completed",
        )
    except Exception as e:
        logger.error(f"Failed to consolidate memories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to consolidate memories: {str(e)}",
        )
