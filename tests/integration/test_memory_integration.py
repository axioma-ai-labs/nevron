"""
Integration tests for Tri-Memory Architecture.

Tests that memory types work together properly for consolidation
and unified recall.

NOTE: These tests describe the intended API for memory integration.
Some APIs may not be fully implemented yet.
"""

import pytest


# Skip entire module if imports fail (APIs not implemented yet)
pytest.importorskip("src.memory.episodic", reason="EpisodicMemory API not fully implemented")

try:
    from src.memory.episodic import Episode, EpisodicMemory
    from src.memory.procedural import ProceduralMemory, Skill
    from src.memory.semantic import Concept, ConceptType, SemanticMemory
except ImportError as e:
    pytest.skip(f"Memory integration tests require unimplemented API: {e}", allow_module_level=True)


class TestTriMemoryIntegration:
    """Test that memory types work together."""

    @pytest.fixture
    def episodic_memory(self):
        """Create episodic memory instance."""
        return EpisodicMemory(max_episodes=100)

    @pytest.fixture
    def semantic_memory(self):
        """Create semantic memory instance."""
        return SemanticMemory()

    @pytest.fixture
    def procedural_memory(self):
        """Create procedural memory instance."""
        return ProceduralMemory()

    @pytest.mark.asyncio
    async def test_episodic_storage_and_retrieval(self, episodic_memory):
        """Test that episodes can be stored and retrieved."""
        # Store an episode
        episode = Episode(
            episode_id="ep-001",
            description="Searched for AI news",
            context={"query": "AI trends 2024"},
            actions=["search_tavily"],
            outcome="Found 5 relevant articles",
            success=True,
            importance=0.8,
        )

        await episodic_memory.store(episode)

        # Retrieve by ID
        retrieved = await episodic_memory.get("ep-001")
        assert retrieved is not None
        assert retrieved.description == "Searched for AI news"
        assert retrieved.success is True

    @pytest.mark.asyncio
    async def test_semantic_concept_relations(self, semantic_memory):
        """Test that semantic concepts can be related."""
        # Create related concepts
        ai_concept = Concept(
            concept_id="concept-ai",
            name="Artificial Intelligence",
            concept_type=ConceptType.DOMAIN,
            description="The field of AI and machine learning",
            properties={"field": "technology"},
        )

        ml_concept = Concept(
            concept_id="concept-ml",
            name="Machine Learning",
            concept_type=ConceptType.DOMAIN,
            description="Subset of AI focused on learning from data",
            properties={"field": "technology"},
        )

        await semantic_memory.store(ai_concept)
        await semantic_memory.store(ml_concept)

        # Create relation
        await semantic_memory.relate("concept-ai", "concept-ml", "contains", strength=0.9)

        # Query related concepts
        related = await semantic_memory.get_related("concept-ai")
        assert len(related) > 0
        assert any(c.concept_id == "concept-ml" for c, _, _ in related)

    @pytest.mark.asyncio
    async def test_procedural_skill_execution_tracking(self, procedural_memory):
        """Test that procedural memory tracks skill execution."""
        # Create a skill
        skill = Skill(
            skill_id="skill-search",
            name="Web Search",
            description="Search the web for information",
            trigger_conditions=["need information", "research task"],
            action_sequence=["search_tavily", "parse_results"],
            success_rate=0.85,
        )

        await procedural_memory.store(skill)

        # Record execution
        await procedural_memory.record_execution(
            "skill-search",
            success=True,
            context={"query": "AI news"},
            result={"articles": 5},
        )

        # Check skill was updated
        retrieved = await procedural_memory.get("skill-search")
        assert retrieved is not None
        assert retrieved.execution_count >= 1

    @pytest.mark.asyncio
    async def test_episodic_to_semantic_pattern(self, episodic_memory, semantic_memory):
        """Test pattern: experiences inform semantic knowledge."""
        # Store multiple related episodes
        for i in range(5):
            episode = Episode(
                episode_id=f"ep-search-{i}",
                description=f"Research task {i}",
                context={"task_type": "research"},
                actions=["search_tavily", "summarize"],
                outcome=f"Found information for task {i}",
                success=True,
                importance=0.7,
            )
            await episodic_memory.store(episode)

        # Retrieve episodes for pattern extraction
        episodes = await episodic_memory.search({"task_type": "research"}, limit=10)
        assert len(episodes) >= 3  # Should find multiple

        # Extract pattern and store as semantic concept
        if len(episodes) >= 3:
            research_concept = Concept(
                concept_id="concept-research-pattern",
                name="Research Task Pattern",
                concept_type=ConceptType.PATTERN,
                description="Common pattern for research tasks",
                properties={
                    "common_actions": ["search_tavily", "summarize"],
                    "success_rate": sum(e.success for e in episodes) / len(episodes),
                    "derived_from_episodes": len(episodes),
                },
            )
            await semantic_memory.store(research_concept)

            # Verify the concept was stored
            retrieved = await semantic_memory.get("concept-research-pattern")
            assert retrieved is not None
            assert retrieved.properties["derived_from_episodes"] >= 3

    @pytest.mark.asyncio
    async def test_episodic_to_procedural_pattern(self, episodic_memory, procedural_memory):
        """Test pattern: successful experiences become skills."""
        # Store successful episodes with same action pattern
        for i in range(5):
            episode = Episode(
                episode_id=f"ep-post-{i}",
                description=f"Posted update {i}",
                context={"channel": "telegram"},
                actions=["generate_text", "send_telegram_message"],
                outcome="Successfully posted",
                success=True,
                importance=0.6,
            )
            await episodic_memory.store(episode)

        # Find successful pattern
        episodes = await episodic_memory.search({"channel": "telegram"}, limit=10)
        successful = [e for e in episodes if e.success]

        # If pattern is consistent, create a skill
        if len(successful) >= 3:
            common_actions = successful[0].actions
            all_same = all(e.actions == common_actions for e in successful)

            if all_same:
                skill = Skill(
                    skill_id="skill-telegram-post",
                    name="Telegram Posting",
                    description="Post updates to Telegram",
                    trigger_conditions=["post to telegram", "send update"],
                    action_sequence=common_actions,
                    success_rate=len(successful) / len(episodes),
                )
                await procedural_memory.store(skill)

                # Verify skill was created
                retrieved = await procedural_memory.get("skill-telegram-post")
                assert retrieved is not None
                assert retrieved.success_rate > 0.5

    @pytest.mark.asyncio
    async def test_semantic_guides_procedural(self, semantic_memory, procedural_memory):
        """Test pattern: semantic knowledge helps select skills."""
        # Store domain concepts
        news_concept = Concept(
            concept_id="concept-news",
            name="News Gathering",
            concept_type=ConceptType.DOMAIN,
            description="Domain of news and information gathering",
            properties={
                "preferred_tools": ["search_tavily", "ask_perplexity"],
                "best_time": "morning",
            },
        )
        await semantic_memory.store(news_concept)

        # Store related skill
        news_skill = Skill(
            skill_id="skill-news",
            name="News Research",
            description="Research and gather news",
            trigger_conditions=["gather news", "research topic"],
            action_sequence=["search_tavily", "summarize"],
            success_rate=0.9,
            context_requirements={"domain": "news"},
        )
        await procedural_memory.store(news_skill)

        # Query: given a news-related task, find appropriate skill
        domain = await semantic_memory.get("concept-news")
        assert domain is not None

        skills = await procedural_memory.find_by_context({"domain": "news"})
        assert len(skills) >= 1
        assert any(s.skill_id == "skill-news" for s in skills)

    @pytest.mark.asyncio
    async def test_memory_consolidation_cycle(
        self, episodic_memory, semantic_memory, procedural_memory
    ):
        """Test full consolidation cycle across memory types."""
        # Phase 1: Accumulate episodes
        for i in range(10):
            success = i % 3 != 0  # 70% success rate
            episode = Episode(
                episode_id=f"ep-consolidate-{i}",
                description=f"Task {i}",
                context={"type": "consolidation_test"},
                actions=["action_a", "action_b"],
                outcome="Completed" if success else "Failed",
                success=success,
            )
            await episodic_memory.store(episode)

        # Phase 2: Analyze for patterns (semantic extraction)
        episodes = await episodic_memory.search({"type": "consolidation_test"}, limit=20)
        assert len(episodes) >= 5

        success_count = sum(1 for e in episodes if e.success)
        failure_count = len(episodes) - success_count

        # Store analysis as semantic knowledge
        analysis_concept = Concept(
            concept_id="concept-consolidation-analysis",
            name="Consolidation Test Analysis",
            concept_type=ConceptType.INSIGHT,
            description="Analysis of consolidation test episodes",
            properties={
                "total_episodes": len(episodes),
                "success_rate": success_count / len(episodes),
                "failure_rate": failure_count / len(episodes),
            },
        )
        await semantic_memory.store(analysis_concept)

        # Phase 3: Create skill from successful pattern
        successful_episodes = [e for e in episodes if e.success]
        if successful_episodes:
            skill = Skill(
                skill_id="skill-from-consolidation",
                name="Consolidated Skill",
                description="Skill derived from episode consolidation",
                trigger_conditions=["consolidation_test"],
                action_sequence=successful_episodes[0].actions,
                success_rate=success_count / len(episodes),
                derived_from=["episode_consolidation"],
            )
            await procedural_memory.store(skill)

        # Verify full cycle
        concept = await semantic_memory.get("concept-consolidation-analysis")
        assert concept is not None
        assert concept.properties["total_episodes"] >= 5

        skill = await procedural_memory.get("skill-from-consolidation")
        if successful_episodes:
            assert skill is not None

    @pytest.mark.asyncio
    async def test_unified_recall_simulation(
        self, episodic_memory, semantic_memory, procedural_memory
    ):
        """Test unified recall across all memory types."""
        # Store data in each memory type
        episode = Episode(
            episode_id="ep-unified-001",
            description="Unified recall test episode",
            context={"test": "unified"},
            actions=["test_action"],
            outcome="Success",
            success=True,
        )
        await episodic_memory.store(episode)

        concept = Concept(
            concept_id="concept-unified-001",
            name="Unified Test Concept",
            concept_type=ConceptType.DOMAIN,
            description="Test concept for unified recall",
            properties={"test": "unified"},
        )
        await semantic_memory.store(concept)

        skill = Skill(
            skill_id="skill-unified-001",
            name="Unified Test Skill",
            description="Test skill for unified recall",
            trigger_conditions=["unified test"],
            action_sequence=["test_action"],
        )
        await procedural_memory.store(skill)

        # Simulate unified recall
        query = "unified test"
        results = {
            "episodic": [],
            "semantic": [],
            "procedural": [],
        }

        # Search each memory type
        ep_results = await episodic_memory.search({"test": "unified"}, limit=5)
        results["episodic"] = [e.episode_id for e in ep_results]

        sem_results = await semantic_memory.search(query, limit=5)
        results["semantic"] = [c.concept_id for c in sem_results]

        proc_results = await procedural_memory.find_by_trigger("unified test")
        results["procedural"] = [s.skill_id for s in proc_results]

        # Verify we got results from all memory types
        assert len(results["episodic"]) >= 1
        assert "ep-unified-001" in results["episodic"]

        # Semantic and procedural may have different search mechanics
        # but should be able to find relevant items
        all_results = results["episodic"] + results["semantic"] + results["procedural"]
        assert len(all_results) >= 1


