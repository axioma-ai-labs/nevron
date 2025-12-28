"""Hierarchical Planner with Tree of Thoughts reasoning.

Implements three-level planning (strategic, tactical, operational)
and Tree of Thoughts decomposition for complex goals.
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.llm.llm import LLM
from src.planning.goal import Goal, GoalDecomposition, GoalPriority, GoalRegistry
from src.planning.plan_tree import ActionStep, PlanNode, PlanTree


@dataclass
class BranchEvaluation:
    """Evaluation result for a plan branch."""

    node: PlanNode
    score: float  # Overall score (0.0 to 1.0)
    feasibility: float  # How achievable is this branch
    efficiency: float  # How resource-efficient
    completeness: float  # How well does it address the goal
    risk: float  # Risk level (lower is better)
    reasoning: str  # Explanation of the evaluation


@dataclass
class PlannerConfig:
    """Configuration for the hierarchical planner."""

    # Tree of Thoughts settings
    num_decomposition_branches: int = 3  # Number of parallel decomposition approaches
    min_confidence_threshold: float = 0.4  # Minimum confidence to proceed
    max_decomposition_depth: int = 5  # Maximum depth of goal decomposition

    # Planning levels
    enable_strategic_planning: bool = True
    enable_tactical_planning: bool = True
    enable_operational_planning: bool = True

    # Timeouts
    decomposition_timeout_seconds: float = 30.0
    evaluation_timeout_seconds: float = 15.0

    # Retry settings
    max_planning_retries: int = 3


class HierarchicalPlanner:
    """Three-level hierarchical planner with Tree of Thoughts.

    Planning levels:
    - Strategic: Long-term goals (days/weeks)
    - Tactical: Sub-goals (hours)
    - Operational: Immediate actions (minutes)
    """

    def __init__(
        self,
        config: Optional[PlannerConfig] = None,
        available_actions: Optional[List[str]] = None,
    ):
        """Initialize the hierarchical planner.

        Args:
            config: Planner configuration
            available_actions: List of available action names
        """
        self.config = config or PlannerConfig()
        self.llm = LLM()
        self.goal_registry = GoalRegistry()
        self._available_actions = available_actions or []

    def set_available_actions(self, actions: List[str]) -> None:
        """Update the list of available actions.

        Args:
            actions: List of action names
        """
        self._available_actions = actions

    async def plan(self, goal: Goal, context: Optional[Dict[str, Any]] = None) -> PlanTree:
        """Create a hierarchical plan for a goal.

        Args:
            goal: The goal to plan for
            context: Optional context information

        Returns:
            PlanTree with the complete plan
        """
        context = context or {}
        logger.info(f"Planning for goal: {goal.description}")

        # Register the goal
        self.goal_registry.add(goal)
        goal.start()

        # Decompose the goal using Tree of Thoughts
        decomposition = await self.decompose(goal, context)

        # Create root plan node
        root = PlanNode.create(
            goal=goal,
            confidence=decomposition.confidence,
            approach=decomposition.approach,
            reasoning=decomposition.reasoning,
        )

        # Add subgoals as children
        for subgoal in decomposition.subgoals:
            self.goal_registry.add(subgoal)
            subgoal_actions = await self._generate_action_plan(subgoal, context)
            child = PlanNode.create(
                goal=subgoal,
                actions=subgoal_actions,
                parent=root,
                confidence=decomposition.confidence,
            )
            root.add_child(child)

        # If no subgoals, generate actions for the root goal directly
        if not decomposition.subgoals:
            root.actions = await self._generate_action_plan(goal, context)
            root.estimated_steps = len(root.actions)

        # Create and return the plan tree
        plan_tree = PlanTree(root)
        logger.info(f"Created plan with {plan_tree.total_steps} steps")
        return plan_tree

    async def decompose(
        self, goal: Goal, context: Optional[Dict[str, Any]] = None
    ) -> GoalDecomposition:
        """Decompose a goal into sub-goals using Tree of Thoughts.

        Generates multiple decomposition approaches, evaluates each,
        and selects the best one.

        Args:
            goal: Goal to decompose
            context: Optional context information

        Returns:
            GoalDecomposition with selected sub-goals
        """
        context = context or {}
        logger.debug(f"Decomposing goal: {goal.description}")

        # Generate multiple decomposition branches
        try:
            branches = await asyncio.wait_for(
                self._generate_decomposition_branches(goal, context),
                timeout=self.config.decomposition_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("Decomposition timed out, using simple approach")
            branches = await self._generate_simple_decomposition(goal, context)

        if not branches:
            # No decomposition needed - goal is atomic
            return GoalDecomposition(
                original_goal=goal,
                subgoals=[],
                reasoning="Goal is atomic and does not require decomposition",
                confidence=0.8,
                approach="Direct execution",
            )

        # Evaluate branches
        evaluations = await self._evaluate_branches(branches, goal, context)

        # Select best branch
        best = self._select_best_branch(evaluations)

        if best is None:
            logger.warning("No suitable decomposition found")
            return GoalDecomposition(
                original_goal=goal,
                subgoals=[],
                reasoning="Could not find a suitable decomposition approach",
                confidence=0.5,
                approach="Fallback to direct execution",
            )

        logger.info(f"Selected decomposition with confidence {best.score:.2f}")

        return GoalDecomposition(
            original_goal=goal,
            subgoals=[child.goal for child in best.node.children],
            reasoning=best.reasoning,
            confidence=best.score,
            approach=best.node.approach,
        )

    async def _generate_decomposition_branches(
        self, goal: Goal, context: Dict[str, Any]
    ) -> List[PlanNode]:
        """Generate multiple decomposition approaches in parallel.

        Args:
            goal: Goal to decompose
            context: Context information

        Returns:
            List of plan nodes representing different approaches
        """
        prompt = self._create_decomposition_prompt(goal, context)

        # Generate N different approaches
        branches: List[PlanNode] = []
        tasks = [
            self._generate_single_decomposition(goal, prompt, i)
            for i in range(self.config.num_decomposition_branches)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, BaseException):
                logger.error(f"Decomposition branch failed: {result}")
                continue
            if result is not None:
                branches.append(result)

        return branches

    async def _generate_single_decomposition(
        self, goal: Goal, prompt: str, branch_id: int
    ) -> Optional[PlanNode]:
        """Generate a single decomposition approach.

        Args:
            goal: Goal to decompose
            prompt: Decomposition prompt
            branch_id: Branch identifier for variation

        Returns:
            PlanNode with subgoals, or None if failed
        """
        # Add variation to prompt
        variation_prompt = f"""{prompt}

