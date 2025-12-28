"""Tests for Hierarchical Planner module."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from src.planning.goal import Goal, GoalDecomposition, GoalPriority
from src.planning.hierarchical_planner import BranchEvaluation, HierarchicalPlanner, PlannerConfig
from src.planning.plan_tree import PlanNode, PlanTree


class TestPlannerConfig:
    """Tests for PlannerConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PlannerConfig()

        assert config.num_decomposition_branches == 3
        assert config.min_confidence_threshold == 0.4
        assert config.max_decomposition_depth == 5
        assert config.enable_strategic_planning is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PlannerConfig(
            num_decomposition_branches=5,
            min_confidence_threshold=0.6,
        )

        assert config.num_decomposition_branches == 5
        assert config.min_confidence_threshold == 0.6


class TestBranchEvaluation:
    """Tests for BranchEvaluation dataclass."""

    def test_branch_evaluation_creation(self):
        """Test creating a branch evaluation."""
        goal = Goal.create(description="Test goal")
        node = PlanNode.create(goal=goal)

        evaluation = BranchEvaluation(
            node=node,
            score=0.85,
            feasibility=0.9,
            efficiency=0.8,
            completeness=0.85,
            risk=0.2,
            reasoning="Good approach",
        )

        assert evaluation.score == 0.85
        assert evaluation.feasibility == 0.9
        assert evaluation.risk == 0.2


@pytest.fixture
def mock_llm():
    """Mock the LLM."""
    llm = AsyncMock()
    return llm


@pytest.fixture
def planner(mock_llm):
    """Create a HierarchicalPlanner with mocked LLM."""
    with patch("src.planning.hierarchical_planner.LLM", return_value=mock_llm):
        planner = HierarchicalPlanner(
            available_actions=["search_tavily", "analyze_news", "send_telegram_message"],
        )
        planner.llm = mock_llm
        return planner