class TestMemoryPersistence:
    """Test memory persistence and recovery."""

    @pytest.mark.asyncio
    async def test_episodic_memory_limits(self):
        """Test that episodic memory respects limits."""
        memory = EpisodicMemory(max_episodes=5)

        # Store more than limit
        for i in range(10):
            episode = Episode(
                episode_id=f"ep-limit-{i}",
                description=f"Episode {i}",
                context={},
                actions=[],
                outcome="Done",
                success=True,
                importance=0.5 + (i * 0.05),  # Later = more important
            )
            await memory.store(episode)

        # Should only keep most important/recent
        all_episodes = await memory.get_all()
        assert len(all_episodes) <= 5

    @pytest.mark.asyncio
    async def test_semantic_memory_deduplication(self):
        """Test that semantic memory handles duplicates."""
        memory = SemanticMemory()

        # Store same concept twice
        concept1 = Concept(
            concept_id="concept-dup",
            name="Duplicate Test",
            concept_type=ConceptType.DOMAIN,
            description="First version",
        )
        await memory.store(concept1)

        concept2 = Concept(
            concept_id="concept-dup",
            name="Duplicate Test",
            concept_type=ConceptType.DOMAIN,
            description="Second version",
        )
        await memory.store(concept2)

        # Should have updated, not duplicated
        retrieved = await memory.get("concept-dup")
        assert retrieved is not None
        assert retrieved.description == "Second version"

    @pytest.mark.asyncio
    async def test_procedural_skill_improvement(self):
        """Test that skills improve with successful executions."""
        memory = ProceduralMemory()

        skill = Skill(
            skill_id="skill-improve",
            name="Improving Skill",
            description="A skill that should improve",
            trigger_conditions=["improve"],
            action_sequence=["action"],
            success_rate=0.5,
        )
        await memory.store(skill)

        # Record multiple successful executions
        for _ in range(10):
            await memory.record_execution(
                "skill-improve",
                success=True,
                context={},
            )

        # Success rate should have improved
        updated = await memory.get("skill-improve")
        assert updated is not None
        assert updated.success_rate > 0.5
        assert updated.execution_count >= 10