Approach variation: {branch_id + 1} of {self.config.num_decomposition_branches}
Try a different strategy than other approaches. Be creative but practical."""

        try:
            messages = [{"role": "user", "content": variation_prompt}]
            response = await self.llm.generate_response(messages)

            # Parse the response
            subgoals, approach, reasoning = self._parse_decomposition_response(response, goal)

            if not subgoals:
                return None

            # Create plan node with subgoals
            node = PlanNode.create(
                goal=goal,
                approach=approach,
                reasoning=reasoning,
            )

            for subgoal in subgoals:
                child = PlanNode.create(goal=subgoal, parent=node)
                node.add_child(child)

            return node

        except Exception as e:
            logger.error(f"Failed to generate decomposition branch {branch_id}: {e}")
            return None

    async def _generate_simple_decomposition(
        self, goal: Goal, context: Dict[str, Any]
    ) -> List[PlanNode]:
        """Generate a simple single decomposition (fallback).

        Args:
            goal: Goal to decompose
            context: Context information

        Returns:
            List with a single decomposition node
        """
        prompt = self._create_decomposition_prompt(goal, context)

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.generate_response(messages)
            subgoals, approach, reasoning = self._parse_decomposition_response(response, goal)

            if not subgoals:
                return []

            node = PlanNode.create(goal=goal, approach=approach, reasoning=reasoning)
            for subgoal in subgoals:
                child = PlanNode.create(goal=subgoal, parent=node)
                node.add_child(child)

            return [node]

        except Exception as e:
            logger.error(f"Simple decomposition failed: {e}")
            return []

    def _create_decomposition_prompt(self, goal: Goal, context: Dict[str, Any]) -> str:
        """Create prompt for goal decomposition.

        Args:
            goal: Goal to decompose
            context: Context information

        Returns:
            Prompt string
        """
        available_actions_str = (
            ", ".join(self._available_actions) if self._available_actions else "various actions"
        )

        context_str = ""
        if context:
            context_str = f"\nContext:\n{json.dumps(context, indent=2, default=str)}"

        success_criteria_str = (
            "\n".join(f"- {c}" for c in goal.success_criteria)
            if goal.success_criteria
            else "- Goal is achieved successfully"
        )

        return f"""Decompose the following goal into smaller, actionable sub-goals.

Goal: {goal.description}

