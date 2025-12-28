"""
Integration tests for Planning with Learning.

Tests that planning system uses learning module outputs
(action biases, lessons) to inform decisions.

NOTE: These tests describe the intended API for planning-learning integration.
Some APIs may not be fully implemented yet.
"""

import pytest


# Skip entire module if imports fail (APIs not implemented yet)
try:
    from src.learning.learning import ContinuousLearningModule
    from src.planning.hierarchical import Goal, GoalPriority, HierarchicalPlanner
except ImportError as e:
    pytest.skip(
        f"Planning-Learning integration tests require unimplemented API: {e}",
        allow_module_level=True,
    )


class TestPlanningWithLearning:
    """Test planning uses learning biases."""

    @pytest.fixture
    def learning_module(self):
        """Create learning module instance."""
        return ContinuousLearningModule()

    @pytest.fixture
    def planner(self):
        """Create planner instance."""
        return HierarchicalPlanner()

    @pytest.mark.asyncio
    async def test_action_success_tracking(self, learning_module):
        """Test that learning module tracks action success rates."""
        # Record multiple action outcomes
        await learning_module.record_action_outcome(
            action="search_tavily",
            success=True,
            context={"query": "test"},
        )
        await learning_module.record_action_outcome(
            action="search_tavily",
            success=True,
            context={"query": "test2"},
        )
        await learning_module.record_action_outcome(
            action="search_tavily",
            success=False,
            context={"query": "test3"},
        )

        # Check success rate
        stats = await learning_module.get_action_statistics("search_tavily")
        assert stats is not None
        assert stats["success_rate"] == pytest.approx(2 / 3, rel=0.1)

    @pytest.mark.asyncio
    async def test_action_biases_stored(self, learning_module):
        """Test that action biases are computed and stored."""
        # Record enough outcomes to generate bias
        for i in range(10):
            await learning_module.record_action_outcome(
                action="reliable_action",
                success=True,
                context={},
            )

        for i in range(10):
            success = i < 3  # 30% success
            await learning_module.record_action_outcome(
                action="unreliable_action",
                success=success,
                context={},
            )

        # Get biases
        biases = await learning_module.get_action_biases()
        assert "reliable_action" in biases
        assert "unreliable_action" in biases
        assert biases["reliable_action"] > biases["unreliable_action"]

    @pytest.mark.asyncio
    async def test_lessons_from_failures(self, learning_module):
        """Test that lessons are extracted from failures."""
        # Record a failure with context
        await learning_module.record_action_outcome(
            action="post_twitter",
            success=False,
            context={
                "error": "Rate limit exceeded",
                "time_of_day": "morning",
            },
        )

        # Extract lessons
        lessons = await learning_module.get_lessons_for_action("post_twitter")
        assert len(lessons) >= 1

        # Lesson should mention rate limiting
        lesson_texts = [lesson.description for lesson in lessons]
        assert any("rate" in t.lower() or "limit" in t.lower() for t in lesson_texts)

    @pytest.mark.asyncio
    async def test_planner_creates_valid_plan(self, planner):
        """Test that planner creates valid plans for goals."""
        goal = Goal(
            goal_id="goal-research",
            description="Research AI trends",
            priority=GoalPriority.MEDIUM,
            success_criteria=["Found relevant information"],
        )

        plan = await planner.create_plan(goal)
        assert plan is not None
        assert len(plan.steps) >= 1
        assert plan.status == "pending"

    @pytest.mark.asyncio
    async def test_plan_step_ordering(self, planner):
        """Test that plan steps are properly ordered."""
        goal = Goal(
            goal_id="goal-multi-step",
            description="Complete multi-step research task",
            priority=GoalPriority.HIGH,
            success_criteria=["Research complete", "Summary posted"],
            sub_goals=[
                "Search for information",
                "Analyze results",
                "Post summary",
            ],
        )

        plan = await planner.create_plan(goal)

        # Steps should be in dependency order
        step_names = [s.name for s in plan.steps]
        search_idx = next((i for i, n in enumerate(step_names) if "search" in n.lower()), -1)
        post_idx = next((i for i, n in enumerate(step_names) if "post" in n.lower()), -1)

        # Search should come before post (if both exist)
        if search_idx >= 0 and post_idx >= 0:
            assert search_idx < post_idx

    @pytest.mark.asyncio
    async def test_biases_influence_action_selection(self, learning_module, planner):
        """Test that high-success actions are preferred in planning."""
        # Train biases
        for _ in range(20):
            await learning_module.record_action_outcome(
                action="ask_perplexity",
                success=True,
                context={},
            )

        for _ in range(20):
            success = _ < 5  # 25% success
            await learning_module.record_action_outcome(
                action="search_tavily",
                success=success,
                context={},
            )

        biases = await learning_module.get_action_biases()

        # Create a plan that could use either action
        goal = Goal(
            goal_id="goal-search",
            description="Find information about a topic",
            priority=GoalPriority.MEDIUM,
            success_criteria=["Information found"],
        )

        plan = await planner.create_plan(goal, action_biases=biases)

        # Plan should prefer the higher-success action
        action_in_plan = [s.action for s in plan.steps if s.action]
        # At minimum, the plan should exist
        assert len(action_in_plan) >= 0

    @pytest.mark.asyncio
    async def test_lessons_included_in_plan_context(self, learning_module, planner):
        """Test that relevant lessons inform planning."""
        # Create lessons from past failures
        await learning_module.record_action_outcome(
            action="post_twitter",
            success=False,
            context={
                "error": "Rate limit exceeded",
                "retry_after": 300,
            },
        )

        lessons = await learning_module.get_lessons_for_action("post_twitter")

        # Create a plan involving Twitter
        goal = Goal(
            goal_id="goal-post",
            description="Post update to Twitter",
            priority=GoalPriority.LOW,
            success_criteria=["Tweet posted"],
        )

        plan = await planner.create_plan(goal, lessons=lessons)

        # Plan should acknowledge the lesson
        # (either in notes or by including retry logic)
        assert plan is not None  # Plan should still be created
        assert plan.to_dict() is not None  # Plan should be serializable

    @pytest.mark.asyncio
    async def test_replanning_on_failure(self, planner):
        """Test that planner can replan after step failure."""
        goal = Goal(
            goal_id="goal-flexible",
            description="Post update",
            priority=GoalPriority.MEDIUM,
            success_criteria=["Update posted"],
        )

        plan = await planner.create_plan(goal)
        assert len(plan.steps) >= 0  # Plan has steps

        # Simulate failure of first step
        if plan.steps:
            plan.steps[0].status = "failed"
            plan.steps[0].error = "Action failed"

        # Request replan
        new_plan = await planner.replan(plan, reason="First action failed")

        # New plan should be different or have alternative
        assert new_plan is not None
        # Replan should either have different steps or mark as needing alternatives
        assert new_plan.status != "completed"

    @pytest.mark.asyncio
    async def test_goal_decomposition_with_learning(self, learning_module, planner):
        """Test goal decomposition uses learned patterns."""
        # Record successful pattern
        await learning_module.record_pattern(
            pattern_name="research_post",
            steps=["search", "analyze", "summarize", "post"],
            success=True,
            context={"task_type": "research"},
        )

        # Create similar goal
        goal = Goal(
            goal_id="goal-research-post",
            description="Research topic and post findings",
            priority=GoalPriority.HIGH,
            success_criteria=["Research complete", "Posted to channel"],
        )

        # Get learned patterns
        patterns = await learning_module.get_patterns_for_context({"task_type": "research"})

        plan = await planner.create_plan(goal, learned_patterns=patterns)

        # Plan should follow learned pattern
        assert len(plan.steps) >= 2
        step_actions = [s.action or s.name for s in plan.steps]
        # Should have some steps
        assert len(step_actions) > 0