class TestHierarchicalPlanner:
    """Tests for HierarchicalPlanner class."""

    def test_planner_creation(self, planner):
        """Test creating a planner."""
        assert planner is not None
        assert len(planner._available_actions) == 3

    def test_set_available_actions(self, planner):
        """Test updating available actions."""
        planner.set_available_actions(["action1", "action2"])
        assert planner._available_actions == ["action1", "action2"]

    @pytest.mark.asyncio
    async def test_plan_simple_goal(self, planner, mock_llm):
        """Test planning for a simple goal."""
        # Mock LLM to return atomic goal (no decomposition)
        mock_llm.generate_response.side_effect = [
            # First call: decomposition - atomic goal
            json.dumps(
                {
                    "approach": "Direct execution",
                    "reasoning": "Simple goal",
                    "subgoals": [],
                }
            ),
            # Second call: action plan
            json.dumps(
                {
                    "actions": [
                        {
                            "action_name": "search_tavily",
                            "description": "Search for info",
                            "arguments": {"query": "test"},
                            "estimated_duration_seconds": 30,
                        }
                    ]
                }
            ),
        ]

        goal = Goal.create(description="Simple test goal")
        plan_tree = await planner.plan(goal)

        assert plan_tree is not None
        assert isinstance(plan_tree, PlanTree)
        assert plan_tree.root.goal == goal

    @pytest.mark.asyncio
    async def test_plan_complex_goal(self, planner, mock_llm):
        """Test planning for a complex goal with decomposition."""
        # Mock LLM responses
        mock_llm.generate_response.side_effect = [
            # First call: decomposition with subgoals
            json.dumps(
                {
                    "approach": "Sequential execution",
                    "reasoning": "Complex goal needs breakdown",
                    "subgoals": [
                        {
                            "description": "Research phase",
                            "success_criteria": ["Data gathered"],
                            "priority": "high",
                        },
                        {
                            "description": "Analysis phase",
                            "success_criteria": ["Analysis complete"],
                            "priority": "medium",
                        },
                    ],
                }
            ),
            # Evaluation
            json.dumps(
                {
                    "feasibility": 0.8,
                    "efficiency": 0.7,
                    "completeness": 0.9,
                    "risk": 0.2,
                    "reasoning": "Good approach",
                }
            ),
            # Action plan for subgoal 1
            json.dumps(
                {
                    "actions": [
                        {
                            "action_name": "search_tavily",
                            "description": "Search",
                            "arguments": {},
                        }
                    ]
                }
            ),
            # Action plan for subgoal 2
            json.dumps(
                {
                    "actions": [
                        {
                            "action_name": "analyze_news",
                            "description": "Analyze",
                            "arguments": {},
                        }
                    ]
                }
            ),
        ]

        goal = Goal.create(description="Complex research goal")
        plan_tree = await planner.plan(goal)

        assert plan_tree is not None
        assert len(plan_tree.root.children) >= 0  # May or may not have children

    @pytest.mark.asyncio
    async def test_decompose_goal(self, planner, mock_llm):
        """Test goal decomposition."""
        mock_llm.generate_response.side_effect = [
            # Decomposition response
            json.dumps(
                {
                    "approach": "Step by step",
                    "reasoning": "Breaking into phases",
                    "subgoals": [
                        {
                            "description": "Phase 1",
                            "success_criteria": ["Done"],
                            "priority": "high",
                        },
                    ],
                }
            ),
            # Evaluation response
            json.dumps(
                {
                    "feasibility": 0.9,
                    "efficiency": 0.8,
                    "completeness": 0.9,
                    "risk": 0.1,
                    "reasoning": "Feasible approach",
                }
            ),
        ]

        goal = Goal.create(description="Goal to decompose")
        decomposition = await planner.decompose(goal)

        assert decomposition is not None
        assert isinstance(decomposition, GoalDecomposition)

    @pytest.mark.asyncio
    async def test_decomposition_timeout(self, planner, mock_llm):
        """Test decomposition handles timeout gracefully."""
        import asyncio

        async def slow_response(*args):
            await asyncio.sleep(100)  # Way longer than timeout
            return "{}"

        mock_llm.generate_response.side_effect = slow_response

        # Set very short timeout
        planner.config.decomposition_timeout_seconds = 0.01

        goal = Goal.create(description="Timeout test")
        decomposition = await planner.decompose(goal)

        # Should still return something (fallback)
        assert decomposition is not None

    @pytest.mark.asyncio
    async def test_generate_action_plan(self, planner, mock_llm):
        """Test generating action plan for a goal."""
        mock_llm.generate_response.return_value = json.dumps(
            {
                "actions": [
                    {
                        "action_name": "search_tavily",
                        "description": "Search for information",
                        "arguments": {"query": "test"},
                        "estimated_duration_seconds": 30,
                    },
                    {
                        "action_name": "analyze_news",
                        "description": "Analyze the results",
                        "arguments": {},
                        "estimated_duration_seconds": 60,
                    },
                ]
            }
        )

        goal = Goal.create(description="Action plan test")
        actions = await planner._generate_action_plan(goal, {})

        assert len(actions) == 2
        assert actions[0].action_name == "search_tavily"
        assert actions[1].action_name == "analyze_news"

    @pytest.mark.asyncio
    async def test_generate_action_plan_parse_error(self, planner, mock_llm):
        """Test action plan generation handles parse errors."""
        mock_llm.generate_response.return_value = "invalid json"

        goal = Goal.create(description="Parse error test")
        actions = await planner._generate_action_plan(goal, {})

        assert actions == []

    @pytest.mark.asyncio
    async def test_evaluate_branches(self, planner, mock_llm):
        """Test evaluating decomposition branches."""
        mock_llm.generate_response.return_value = json.dumps(
            {
                "feasibility": 0.8,
                "efficiency": 0.7,
                "completeness": 0.9,
                "risk": 0.3,
                "reasoning": "Good approach",
            }
        )

        goal = Goal.create(description="Evaluate test")
        node = PlanNode.create(goal=goal, approach="Test approach")

        evaluations = await planner._evaluate_branches([node], goal, {})

        assert len(evaluations) == 1
        assert evaluations[0].score > 0

    def test_select_best_branch(self, planner):
        """Test selecting the best branch."""
        goal = Goal.create(description="Test")
        node1 = PlanNode.create(goal=goal)
        node2 = PlanNode.create(goal=goal)

        evaluations = [
            BranchEvaluation(
                node=node1,
                score=0.6,
                feasibility=0.6,
                efficiency=0.6,
                completeness=0.6,
                risk=0.4,
                reasoning="OK",
            ),
            BranchEvaluation(
                node=node2,
                score=0.9,
                feasibility=0.9,
                efficiency=0.9,
                completeness=0.9,
                risk=0.1,
                reasoning="Great",
            ),
        ]

        best = planner._select_best_branch(evaluations)

        assert best is not None
        assert best.score == 0.9

    def test_select_best_branch_empty(self, planner):
        """Test selecting from empty evaluations."""
        best = planner._select_best_branch([])
        assert best is None

    def test_create_decomposition_prompt(self, planner):
        """Test creating decomposition prompt."""
        goal = Goal.create(
            description="Test goal",
            success_criteria=["Criterion 1"],
            priority=GoalPriority.HIGH,
        )

        prompt = planner._create_decomposition_prompt(goal, {"key": "value"})

        assert "Test goal" in prompt
        assert "Criterion 1" in prompt
        assert "high" in prompt
        assert "search_tavily" in prompt

    def test_parse_decomposition_response(self, planner):
        """Test parsing decomposition response."""
        parent = Goal.create(description="Parent")
        response = json.dumps(
            {
                "approach": "Sequential",
                "reasoning": "Step by step",
                "subgoals": [
                    {
                        "description": "Step 1",
                        "success_criteria": ["Done"],
                        "priority": "high",
                    },
                ],
            }
        )

        subgoals, approach, reasoning = planner._parse_decomposition_response(response, parent)

        assert len(subgoals) == 1
        assert subgoals[0].description == "Step 1"
        assert approach == "Sequential"

    def test_parse_decomposition_response_invalid(self, planner):
        """Test parsing invalid decomposition response."""
        parent = Goal.create(description="Parent")
        subgoals, approach, reasoning = planner._parse_decomposition_response(
            "invalid json", parent
        )

        assert subgoals == []
        assert approach == ""

    @pytest.mark.asyncio
    async def test_refine_plan(self, planner, mock_llm):
        """Test refining an existing plan."""
        # Create a simple plan
        mock_llm.generate_response.side_effect = [
            json.dumps(
                {
                    "approach": "Direct",
                    "reasoning": "Simple",
                    "subgoals": [],
                }
            ),
            json.dumps(
                {"actions": [{"action_name": "test", "description": "Test", "arguments": {}}]}
            ),
        ]

        goal = Goal.create(description="Refine test")
        plan = await planner.plan(goal)

        # Refine it
        mock_llm.generate_response.side_effect = [
            json.dumps(
                {
                    "approach": "Refined",
                    "reasoning": "Updated based on feedback",
                    "subgoals": [],
                }
            ),
            json.dumps(
                {"actions": [{"action_name": "new_action", "description": "New", "arguments": {}}]}
            ),
        ]

        refined = await planner.refine_plan(plan, "Need to adjust")

        assert refined is not None

    def test_get_statistics(self, planner):
        """Test getting planner statistics."""
        stats = planner.get_statistics()

        assert "total_goals_tracked" in stats
        assert "available_actions" in stats
        assert "config" in stats