Success Criteria:
{success_criteria_str}

Priority: {goal.priority.value}
{context_str}

Available Actions: {available_actions_str}

Instructions:
1. Break down the goal into 2-5 concrete sub-goals
2. Each sub-goal should be achievable with the available actions
3. Sub-goals should be in logical execution order
4. Consider dependencies between sub-goals

Respond in the following JSON format:
{{
    "approach": "Brief description of your decomposition approach",
    "reasoning": "Why this decomposition makes sense",
    "subgoals": [
        {{
            "description": "Sub-goal description",
            "success_criteria": ["Criterion 1", "Criterion 2"],
            "priority": "medium"
        }}
    ]
}}

If the goal is simple enough to execute directly (atomic goal), respond with:
{{
    "approach": "Direct execution",
    "reasoning": "Goal is atomic and can be executed directly",
    "subgoals": []
}}

Respond with ONLY valid JSON, nothing else."""

    def _parse_decomposition_response(
        self, response: str, parent_goal: Goal
    ) -> Tuple[List[Goal], str, str]:
        """Parse LLM response into subgoals.

        Args:
            response: LLM response string
            parent_goal: Parent goal for context

        Returns:
            Tuple of (subgoals, approach, reasoning)
        """
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response)

            approach = data.get("approach", "")
            reasoning = data.get("reasoning", "")
            subgoals_data = data.get("subgoals", [])

            subgoals = []
            for i, sg_data in enumerate(subgoals_data):
                priority_str = sg_data.get("priority", "medium")
                try:
                    priority = GoalPriority(priority_str)
                except ValueError:
                    priority = GoalPriority.MEDIUM

                subgoal = Goal.create(
                    description=sg_data.get("description", f"Subgoal {i + 1}"),
                    success_criteria=sg_data.get("success_criteria", []),
                    priority=priority,
                    parent_id=parent_goal.id,
                )
                subgoals.append(subgoal)

            return subgoals, approach, reasoning

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse decomposition response: {e}")
            return [], "", ""

    async def _evaluate_branches(
        self, branches: List[PlanNode], goal: Goal, context: Dict[str, Any]
    ) -> List[BranchEvaluation]:
        """Evaluate decomposition branches.

        Args:
            branches: List of plan nodes to evaluate
            goal: Original goal
            context: Context information

        Returns:
            List of evaluations
        """
        tasks = [self._evaluate_branch(branch, goal, context) for branch in branches]

        try:
            evaluations = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=self.config.evaluation_timeout_seconds,
            )
        except asyncio.TimeoutError:
            logger.warning("Branch evaluation timed out")
            # Return default evaluations
            return [
                BranchEvaluation(
                    node=branch,
                    score=0.5,
                    feasibility=0.5,
                    efficiency=0.5,
                    completeness=0.5,
                    risk=0.5,
                    reasoning="Evaluation timed out",
                )
                for branch in branches
            ]

        results: List[BranchEvaluation] = []
        for eval_result, branch in zip(evaluations, branches):
            if isinstance(eval_result, BaseException):
                logger.error(f"Evaluation failed: {eval_result}")
                results.append(
                    BranchEvaluation(
                        node=branch,
                        score=0.3,
                        feasibility=0.3,
                        efficiency=0.5,
                        completeness=0.3,
                        risk=0.7,
                        reasoning=f"Evaluation error: {eval_result}",
                    )
                )
            else:
                results.append(eval_result)

        return results

    async def _evaluate_branch(
        self, branch: PlanNode, goal: Goal, context: Dict[str, Any]
    ) -> BranchEvaluation:
        """Evaluate a single decomposition branch.

        Args:
            branch: Plan node to evaluate
            goal: Original goal
            context: Context information

        Returns:
            Branch evaluation
        """
        subgoals_str = "\n".join(f"- {child.goal.description}" for child in branch.children)

        prompt = f"""Evaluate the following goal decomposition:

Original Goal: {goal.description}

Decomposition Approach: {branch.approach}
Reasoning: {branch.reasoning}

Sub-goals:
{subgoals_str if subgoals_str else "(No sub-goals - direct execution)"}

Evaluate this decomposition on a scale of 0.0 to 1.0 for each criterion:

Respond in JSON format:
{{
    "feasibility": 0.8,
    "efficiency": 0.7,
    "completeness": 0.9,
    "risk": 0.3,
    "reasoning": "Brief explanation of the evaluation"
}}

