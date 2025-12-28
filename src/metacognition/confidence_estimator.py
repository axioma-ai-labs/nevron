"""Confidence Estimator - Estimate agent's confidence in current approach.

Low confidence triggers human handoff.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class ConfidenceFactor(Enum):
    """Factors that affect confidence estimation."""

    GOAL_CLARITY = "goal_clarity"  # Is the goal well-defined?
    MEMORY_SUPPORT = "memory_support"  # Have we done this before?
    TOOL_AVAILABILITY = "tool_availability"  # Do we have needed tools?
    CONTEXT_FAMILIARITY = "context_familiarity"  # Is this situation known?
    PLAN_COMPLETENESS = "plan_completeness"  # Is the plan complete?
    SUCCESS_HISTORY = "success_history"  # Past success rate
    ERROR_STATE = "error_state"  # Are we in an error state?


@dataclass
class ConfidenceEstimate:
    """Represents an estimate of the agent's confidence."""

    level: float  # 0.0 to 1.0
    factors: Dict[ConfidenceFactor, float]  # Factor -> score
    uncertain_aspects: List[str]
    would_benefit_from: Optional[str] = None
    should_request_help: bool = False
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "level": self.level,
            "factors": {k.value: v for k, v in self.factors.items()},
            "uncertain_aspects": self.uncertain_aspects,
            "would_benefit_from": self.would_benefit_from,
            "should_request_help": self.should_request_help,
            "explanation": self.explanation,
        }

    @property
    def is_low(self) -> bool:
        """Check if confidence is low."""
        return self.level < 0.4

    @property
    def is_medium(self) -> bool:
        """Check if confidence is medium."""
        return 0.4 <= self.level < 0.7

    @property
    def is_high(self) -> bool:
        """Check if confidence is high."""
        return self.level >= 0.7

    @property
    def weakest_factor(self) -> Optional[ConfidenceFactor]:
        """Get the weakest confidence factor."""
        if not self.factors:
            return None
        return min(self.factors.keys(), key=lambda k: self.factors[k])