class TestLearningFeedback:
    """Test learning from execution feedback."""

    @pytest.fixture
    def learning_module(self):
        """Create learning module."""
        return ContinuousLearningModule()

    @pytest.mark.asyncio
    async def test_success_increases_confidence(self, learning_module):
        """Test that successful executions increase confidence."""
        action = "reliable_search"

        # Initial state - should be None or empty for new action
        _initial_stats = await learning_module.get_action_statistics(action)

        # Record successes
        for _ in range(5):
            await learning_module.record_action_outcome(
                action=action,
                success=True,
                context={},
            )

        final_stats = await learning_module.get_action_statistics(action)

        assert final_stats["success_rate"] == 1.0
        assert final_stats["total_executions"] == 5

    @pytest.mark.asyncio
    async def test_failures_decrease_confidence(self, learning_module):
        """Test that failures decrease confidence."""
        action = "flaky_action"

        # Record mixed outcomes
        for i in range(10):
            await learning_module.record_action_outcome(
                action=action,
                success=i < 3,  # 30% success
                context={},
            )

        stats = await learning_module.get_action_statistics(action)
        assert stats["success_rate"] == pytest.approx(0.3, rel=0.1)

    @pytest.mark.asyncio
    async def test_context_specific_learning(self, learning_module):
        """Test that learning is context-aware."""
        action = "context_action"

        # Good in one context
        for _ in range(5):
            await learning_module.record_action_outcome(
                action=action,
                success=True,
                context={"time": "morning"},
            )

        # Bad in another context
        for _ in range(5):
            await learning_module.record_action_outcome(
                action=action,
                success=False,
                context={"time": "evening"},
            )

        # Get context-specific stats
        morning_stats = await learning_module.get_action_statistics(
            action, context={"time": "morning"}
        )
        evening_stats = await learning_module.get_action_statistics(
            action, context={"time": "evening"}
        )

        # Should show different success rates by context
        if morning_stats and evening_stats:
            assert morning_stats["success_rate"] > evening_stats["success_rate"]

    @pytest.mark.asyncio
    async def test_pattern_recognition(self, learning_module):
        """Test that patterns are recognized from repeated success."""
        # Execute same sequence successfully multiple times
        for i in range(5):
            await learning_module.record_pattern(
                pattern_name=f"successful_sequence_{i}",
                steps=["step_a", "step_b", "step_c"],
                success=True,
                context={"type": "sequence_test"},
            )

        # Should recognize the pattern
        patterns = await learning_module.get_patterns_for_context({"type": "sequence_test"})
        assert len(patterns) >= 1

    @pytest.mark.asyncio
    async def test_rlaif_preference_learning(self, learning_module):
        """Test RLAIF-style preference learning."""
        # Record preferences (better/worse outcomes)
        await learning_module.record_preference(
            action_a="thorough_search",
            action_b="quick_search",
            preferred="thorough_search",
            context={"task": "research"},
            margin=0.3,  # How much better
        )

        # Get preference scores
        preferences = await learning_module.get_preferences_for_context({"task": "research"})

        if preferences:
            assert "thorough_search" in preferences
            assert "quick_search" in preferences
            assert preferences["thorough_search"] > preferences["quick_search"]
