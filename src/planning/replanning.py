"""Replanning Engine for failure recovery.

Provides intelligent replanning when plan execution fails,
including failure analysis, alternative generation, and plan updates.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from src.llm.llm import LLM
from src.planning.goal import Goal
from src.planning.plan_tree import ActionStep, NodeStatus, PlanNode, PlanTree


class FailureType(str, Enum):
    """Types of failures that can occur during execution."""

    ACTION_ERROR = "action_error"  # Action raised an exception
    TIMEOUT = "timeout"  # Action timed out
    INVALID_RESULT = "invalid_result"  # Action returned unexpected result
    PRECONDITION_NOT_MET = "precondition_not_met"  # Prerequisites not satisfied
    RESOURCE_UNAVAILABLE = "resource_unavailable"  # Required resource not available
    RATE_LIMITED = "rate_limited"  # API rate limit hit
    PERMISSION_DENIED = "permission_denied"  # Access denied
    UNKNOWN = "unknown"  # Unknown failure type


class ReplanningStrategy(str, Enum):
    """Strategies for replanning after failure."""

    RETRY = "retry"  # Retry the same action
    SKIP = "skip"  # Skip the failed action and continue
    ALTERNATIVE = "alternative"  # Try an alternative approach
    BACKTRACK = "backtrack"  # Go back to parent goal
    ABORT = "abort"  # Abort the current plan
    WAIT_AND_RETRY = "wait_and_retry"  # Wait before retrying


@dataclass
class FailureAnalysis:
    """Analysis of a plan execution failure."""

    failure_type: FailureType
    failed_action: ActionStep
    failed_node: PlanNode
    error_message: str
    context: Dict[str, Any] = field(default_factory=dict)
    recommended_strategy: ReplanningStrategy = ReplanningStrategy.ALTERNATIVE
    can_recover: bool = True
    retry_after_seconds: Optional[float] = None
    reasoning: str = ""
    analyzed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ReplanningResult:
    """Result of a replanning operation."""

    success: bool
    strategy_used: ReplanningStrategy
    new_plan: Optional[PlanTree] = None
    alternative_nodes: List[PlanNode] = field(default_factory=list)
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ReplanningConfig:
    """Configuration for the replanning engine."""

    max_retries_per_action: int = 3
    max_alternatives: int = 3
    backtrack_limit: int = 2  # How many levels to backtrack
    retry_delay_base_seconds: float = 5.0  # Base delay for retries
    retry_delay_multiplier: float = 2.0  # Exponential backoff multiplier
    enable_llm_analysis: bool = True  # Use LLM for failure analysis


class ReplanningEngine:
    """Engine for handling plan failures and generating alternatives.

    Analyzes failures, determines recovery strategies, and
    generates alternative plan branches when needed.
    """

    def __init__(
        self,
        config: Optional[ReplanningConfig] = None,
        available_actions: Optional[List[str]] = None,
    ):
        """Initialize the replanning engine.

        Args:
            config: Replanning configuration
            available_actions: List of available action names
        """
        self.config = config or ReplanningConfig()
        self.llm = LLM()
        self._available_actions = available_actions or []
        self._failure_history: List[FailureAnalysis] = []

    def set_available_actions(self, actions: List[str]) -> None:
        """Update the list of available actions.

        Args:
            actions: List of action names
        """
        self._available_actions = actions

    async def analyze_failure(
        self,
        action: ActionStep,
        node: PlanNode,
        error: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailureAnalysis:
        """Analyze why an action failed and determine recovery strategy.

        Args:
            action: The failed action
            node: The plan node containing the action
            error: Error message from the failure
            context: Additional context information

        Returns:
            FailureAnalysis with recommended recovery strategy
        """
        context = context or {}
        logger.info(f"Analyzing failure for action: {action.action_name}")

        # Determine failure type from error message
        failure_type = self._classify_failure(error)

        # Determine if recovery is possible
        can_recover = self._can_recover(failure_type, action)

        # Calculate retry delay if applicable
        retry_count = context.get("retry_count", 0)
        retry_after = None
        if failure_type in (FailureType.RATE_LIMITED, FailureType.TIMEOUT):
            retry_after = self.config.retry_delay_base_seconds * (
                self.config.retry_delay_multiplier**retry_count
            )

        # Determine recommended strategy
        strategy = self._determine_strategy(failure_type, retry_count, can_recover)

        # Use LLM for deeper analysis if enabled
        reasoning = ""
        if self.config.enable_llm_analysis:
            reasoning = await self._llm_analyze_failure(action, node, error, failure_type)

        analysis = FailureAnalysis(
            failure_type=failure_type,
            failed_action=action,
            failed_node=node,
            error_message=error,
            context=context,
            recommended_strategy=strategy,
            can_recover=can_recover,
            retry_after_seconds=retry_after,
            reasoning=reasoning,
        )

        self._failure_history.append(analysis)
        return analysis

    def _classify_failure(self, error: str) -> FailureType:
        """Classify the type of failure from error message.

        Args:
            error: Error message string

        Returns:
            Classified failure type
        """
        error_lower = error.lower()

        if "timeout" in error_lower or "timed out" in error_lower:
            return FailureType.TIMEOUT

        if "rate limit" in error_lower or "too many requests" in error_lower:
            return FailureType.RATE_LIMITED

        if (
            "permission" in error_lower
            or "access denied" in error_lower
            or "unauthorized" in error_lower
        ):
            return FailureType.PERMISSION_DENIED

        if "not found" in error_lower or "unavailable" in error_lower:
            return FailureType.RESOURCE_UNAVAILABLE

        if "invalid" in error_lower or "unexpected" in error_lower:
            return FailureType.INVALID_RESULT

        if "precondition" in error_lower or "prerequisite" in error_lower:
            return FailureType.PRECONDITION_NOT_MET

        if "error" in error_lower or "exception" in error_lower or "failed" in error_lower:
            return FailureType.ACTION_ERROR

        return FailureType.UNKNOWN

    def _can_recover(self, failure_type: FailureType, action: ActionStep) -> bool:
        """Determine if recovery is possible for a failure.

        Args:
            failure_type: Type of failure
            action: Failed action

        Returns:
            True if recovery is possible
        """
        # Some failure types are not recoverable
        if failure_type == FailureType.PERMISSION_DENIED:
            return False

        # Check retry count
        if action.status == NodeStatus.FAILED:
            # Already failed once, may still be recoverable
            return True

        return True

    def _determine_strategy(
        self,
        failure_type: FailureType,
        retry_count: int,
        can_recover: bool,
    ) -> ReplanningStrategy:
        """Determine the best replanning strategy.

        Args:
            failure_type: Type of failure
            retry_count: Number of previous retries
            can_recover: Whether recovery is possible

        Returns:
            Recommended strategy
        """
        if not can_recover:
            return ReplanningStrategy.ABORT

        # Rate limited - wait and retry
        if failure_type == FailureType.RATE_LIMITED:
            return ReplanningStrategy.WAIT_AND_RETRY

        # Timeout - retry a few times, then try alternative
        if failure_type == FailureType.TIMEOUT:
            if retry_count < 2:
                return ReplanningStrategy.RETRY
            return ReplanningStrategy.ALTERNATIVE

        # Resource unavailable - skip or alternative
        if failure_type == FailureType.RESOURCE_UNAVAILABLE:
            return ReplanningStrategy.SKIP

        # Action error - try alternative
        if failure_type == FailureType.ACTION_ERROR:
            if retry_count < self.config.max_retries_per_action:
                return ReplanningStrategy.RETRY
            return ReplanningStrategy.ALTERNATIVE

        # Precondition not met - backtrack
        if failure_type == FailureType.PRECONDITION_NOT_MET:
            return ReplanningStrategy.BACKTRACK

        # Default: try alternative
        return ReplanningStrategy.ALTERNATIVE

    async def _llm_analyze_failure(
        self,
        action: ActionStep,
        node: PlanNode,
        error: str,
        failure_type: FailureType,
    ) -> str:
        """Use LLM to analyze failure and provide reasoning.

        Args:
            action: Failed action
            node: Plan node
            error: Error message
            failure_type: Classified failure type

        Returns:
            LLM reasoning about the failure
        """
        prompt = f"""Analyze the following action failure and provide brief reasoning:

