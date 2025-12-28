"""Memory module for agent memory systems.

Provides:
- TriMemorySystem: Unified interface for tri-memory architecture
- EpisodicMemory: Time-indexed experiences
- SemanticMemory: Facts and knowledge
- ProceduralMemory: Skills and patterns
- MemoryModule: Legacy single-store memory (for backward compatibility)
"""

from src.memory.consolidation import ConsolidationResult, MemoryConsolidator
from src.memory.episodic import Episode, EpisodicMemory
from src.memory.memory_module import MemoryModule, get_memory_module
from src.memory.procedural import ProceduralMemory, Skill
from src.memory.semantic import Concept, Fact, SemanticMemory
from src.memory.tri_memory import MemoryRecall, TriMemorySystem, get_tri_memory_system


__all__ = [
    # Tri-memory system
    "TriMemorySystem",
    "MemoryRecall",
    "get_tri_memory_system",
    # Episodic memory
    "EpisodicMemory",
    "Episode",
    # Semantic memory
    "SemanticMemory",
    "Fact",
    "Concept",
    # Procedural memory
    "ProceduralMemory",
    "Skill",
    # Consolidation
    "MemoryConsolidator",
    "ConsolidationResult",
    # Legacy
    "MemoryModule",
    "get_memory_module",
]