class ConfidenceEstimator:
    """Estimate agent's confidence in current approach.

    Factors considered:
    - Plan clarity (is goal well-defined?)
    - Memory support (have we done this before?)
    - Tool availability (do we have needed tools?)
    - Context familiarity (is this situation known?)
    - Recent performance (are we succeeding?)
    """

    # Weights for each factor
    FACTOR_WEIGHTS = {
        ConfidenceFactor.GOAL_CLARITY: 0.25,
        ConfidenceFactor.MEMORY_SUPPORT: 0.15,
        ConfidenceFactor.TOOL_AVAILABILITY: 0.15,
        ConfidenceFactor.CONTEXT_FAMILIARITY: 0.15,
        ConfidenceFactor.PLAN_COMPLETENESS: 0.10,
        ConfidenceFactor.SUCCESS_HISTORY: 0.15,
        ConfidenceFactor.ERROR_STATE: 0.05,
    }

    # Threshold for requesting human help
    HELP_THRESHOLD = 0.3

    def __init__(self):
        """Initialize confidence estimator."""
        logger.debug("ConfidenceEstimator initialized")

    def estimate(
        self,
        goal: Optional[str] = None,
        plan: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        available_tools: Optional[List[str]] = None,
        memory_matches: Optional[List[Dict[str, Any]]] = None,
        success_rate: float = 0.5,
        error_state: bool = False,
    ) -> ConfidenceEstimate:
        """Estimate confidence in current approach.

        Args:
            goal: Current goal description
            plan: Current plan structure
            context: Current context
            available_tools: List of available tool names
            memory_matches: Relevant memories found
            success_rate: Recent success rate
            error_state: Whether in an error state

        Returns:
            ConfidenceEstimate
        """
        factors: Dict[ConfidenceFactor, float] = {}
        uncertain_aspects: List[str] = []

        # 1. Goal clarity
        goal_score = self._assess_goal_clarity(goal)
        factors[ConfidenceFactor.GOAL_CLARITY] = goal_score
        if goal_score < 0.5:
            uncertain_aspects.append("Goal is unclear or undefined")

        # 2. Memory support
        memory_score = self._assess_memory_support(memory_matches)
        factors[ConfidenceFactor.MEMORY_SUPPORT] = memory_score
        if memory_score < 0.5:
            uncertain_aspects.append("No similar past experience found")

        # 3. Tool availability
        tool_score = self._assess_tool_availability(available_tools, plan)
        factors[ConfidenceFactor.TOOL_AVAILABILITY] = tool_score
        if tool_score < 0.5:
            uncertain_aspects.append("Required tools may not be available")

        # 4. Context familiarity
        context_score = self._assess_context_familiarity(context, memory_matches)
        factors[ConfidenceFactor.CONTEXT_FAMILIARITY] = context_score
        if context_score < 0.5:
            uncertain_aspects.append("Unfamiliar situation")

        # 5. Plan completeness
        plan_score = self._assess_plan_completeness(plan)
        factors[ConfidenceFactor.PLAN_COMPLETENESS] = plan_score
        if plan_score < 0.5:
            uncertain_aspects.append("Plan may be incomplete")

        # 6. Success history
        factors[ConfidenceFactor.SUCCESS_HISTORY] = success_rate
        if success_rate < 0.5:
            uncertain_aspects.append("Recent performance has been poor")

        # 7. Error state
        error_score = 0.2 if error_state else 1.0
        factors[ConfidenceFactor.ERROR_STATE] = error_score
        if error_state:
            uncertain_aspects.append("Currently in error recovery mode")

        # Calculate overall confidence
        overall = self._calculate_overall_confidence(factors)

        # Determine if should request help
        should_request_help = overall < self.HELP_THRESHOLD

        # Generate explanation and help request
        would_benefit_from = (
            self._generate_help_request(factors, uncertain_aspects) if should_request_help else None
        )

        explanation = self._generate_explanation(factors, uncertain_aspects)

        return ConfidenceEstimate(
            level=overall,
            factors=factors,
            uncertain_aspects=uncertain_aspects,
            would_benefit_from=would_benefit_from,
            should_request_help=should_request_help,
            explanation=explanation,
        )

    def _assess_goal_clarity(self, goal: Optional[str]) -> float:
        """Assess how clear the goal is.

        Args:
            goal: Goal description

        Returns:
            Clarity score (0.0 to 1.0)
        """
        if not goal:
            return 0.2

        # Check goal characteristics
        score = 0.5  # Base score for having a goal

        # Length check (too short or too long = less clear)
        if 20 <= len(goal) <= 200:
            score += 0.2

        # Check for question words (indicates uncertainty)
        question_words = ["what", "how", "why", "when", "where", "which"]
        goal_lower = goal.lower()
        if any(word in goal_lower for word in question_words):
            score -= 0.1

        # Check for action verbs (indicates actionable goal)
        action_verbs = ["create", "find", "analyze", "send", "search", "post", "get"]
        if any(verb in goal_lower for verb in action_verbs):
            score += 0.2

        # Check for specific keywords
        if any(word in goal_lower for word in ["specific", "exactly", "must", "should"]):
            score += 0.1

        return max(0.0, min(1.0, score))

    def _assess_memory_support(
        self,
        memory_matches: Optional[List[Dict[str, Any]]],
    ) -> float:
        """Assess memory support for the task.

        Args:
            memory_matches: Relevant memories found

        Returns:
            Memory support score (0.0 to 1.0)
        """
        if not memory_matches:
            return 0.3  # No memories = low support

        # More matches = higher support
        num_matches = len(memory_matches)
        if num_matches >= 5:
            return 0.9
        elif num_matches >= 3:
            return 0.7
        elif num_matches >= 1:
            return 0.5
        return 0.3

    def _assess_tool_availability(
        self,
        available_tools: Optional[List[str]],
        plan: Optional[Dict[str, Any]],
    ) -> float:
        """Assess tool availability for the plan.

        Args:
            available_tools: List of available tools
            plan: Current plan

        Returns:
            Tool availability score (0.0 to 1.0)
        """
        if not available_tools:
            return 0.5  # Unknown = neutral

        if not plan:
            return 0.7  # No plan = assume tools are available

        # Check if plan requires specific tools
        required_tools = plan.get("required_tools", [])
        if not required_tools:
            return 0.8

        # Calculate coverage
        available_set = set(available_tools)
        required_set = set(required_tools)
        covered = len(required_set & available_set)

        if len(required_set) == 0:
            return 0.8

        return covered / len(required_set)

    def _assess_context_familiarity(
        self,
        context: Optional[Dict[str, Any]],
        memory_matches: Optional[List[Dict[str, Any]]],
    ) -> float:
        """Assess familiarity with current context.

        Args:
            context: Current context
            memory_matches: Relevant memories

        Returns:
            Familiarity score (0.0 to 1.0)
        """
        if not context:
            return 0.5  # No context = neutral

        # Base score
        score = 0.5

        # Memory matches indicate familiarity
        if memory_matches and len(memory_matches) > 0:
            score += 0.2

        # Check for known context keys
        known_keys = ["goal", "task_type", "action", "environment"]
        present_known = sum(1 for k in known_keys if k in context)
        score += present_known * 0.1

        return min(1.0, score)

    def _assess_plan_completeness(
        self,
        plan: Optional[Dict[str, Any]],
    ) -> float:
        """Assess how complete the plan is.

        Args:
            plan: Current plan structure

        Returns:
            Completeness score (0.0 to 1.0)
        """
        if not plan:
            return 0.3  # No plan = low score

        score = 0.5  # Base for having a plan

        # Check for key plan components
        if plan.get("steps"):
            score += 0.2
        if plan.get("goal") or plan.get("objective"):
            score += 0.1
        if plan.get("success_criteria"):
            score += 0.1
        if plan.get("fallback") or plan.get("alternatives"):
            score += 0.1

        return min(1.0, score)

    def _calculate_overall_confidence(
        self,
        factors: Dict[ConfidenceFactor, float],
    ) -> float:
        """Calculate overall confidence from factors.

        Args:
            factors: Individual factor scores

        Returns:
            Overall confidence (0.0 to 1.0)
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for factor, score in factors.items():
            weight = self.FACTOR_WEIGHTS.get(factor, 0.1)
            weighted_sum += score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.5

        return weighted_sum / total_weight

    def _generate_help_request(
        self,
        factors: Dict[ConfidenceFactor, float],
        uncertain_aspects: List[str],
    ) -> str:
        """Generate a help request based on weaknesses.

        Args:
            factors: Factor scores
            uncertain_aspects: List of uncertainties

        Returns:
            Help request string
        """
        # Find the weakest factor
        weakest = min(factors.keys(), key=lambda k: factors[k])

        help_requests = {
            ConfidenceFactor.GOAL_CLARITY: "Human clarification on the exact goal and success criteria",
            ConfidenceFactor.MEMORY_SUPPORT: "Human guidance on how to approach this unfamiliar task",
            ConfidenceFactor.TOOL_AVAILABILITY: "Human help identifying the right tools to use",
            ConfidenceFactor.CONTEXT_FAMILIARITY: "Human context about this situation",
            ConfidenceFactor.PLAN_COMPLETENESS: "Human input on the overall approach",
            ConfidenceFactor.SUCCESS_HISTORY: "Human feedback on what's going wrong",
            ConfidenceFactor.ERROR_STATE: "Human assistance recovering from errors",
        }

        return help_requests.get(
            weakest,
            "Human guidance on how to proceed",
        )

    def _generate_explanation(
        self,
        factors: Dict[ConfidenceFactor, float],
        uncertain_aspects: List[str],
    ) -> str:
        """Generate explanation of confidence level.

        Args:
            factors: Factor scores
            uncertain_aspects: List of uncertainties

        Returns:
            Explanation string
        """
        overall = self._calculate_overall_confidence(factors)

        if overall >= 0.7:
            level_desc = "High confidence"
        elif overall >= 0.4:
            level_desc = "Medium confidence"
        else:
            level_desc = "Low confidence"

        explanation = f"{level_desc} ({overall:.0%})"

        if uncertain_aspects:
            explanation += f". Uncertainties: {', '.join(uncertain_aspects[:2])}"

        return explanation

    def quick_estimate(
        self,
        goal: Optional[str] = None,
        has_memories: bool = False,
        success_rate: float = 0.5,
        error_state: bool = False,
    ) -> float:
        """Quick confidence estimate without full analysis.

        Args:
            goal: Current goal
            has_memories: Whether relevant memories exist
            success_rate: Recent success rate
            error_state: Whether in error state

        Returns:
            Confidence level (0.0 to 1.0)
        """
        score = 0.5

        if goal and len(goal) > 10:
            score += 0.15

        if has_memories:
            score += 0.15

        score += (success_rate - 0.5) * 0.2

        if error_state:
            score -= 0.2

        return max(0.0, min(1.0, score))
