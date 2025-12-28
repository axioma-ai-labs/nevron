"""Self-Critic - RLAIF (Reinforcement Learning from AI Feedback).

Uses LLM to analyze failures and generate learning.
This is RLAIF - using AI to generate reward signal and improvement suggestions.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class CritiqueLevel(str, Enum):
    """Severity level of critique."""

    INFO = "info"  # Minor observations
    WARNING = "warning"  # Potential issues
    ERROR = "error"  # Clear problems
    CRITICAL = "critical"  # Major failures


@dataclass
class Critique:
    """Result of self-critique analysis."""

    id: str
    action: str
    context_summary: str
    outcome_summary: str

    # Analysis results
    failure_reason: str
    what_went_wrong: str
    better_approach: str
    pattern_to_avoid: str
    lesson_learned: str

    # Metadata
    level: CritiqueLevel = CritiqueLevel.ERROR
    confidence: float = 0.7
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "action": self.action,
            "context_summary": self.context_summary,
            "outcome_summary": self.outcome_summary,
            "failure_reason": self.failure_reason,
            "what_went_wrong": self.what_went_wrong,
            "better_approach": self.better_approach,
            "pattern_to_avoid": self.pattern_to_avoid,
            "lesson_learned": self.lesson_learned,
            "level": self.level.value,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Critique":
        """Create from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            action=data["action"],
            context_summary=data.get("context_summary", ""),
            outcome_summary=data.get("outcome_summary", ""),
            failure_reason=data.get("failure_reason", ""),
            what_went_wrong=data.get("what_went_wrong", ""),
            better_approach=data.get("better_approach", ""),
            pattern_to_avoid=data.get("pattern_to_avoid", ""),
            lesson_learned=data.get("lesson_learned", ""),
            level=CritiqueLevel(data.get("level", "error")),
            confidence=data.get("confidence", 0.7),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.now(timezone.utc)),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ImprovementSuggestion:
    """Suggestion for improvement based on failure patterns."""

    id: str
    pattern: str  # What pattern was identified
    suggestion: str  # What to do differently
    priority: int  # 1 = highest priority
    affected_actions: List[str]
    confidence: float = 0.7
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "pattern": self.pattern,
            "suggestion": self.suggestion,
            "priority": self.priority,
            "affected_actions": self.affected_actions,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class FailedAction:
    """Represents a failed action for batch analysis."""

    action: str
    context: Dict[str, Any]
    outcome: Any
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SelfCritic:
    """Use LLM to analyze failures and generate learning.

    This implements RLAIF - using AI to generate reward signals
    and improvement suggestions when human feedback isn't available.

    Features:
    - Single action critique
    - Batch failure analysis
    - Pattern recognition across failures
    - Improvement suggestions
    """

    def __init__(self, llm_provider: Optional[Any] = None):
        """Initialize self-critic.

        Args:
            llm_provider: Optional LLM provider for generating critiques.
                         If not provided, uses rule-based analysis.
        """
        self._llm = llm_provider
        self._critiques: List[Critique] = []
        self._suggestions: List[ImprovementSuggestion] = []

        # Pattern matching rules for common failures
        self._failure_patterns: Dict[str, Dict[str, Any]] = {
            "rate_limit": {
                "keywords": ["rate limit", "too many requests", "429", "throttle"],
                "reason": "API rate limiting exceeded",
                "better_approach": "Implement backoff, use alternative API, or cache results",
                "pattern": "Excessive API calls without rate limiting",
            },
            "timeout": {
                "keywords": ["timeout", "timed out", "deadline exceeded"],
                "reason": "Operation timed out",
                "better_approach": "Increase timeout, use async processing, or break into smaller tasks",
                "pattern": "Long-running operations without timeout handling",
            },
            "auth_error": {
                "keywords": ["unauthorized", "forbidden", "401", "403", "permission"],
                "reason": "Authentication or authorization failed",
                "better_approach": "Verify credentials, check permissions, refresh tokens",
                "pattern": "Attempting actions without proper authorization",
            },
            "not_found": {
                "keywords": ["not found", "404", "does not exist", "missing"],
                "reason": "Resource not found",
                "better_approach": "Validate resource existence before action, handle missing gracefully",
                "pattern": "Assuming resources exist without verification",
            },
            "invalid_input": {
                "keywords": ["invalid", "bad request", "400", "validation", "malformed"],
                "reason": "Invalid input provided",
                "better_approach": "Validate inputs before sending, use schemas",
                "pattern": "Sending malformed or invalid data",
            },
            "connection_error": {
                "keywords": ["connection", "network", "unreachable", "refused"],
                "reason": "Network connection failed",
                "better_approach": "Implement retry logic, use fallback services",
                "pattern": "Not handling network failures gracefully",
            },
        }

        logger.debug("SelfCritic initialized")

    async def critique(
        self,
        action: str,
        context: Dict[str, Any],
        outcome: Any,
        error_message: Optional[str] = None,
    ) -> Critique:
        """Analyze a failed action and generate critique.

        Args:
            action: The action that was taken
            context: Context in which action was taken
            outcome: The outcome (usually error or empty result)
            error_message: Optional error message

        Returns:
            Critique with analysis and suggestions
        """
        # Summarize context and outcome
        context_summary = self._summarize_context(context)
        outcome_summary = self._summarize_outcome(outcome, error_message)

        # Try LLM-based analysis if available
        if self._llm is not None:
            try:
                critique = await self._llm_critique(
                    action, context_summary, outcome_summary, error_message
                )
                self._critiques.append(critique)
                return critique
            except Exception as e:
                logger.warning(f"LLM critique failed, using rule-based: {e}")

        # Fall back to rule-based analysis
        critique = self._rule_based_critique(
            action, context_summary, outcome_summary, error_message
        )
        self._critiques.append(critique)
        return critique

    async def _llm_critique(
        self,
        action: str,
        context_summary: str,
        outcome_summary: str,
        error_message: Optional[str],
    ) -> Critique:
        """Generate critique using LLM.

        Args:
            action: Action taken
            context_summary: Summary of context
            outcome_summary: Summary of outcome
            error_message: Error message if any

        Returns:
            LLM-generated Critique
        """
        prompt = f"""Analyze this failed action and provide learning:

Action taken: {action}
Context: {context_summary}
Outcome: {outcome_summary}
Error: {error_message or 'No specific error'}

Please analyze:
1. Why did this fail? (failure_reason)
2. What specifically went wrong? (what_went_wrong)
3. What should have been done instead? (better_approach)
4. What pattern should be avoided? (pattern_to_avoid)
5. What lesson should be remembered? (lesson_learned)

Respond in a structured format."""

        # Call LLM (self._llm is guaranteed to exist here due to try/except in caller)
        assert self._llm is not None
        response = await self._llm.generate_response(prompt)

        # Parse response (simplified - real implementation would parse structured output)
        return Critique(
            id=str(uuid.uuid4()),
            action=action,
            context_summary=context_summary,
            outcome_summary=outcome_summary,
            failure_reason=self._extract_field(response, "failure_reason"),
            what_went_wrong=self._extract_field(response, "what_went_wrong"),
            better_approach=self._extract_field(response, "better_approach"),
            pattern_to_avoid=self._extract_field(response, "pattern_to_avoid"),
            lesson_learned=self._extract_field(response, "lesson_learned"),
            confidence=0.8,
            metadata={"source": "llm"},
        )

    def _rule_based_critique(
        self,
        action: str,
        context_summary: str,
        outcome_summary: str,
        error_message: Optional[str],
    ) -> Critique:
        """Generate critique using pattern matching rules.

        Args:
            action: Action taken
            context_summary: Summary of context
            outcome_summary: Summary of outcome
            error_message: Error message if any

        Returns:
            Rule-based Critique
        """
        # Combine text for pattern matching
        text_to_match = f"{outcome_summary} {error_message or ''}".lower()

        # Find matching pattern
        matched_pattern = None
        for pattern_key, pattern_info in self._failure_patterns.items():
            keywords = pattern_info["keywords"]
            if any(kw in text_to_match for kw in keywords):
                matched_pattern = pattern_info
                break

        if matched_pattern:
            return Critique(
                id=str(uuid.uuid4()),
                action=action,
                context_summary=context_summary,
                outcome_summary=outcome_summary,
                failure_reason=matched_pattern["reason"],
                what_went_wrong=f"Action '{action}' failed: {matched_pattern['reason']}",
                better_approach=matched_pattern["better_approach"],
                pattern_to_avoid=matched_pattern["pattern"],
                lesson_learned=f"When using {action}: {matched_pattern['better_approach']}",
                confidence=0.6,
                metadata={"source": "rule_based", "pattern": pattern_key},
            )

        # Generic fallback
        return Critique(
            id=str(uuid.uuid4()),
            action=action,
            context_summary=context_summary,
            outcome_summary=outcome_summary,
            failure_reason="Unknown failure reason",
            what_went_wrong=f"Action '{action}' failed unexpectedly",
            better_approach="Review action parameters and preconditions",
            pattern_to_avoid="Unknown - requires further analysis",
            lesson_learned=f"Action '{action}' may be unreliable in this context",
            level=CritiqueLevel.WARNING,
            confidence=0.4,
            metadata={"source": "fallback"},
        )

    async def generate_improvement_suggestions(
        self,
        recent_failures: List[FailedAction],
    ) -> List[ImprovementSuggestion]:
        """Analyze patterns across multiple failures.

        Args:
            recent_failures: List of recent failed actions

        Returns:
            List of improvement suggestions
        """
        if not recent_failures:
            return []

        suggestions: List[ImprovementSuggestion] = []

        # Group failures by action
        by_action: Dict[str, List[FailedAction]] = {}
        for failure in recent_failures:
            if failure.action not in by_action:
                by_action[failure.action] = []
            by_action[failure.action].append(failure)

        # Analyze each action with multiple failures
        for action, failures in by_action.items():
            if len(failures) >= 2:  # Pattern requires at least 2 failures
                suggestion = self._analyze_failure_pattern(action, failures)
                if suggestion:
                    suggestions.append(suggestion)
                    self._suggestions.append(suggestion)

        # Analyze cross-action patterns
        cross_action = self._analyze_cross_action_patterns(recent_failures)
        suggestions.extend(cross_action)
        self._suggestions.extend(cross_action)

        # Sort by priority
        suggestions.sort(key=lambda s: s.priority)

        return suggestions

    def _analyze_failure_pattern(
        self,
        action: str,
        failures: List[FailedAction],
    ) -> Optional[ImprovementSuggestion]:
        """Analyze failures for a single action.

        Args:
            action: Action name
            failures: List of failures

        Returns:
            ImprovementSuggestion or None
        """
        # Look for common error types
        error_counts: Dict[str, int] = {}
        for f in failures:
            if f.error_message:
                for pattern_key, pattern in self._failure_patterns.items():
                    if any(kw in f.error_message.lower() for kw in pattern["keywords"]):
                        error_counts[pattern_key] = error_counts.get(pattern_key, 0) + 1
                        break

        if error_counts:
            # Find most common pattern
            most_common = max(error_counts.keys(), key=lambda k: error_counts[k])
            pattern_info = self._failure_patterns[most_common]

            return ImprovementSuggestion(
                id=str(uuid.uuid4()),
                pattern=f"Repeated {most_common} failures in {action}",
                suggestion=pattern_info["better_approach"],
                priority=1 if error_counts[most_common] >= 3 else 2,
                affected_actions=[action],
                confidence=min(0.9, 0.5 + 0.1 * error_counts[most_common]),
            )

        # Generic suggestion for unexplained failures
        return ImprovementSuggestion(
            id=str(uuid.uuid4()),
            pattern=f"Frequent failures in {action} ({len(failures)} times)",
            suggestion=f"Review {action} implementation and add better error handling",
            priority=3,
            affected_actions=[action],
            confidence=0.5,
        )

    def _analyze_cross_action_patterns(
        self,
        failures: List[FailedAction],
    ) -> List[ImprovementSuggestion]:
        """Analyze patterns across different actions.

        Args:
            failures: All recent failures

        Returns:
            List of cross-action suggestions
        """
        suggestions: List[ImprovementSuggestion] = []

        # Check for system-wide issues
        error_types: Dict[str, List[str]] = {}
        for f in failures:
            if f.error_message:
                for pattern_key, pattern in self._failure_patterns.items():
                    if any(kw in f.error_message.lower() for kw in pattern["keywords"]):
                        if pattern_key not in error_types:
                            error_types[pattern_key] = []
                        if f.action not in error_types[pattern_key]:
                            error_types[pattern_key].append(f.action)
                        break

        # System-wide pattern suggestions
        for pattern_key, affected_actions in error_types.items():
            if len(affected_actions) >= 2:
                pattern_info = self._failure_patterns[pattern_key]
                suggestions.append(
                    ImprovementSuggestion(
                        id=str(uuid.uuid4()),
                        pattern=f"System-wide {pattern_key} issues",
                        suggestion=f"Address {pattern_info['reason']} across all actions: "
                        f"{pattern_info['better_approach']}",
                        priority=1,  # High priority for system-wide
                        affected_actions=affected_actions,
                        confidence=0.8,
                    )
                )

        return suggestions

    def _summarize_context(self, context: Dict[str, Any]) -> str:
        """Create a summary of context for analysis.

        Args:
            context: Full context dictionary

        Returns:
            Summary string
        """
        if not context:
            return "No context provided"

        # Extract key fields
        parts = []
        for key in ["goal", "task", "action", "state", "query"]:
            if key in context:
                parts.append(f"{key}: {context[key]}")

        if parts:
            return "; ".join(parts[:3])  # Limit to 3 key fields
        return str(context)[:200]  # Fallback to truncated string

    def _summarize_outcome(
        self,
        outcome: Any,
        error_message: Optional[str],
    ) -> str:
        """Create a summary of outcome.

        Args:
            outcome: The outcome value
            error_message: Error message if any

        Returns:
            Summary string
        """
        if error_message:
            return f"Error: {error_message}"
        if outcome is None:
            return "No result returned"
        return str(outcome)[:200]

    def _extract_field(self, response: str, field_name: str) -> str:
        """Extract a field from LLM response.

        Args:
            response: LLM response text
            field_name: Field to extract

        Returns:
            Extracted value or default
        """
        # Simple extraction - look for field name followed by value
        lines = response.split("\n")
        for line in lines:
            if field_name.replace("_", " ") in line.lower():
                parts = line.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return f"See analysis for {field_name}"

    def get_recent_critiques(self, limit: int = 10) -> List[Critique]:
        """Get recent critiques.

        Args:
            limit: Maximum critiques to return

        Returns:
            List of recent Critiques
        """
        return self._critiques[-limit:]

    def get_suggestions(self) -> List[ImprovementSuggestion]:
        """Get all improvement suggestions.

        Returns:
            List of suggestions
        """
        return list(self._suggestions)

    def clear(self) -> None:
        """Clear all critiques and suggestions."""
        self._critiques.clear()
        self._suggestions.clear()
        logger.debug("SelfCritic cleared")