Action: {action.action_name}
Arguments: {json.dumps(action.arguments)}
Goal: {node.goal.description}
Error: {error}
Failure Type: {failure_type.value}

Provide a brief (1-2 sentences) analysis of:
1. Why this likely failed
2. What might help recover

Respond with just the analysis, no formatting."""

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.generate_response(messages)
            return response.strip()
        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return ""

    async def generate_alternatives(
        self,
        analysis: FailureAnalysis,
        plan_tree: PlanTree,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[PlanNode]:
        """Generate alternative plan branches after failure.

        Args:
            analysis: Failure analysis
            plan_tree: Current plan tree
            context: Additional context

        Returns:
            List of alternative plan nodes
        """
        context = context or {}
        logger.info(f"Generating alternatives for: {analysis.failed_action.action_name}")

        # Get context about what failed
        failed_goal = analysis.failed_node.goal
        completed_actions = [
            a for a in analysis.failed_node.actions if a.status == NodeStatus.COMPLETED
        ]

        prompt = self._create_alternatives_prompt(
            failed_goal, analysis.failed_action, analysis.error_message, completed_actions
        )

        try:
            messages = [{"role": "user", "content": prompt}]
            response = await self.llm.generate_response(messages)

            alternatives = self._parse_alternatives_response(response, failed_goal)
            return alternatives[: self.config.max_alternatives]

        except Exception as e:
            logger.error(f"Failed to generate alternatives: {e}")
            return []

    def _create_alternatives_prompt(
        self,
        goal: Goal,
        failed_action: ActionStep,
        error: str,
        completed_actions: List[ActionStep],
    ) -> str:
        """Create prompt for generating alternative approaches.

        Args:
            goal: The goal being pursued
            failed_action: The action that failed
            error: Error message
            completed_actions: Actions already completed

        Returns:
            Prompt string
        """
        completed_str = ""
        if completed_actions:
            completed_str = "\nAlready completed:\n" + "\n".join(
                f"- {a.action_name}: {a.description or 'Done'}" for a in completed_actions
            )

        available_actions_str = "\n".join(f"- {a}" for a in self._available_actions)

        return f"""An action failed during plan execution. Generate alternative approaches.