Respond with ONLY valid JSON, nothing else."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.generate_response(messages)

            # Parse response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response)

            feasibility = float(data.get("feasibility", 0.5))
            efficiency = float(data.get("efficiency", 0.5))
            completeness = float(data.get("completeness", 0.5))
            risk = float(data.get("risk", 0.5))
            reasoning = data.get("reasoning", "")

            # Calculate overall score
            score = (feasibility + efficiency + completeness + (1 - risk)) / 4

            return BranchEvaluation(
                node=branch,
                score=score,
                feasibility=feasibility,
                efficiency=efficiency,
                completeness=completeness,
                risk=risk,
                reasoning=reasoning,
            )

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse evaluation: {e}")
            return BranchEvaluation(
                node=branch,
                score=0.5,
                feasibility=0.5,
                efficiency=0.5,
                completeness=0.5,
                risk=0.5,
                reasoning="Failed to evaluate",
            )

    def _select_best_branch(
        self, evaluations: List[BranchEvaluation]
    ) -> Optional[BranchEvaluation]:
        """Select the best branch based on evaluations.

        Args:
            evaluations: List of branch evaluations

        Returns:
            Best evaluation, or None if none meet threshold
        """
        if not evaluations:
            return None

        # Filter by minimum confidence
        valid = [e for e in evaluations if e.score >= self.config.min_confidence_threshold]

        if not valid:
            # Take best of what we have
            valid = evaluations

        # Sort by score descending
        valid.sort(key=lambda e: e.score, reverse=True)

        return valid[0]

    async def _generate_action_plan(self, goal: Goal, context: Dict[str, Any]) -> List[ActionStep]:
        """Generate an action plan for a goal.

        Args:
            goal: Goal to plan actions for
            context: Context information

        Returns:
            List of action steps
        """
        available_actions_str = "\n".join(f"- {a}" for a in self._available_actions)

        context_str = ""
        if context:
            context_str = f"\nContext:\n{json.dumps(context, indent=2, default=str)}"

        prompt = f"""Generate an action plan to achieve the following goal.

Goal: {goal.description}

Success Criteria:
{chr(10).join(f"- {c}" for c in goal.success_criteria) if goal.success_criteria else "- Goal is achieved successfully"}
{context_str}

Available Actions:
{available_actions_str if available_actions_str else "Any reasonable action"}

Generate 1-5 concrete actions to achieve this goal.

Respond in JSON format:
{{
    "actions": [
        {{
            "action_name": "action_name",
            "description": "What this action does",
            "arguments": {{}},
            "estimated_duration_seconds": 30
        }}
    ]
}}

Respond with ONLY valid JSON, nothing else."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.generate_response(messages)

            # Parse response
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]

            data = json.loads(response)
            actions_data = data.get("actions", [])

            actions = []
            for action_data in actions_data:
                action = ActionStep.create(
                    action_name=action_data.get("action_name", "unknown"),
                    arguments=action_data.get("arguments", {}),
                    description=action_data.get("description"),
                    estimated_duration_seconds=action_data.get("estimated_duration_seconds", 30.0),
                )
                actions.append(action)

            return actions

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Failed to generate action plan: {e}")
            return []

    async def refine_plan(
        self,
        plan_tree: PlanTree,
        feedback: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PlanTree:
        """Refine an existing plan based on feedback.

        Args:
            plan_tree: Current plan tree
            feedback: Feedback or observations
            context: Optional additional context

        Returns:
            Refined plan tree
        """
        context = context or {}
        context["feedback"] = feedback
        context["current_progress"] = plan_tree.progress
        context["completed_steps"] = plan_tree.completed_steps
        context["total_steps"] = plan_tree.total_steps

        # Re-plan from current node
        current_goal = plan_tree.current_node.goal

        logger.info(f"Refining plan for: {current_goal.description}")

        # Create a new plan from the current goal
        new_plan = await self.plan(current_goal, context)

        return new_plan

    def get_statistics(self) -> Dict[str, Any]:
        """Get planner statistics.

        Returns:
            Dictionary with planner statistics
        """
        return {
            "total_goals_tracked": len(self.goal_registry),
            "active_goals": len(self.goal_registry.get_active()),
            "pending_goals": len(self.goal_registry.get_pending()),
            "available_actions": len(self._available_actions),
            "config": {
                "num_decomposition_branches": self.config.num_decomposition_branches,
                "min_confidence_threshold": self.config.min_confidence_threshold,
                "max_decomposition_depth": self.config.max_decomposition_depth,
            },
        }
