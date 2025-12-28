"""Tests for Procedural Memory."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import numpy as np
import pytest

from src.llm.embeddings import EmbeddingGenerator
from src.memory.backends.chroma import ChromaBackend
from src.memory.procedural import ActionPattern, ProceduralMemory, Skill


class TestSkill:
    """Tests for Skill dataclass."""

    def test_skill_creation(self):
        """Test creating a skill."""
        skill = Skill(
            id="skill-001",
            name="Test Skill",
            description="A test skill",
            trigger_pattern="test pattern",
            action_sequence=[{"action": "step1"}, {"action": "step2"}],
            preconditions=["condition1"],
            postconditions=["result1"],
        )

        assert skill.id == "skill-001"
        assert skill.name == "Test Skill"
        assert len(skill.action_sequence) == 2

    def test_skill_confidence_no_usage(self):
        """Test skill confidence with no usage."""
        skill = Skill(
            id="skill-002",
            name="Unused Skill",
            description="Never used",
            trigger_pattern="unused",
            action_sequence=[],
            preconditions=[],
            postconditions=[],
        )

        assert skill.confidence == 0.5  # Neutral confidence

    def test_skill_confidence_all_success(self):
        """Test skill confidence with all successes."""
        skill = Skill(
            id="skill-003",
            name="Successful Skill",
            description="Always works",
            trigger_pattern="success",
            action_sequence=[],
            preconditions=[],
            postconditions=[],
            success_count=10,
            failure_count=0,
        )

        assert skill.confidence == 1.0

    def test_skill_confidence_mixed(self):
        """Test skill confidence with mixed results."""
        skill = Skill(
            id="skill-004",
            name="Mixed Skill",
            description="Sometimes works",
            trigger_pattern="mixed",
            action_sequence=[],
            preconditions=[],
            postconditions=[],
            success_count=7,
            failure_count=3,
        )

        assert skill.confidence == 0.7

    def test_skill_usage_count(self):
        """Test skill usage count property."""
        skill = Skill(
            id="skill-005",
            name="Used Skill",
            description="Used often",
            trigger_pattern="used",
            action_sequence=[],
            preconditions=[],
            postconditions=[],
            success_count=5,
            failure_count=2,
        )

        assert skill.usage_count == 7

    def test_skill_to_dict(self):
        """Test converting skill to dictionary."""
        skill = Skill(
            id="skill-006",
            name="Dict Skill",
            description="For dict test",
            trigger_pattern="dict",
            action_sequence=[{"action": "test"}],
            preconditions=["pre1"],
            postconditions=["post1"],
            success_count=3,
            failure_count=1,
        )

        result = skill.to_dict()

        assert result["id"] == "skill-006"
        assert result["name"] == "Dict Skill"
        assert result["confidence"] == 0.75
        assert "created_at" in result

    def test_skill_from_dict(self):
        """Test creating skill from dictionary."""
        data = {
            "id": "skill-007",
            "name": "From Dict",
            "description": "Created from dict",
            "trigger_pattern": "pattern",
            "action_sequence": [{"action": "a1"}],
            "preconditions": [],
            "postconditions": [],
            "success_count": 5,
            "failure_count": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        skill = Skill.from_dict(data)

        assert skill.id == "skill-007"
        assert skill.success_count == 5


class TestActionPattern:
    """Tests for ActionPattern dataclass."""

    def test_action_pattern_creation(self):
        """Test creating an action pattern."""
        pattern = ActionPattern(
            id="pattern-001",
            actions=[{"action": "step1"}, {"action": "step2"}],
            context={"state": "ready"},
            outcome="completed",
            success=True,
        )

        assert pattern.id == "pattern-001"
        assert len(pattern.actions) == 2
        assert pattern.success is True

    def test_action_pattern_to_dict(self):
        """Test converting pattern to dictionary."""
        pattern = ActionPattern(
            id="pattern-002",
            actions=[{"action": "test"}],
            context={},
            outcome="done",
            success=False,
        )

        result = pattern.to_dict()

        assert result["id"] == "pattern-002"
        assert result["success"] is False
        assert "timestamp" in result


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
def procedural_memory(mock_embedding_generator, mock_chroma_backend):
    """Create procedural memory for testing with mocked dependencies."""
    with (
        patch("src.memory.procedural.ChromaBackend", return_value=mock_chroma_backend),
        patch("src.memory.procedural.EmbeddingGenerator", return_value=mock_embedding_generator),
    ):
        memory = ProceduralMemory(
            backend_type="chroma",
            collection_name="test_procedural_memory",
        )
        # Attach mocks to the instance for test access
        memory._mock_backend = mock_chroma_backend  # type: ignore[attr-defined]
        memory._mock_embedding = mock_embedding_generator  # type: ignore[attr-defined]
        return memory


class TestProceduralMemory:
    """Tests for ProceduralMemory class."""

    def test_initialization(self, procedural_memory):
        """Test procedural memory initialization."""
        assert procedural_memory is not None
        assert procedural_memory.embedding_generator is not None

    def test_check_preconditions_empty(self, procedural_memory):
        """Test checking empty preconditions."""
        result = procedural_memory._check_preconditions([], {"any": "context"})
        assert result is True

    def test_check_preconditions_match(self, procedural_memory):
        """Test checking matching preconditions."""
        result = procedural_memory._check_preconditions(
            ["ready"],
            {"state": "ready", "data": "loaded"},
        )
        assert result is True

    def test_check_preconditions_no_match(self, procedural_memory):
        """Test checking non-matching preconditions."""
        result = procedural_memory._check_preconditions(
            ["required_condition"],
            {"state": "idle"},
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_store_skill(self, procedural_memory):
        """Test storing a skill."""
        skill = await procedural_memory.store_skill(
            name="Test Store Skill",
            description="Skill for storage test",
            trigger_pattern="store test",
            action_sequence=[{"action": "step1"}, {"action": "step2"}],
            preconditions=["ready"],
            postconditions=["done"],
        )

        assert skill is not None
        assert skill.id is not None
        assert skill.name == "Test Store Skill"

        # Verify backend was called
        procedural_memory._mock_backend.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_skill(self, procedural_memory):
        """Test retrieving skills."""
        # Store a skill
        await procedural_memory.store_skill(
            name="Retrieve Test",
            description="For retrieval testing",
            trigger_pattern="retrieve pattern",
            action_sequence=[{"action": "test"}],
        )

        # Retrieve
        skills = await procedural_memory.retrieve_skill(
            task="retrieve test",
            top_k=5,
        )

        assert isinstance(skills, list)

    @pytest.mark.asyncio
    async def test_record_outcome_success(self, procedural_memory):
        """Test recording successful outcome."""
        # Store a skill first
        skill = await procedural_memory.store_skill(
            name="Outcome Test",
            description="For outcome testing",
            trigger_pattern="outcome",
            action_sequence=[],
        )

        # Record success
        result = await procedural_memory.record_outcome(skill.id, success=True)

        assert result is True
        assert procedural_memory._skills[skill.id].success_count == 1

    @pytest.mark.asyncio
    async def test_record_outcome_failure(self, procedural_memory):
        """Test recording failed outcome."""
        skill = await procedural_memory.store_skill(
            name="Failure Test",
            description="For failure testing",
            trigger_pattern="failure",
            action_sequence=[],
        )

        # Record failure
        await procedural_memory.record_outcome(skill.id, success=False)

        assert procedural_memory._skills[skill.id].failure_count == 1

    @pytest.mark.asyncio
    async def test_record_outcome_unknown_skill(self, procedural_memory):
        """Test recording outcome for unknown skill."""
        result = await procedural_memory.record_outcome("unknown-id", success=True)
        assert result is False

    @pytest.mark.asyncio
    async def test_observe_pattern_single(self, procedural_memory):
        """Test observing a single pattern."""
        result = await procedural_memory.observe_pattern(
            actions=[{"action": "single_test"}],
            context={"state": "testing"},
            outcome="observed",
            success=True,
        )

        # Single observation shouldn't create a skill yet
        assert result is None

    @pytest.mark.asyncio
    async def test_observe_pattern_promote_to_skill(self, procedural_memory):
        """Test promoting pattern to skill after enough observations."""
        # Observe the same pattern multiple times
        actions = [{"action": "repeated_test"}]

        for i in range(ProceduralMemory.MIN_OBSERVATIONS_FOR_SKILL):
            result = await procedural_memory.observe_pattern(
                actions=actions,
                context={"iteration": i},
                outcome=f"observation_{i}",
                success=True,
            )

        # Last observation should trigger skill creation
        assert result is not None
        assert isinstance(result, Skill)

    @pytest.mark.asyncio
    async def test_compose_skills(self, procedural_memory):
        """Test composing multiple skills."""
        # Create component skills
        skill1 = await procedural_memory.store_skill(
            name="Skill A",
            description="First component",
            trigger_pattern="skill_a",
            action_sequence=[{"action": "a1"}],
            preconditions=["ready"],
            postconditions=["middle"],
        )
        skill2 = await procedural_memory.store_skill(
            name="Skill B",
            description="Second component",
            trigger_pattern="skill_b",
            action_sequence=[{"action": "b1"}],
            preconditions=["middle"],
            postconditions=["done"],
        )

        # Compose
        composite = await procedural_memory.compose_skills(
            skill_ids=[skill1.id, skill2.id],
            name="Composite Skill",
            description="Combined A and B",
        )

        assert composite is not None
        assert len(composite.action_sequence) == 2
        assert composite.metadata.get("composite") is True

    @pytest.mark.asyncio
    async def test_compose_skills_insufficient(self, procedural_memory):
        """Test composing with insufficient skills."""
        skill = await procedural_memory.store_skill(
            name="Single Skill",
            description="Only one",
            trigger_pattern="single",
            action_sequence=[{"action": "test"}],
        )

        result = await procedural_memory.compose_skills(
            skill_ids=[skill.id],
            name="Should Fail",
            description="Not enough skills",
        )

        assert result is None

    def test_get_all_skills(self, procedural_memory):
        """Test getting all skills."""
        skills = procedural_memory.get_all_skills()
        assert isinstance(skills, list)

    def test_get_skill_not_found(self, procedural_memory):
        """Test getting non-existent skill."""
        skill = procedural_memory.get_skill("nonexistent-id")
        assert skill is None

    @pytest.mark.asyncio
    async def test_get_best_skill_for_action(self, procedural_memory):
        """Test getting best skill for action."""
        skill = await procedural_memory.get_best_skill_for_action("test action")
        # May or may not find a skill depending on similarity
        assert skill is None or isinstance(skill, Skill)