Goal: {goal.description}

Failed Action: {failed_action.action_name}
Error: {error}
{completed_str}

Available Actions:
{available_actions_str if available_actions_str else "Any reasonable action"}

Generate 1-3 alternative approaches to achieve the goal, avoiding the failed action pattern.

Respond in JSON format:
{{
    "alternatives": [
        {{
            "approach": "Brief description of alternative approach",
            "actions": [
                {{
                    "action_name": "action_name",
                    "description": "What this action does",
                    "arguments": {{}},
                    "estimated_duration_seconds": 30
                }}
            ]
        }}
    ]
}}

Respond with ONLY valid JSON, nothing else."""

    def _parse_alternatives_response(self, response: str, goal: Goal) -> List[PlanNode]:
        """Parse LLM response into alternative plan nodes.

        Args:
            response: LLM response
            goal: Original goal

        Returns:
            List of alternative plan nodes
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
            alternatives_data = data.get("alternatives", [])

            alternatives = []
            for alt_data in alternatives_data:
                # Create a copy of the goal for this alternative
                alt_goal = Goal.create(
                    description=goal.description,
                    success_criteria=goal.success_criteria,
                    priority=goal.priority,
                    parent_id=goal.parent_id,
                    metadata={"alternative": True, "approach": alt_data.get("approach", "")},
                )

                # Create actions
                actions = []
                for action_data in alt_data.get("actions", []):
                    action = ActionStep.create(
                        action_name=action_data.get("action_name", "unknown"),
                        arguments=action_data.get("arguments", {}),
                        description=action_data.get("description"),
                        estimated_duration_seconds=action_data.get(
                            "estimated_duration_seconds", 30.0
                        ),
                    )
                    actions.append(action)

                # Create plan node
                node = PlanNode.create(
                    goal=alt_goal,
                    actions=actions,
                    approach=alt_data.get("approach", "Alternative approach"),
                )

                alternatives.append(node)

            return alternatives

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse alternatives: {e}")
            return []

    async def replan(
        self,
        plan_tree: PlanTree,
        analysis: FailureAnalysis,
        context: Optional[Dict[str, Any]] = None,
    ) -> ReplanningResult:
        """Execute a replanning operation based on failure analysis.

        Args:
            plan_tree: Current plan tree
            analysis: Failure analysis
            context: Additional context

        Returns:
            ReplanningResult with updated plan or alternatives
        """
        context = context or {}
        strategy = analysis.recommended_strategy

        logger.info(f"Replanning with strategy: {strategy.value}")

        if strategy == ReplanningStrategy.RETRY:
            return await self._handle_retry(plan_tree, analysis)

        if strategy == ReplanningStrategy.WAIT_AND_RETRY:
            return self._handle_wait_and_retry(analysis)

        if strategy == ReplanningStrategy.SKIP:
            return self._handle_skip(plan_tree, analysis)

        if strategy == ReplanningStrategy.ALTERNATIVE:
            return await self._handle_alternative(plan_tree, analysis, context)

        if strategy == ReplanningStrategy.BACKTRACK:
            return self._handle_backtrack(plan_tree, analysis)

        if strategy == ReplanningStrategy.ABORT:
            return self._handle_abort(plan_tree, analysis)

        return ReplanningResult(
            success=False,
            strategy_used=strategy,
            message="Unknown strategy",
        )

    async def _handle_retry(
        self, plan_tree: PlanTree, analysis: FailureAnalysis
    ) -> ReplanningResult:
        """Handle retry strategy.

        Args:
            plan_tree: Current plan
            analysis: Failure analysis

        Returns:
            Result with retry setup
        """
        action = analysis.failed_action

        # Reset action status for retry
        action.status = NodeStatus.PENDING
        action.error = None
        action.result = None
        action.started_at = None
        action.completed_at = None

        return ReplanningResult(
            success=True,
            strategy_used=ReplanningStrategy.RETRY,
            new_plan=plan_tree,
            message=f"Action {action.action_name} reset for retry",
        )

    def _handle_wait_and_retry(self, analysis: FailureAnalysis) -> ReplanningResult:
        """Handle wait and retry strategy.

        Args:
            analysis: Failure analysis

        Returns:
            Result with wait instructions
        """
        wait_seconds = analysis.retry_after_seconds or self.config.retry_delay_base_seconds

        return ReplanningResult(
            success=True,
            strategy_used=ReplanningStrategy.WAIT_AND_RETRY,
            message=f"Wait {wait_seconds:.1f} seconds before retry",
        )

    def _handle_skip(self, plan_tree: PlanTree, analysis: FailureAnalysis) -> ReplanningResult:
        """Handle skip strategy.

        Args:
            plan_tree: Current plan
            analysis: Failure analysis

        Returns:
            Result with action skipped
        """
        action = analysis.failed_action
        action.status = NodeStatus.SKIPPED

        return ReplanningResult(
            success=True,
            strategy_used=ReplanningStrategy.SKIP,
            new_plan=plan_tree,
            message=f"Skipped action {action.action_name}",
        )

    async def _handle_alternative(
        self,
        plan_tree: PlanTree,
        analysis: FailureAnalysis,
        context: Dict[str, Any],
    ) -> ReplanningResult:
        """Handle alternative strategy.

        Args:
            plan_tree: Current plan
            analysis: Failure analysis
            context: Additional context

        Returns:
            Result with alternative nodes
        """
        alternatives = await self.generate_alternatives(analysis, plan_tree, context)

        if not alternatives:
            return ReplanningResult(
                success=False,
                strategy_used=ReplanningStrategy.ALTERNATIVE,
                message="No alternatives generated",
            )

        return ReplanningResult(
            success=True,
            strategy_used=ReplanningStrategy.ALTERNATIVE,
            alternative_nodes=alternatives,
            message=f"Generated {len(alternatives)} alternative approaches",
        )

    def _handle_backtrack(self, plan_tree: PlanTree, analysis: FailureAnalysis) -> ReplanningResult:
        """Handle backtrack strategy.

        Args:
            plan_tree: Current plan
            analysis: Failure analysis

        Returns:
            Result with backtracked position
        """
        node = analysis.failed_node
        backtrack_count = 0

        # Go back up the tree
        while node.parent and backtrack_count < self.config.backtrack_limit:
            node = node.parent
            backtrack_count += 1

        # Set current node to parent
        plan_tree.current_node = node

        return ReplanningResult(
            success=True,
            strategy_used=ReplanningStrategy.BACKTRACK,
            new_plan=plan_tree,
            message=f"Backtracked {backtrack_count} levels to: {node.goal.description[:40]}",
        )

    def _handle_abort(self, plan_tree: PlanTree, analysis: FailureAnalysis) -> ReplanningResult:
        """Handle abort strategy.

        Args:
            plan_tree: Current plan
            analysis: Failure analysis

        Returns:
            Result with aborted plan
        """
        # Mark goal as failed
        analysis.failed_node.goal.fail(analysis.error_message)

        # Mark root as failed if we're at root
        if plan_tree.current_node == plan_tree.root:
            plan_tree.root.goal.fail("Plan aborted due to unrecoverable failure")

        return ReplanningResult(
            success=False,
            strategy_used=ReplanningStrategy.ABORT,
            message=f"Plan aborted: {analysis.error_message}",
        )

    def should_replan(self, plan_tree: PlanTree) -> bool:
        """Decide if replanning is needed based on current state.

        Args:
            plan_tree: Current plan tree

        Returns:
            True if replanning is recommended
        """
        return plan_tree.needs_replanning()

    def get_failure_history(self) -> List[FailureAnalysis]:
        """Get history of analyzed failures.

        Returns:
            List of failure analyses
        """
        return self._failure_history.copy()

    def clear_failure_history(self) -> None:
        """Clear the failure history."""
        self._failure_history.clear()

    def get_statistics(self) -> Dict[str, Any]:
        """Get replanning statistics.

        Returns:
            Dictionary with statistics
        """
        if not self._failure_history:
            return {
                "total_failures": 0,
                "by_type": {},
                "by_strategy": {},
                "recovery_rate": 0.0,
            }

        by_type: Dict[str, int] = {}
        by_strategy: Dict[str, int] = {}
        recoverable = 0

        for analysis in self._failure_history:
            # Count by type
            type_key = analysis.failure_type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

            # Count by strategy
            strategy_key = analysis.recommended_strategy.value
            by_strategy[strategy_key] = by_strategy.get(strategy_key, 0) + 1

            # Count recoverable
            if analysis.can_recover:
                recoverable += 1

        return {
            "total_failures": len(self._failure_history),
            "by_type": by_type,
            "by_strategy": by_strategy,
            "recovery_rate": recoverable / len(self._failure_history),
        }
