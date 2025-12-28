"""Metacognitive Monitor - Unified self-awareness interface.

External supervisor that watches the primary agent.
Inspired by VIGIL framework - decoupled from task execution.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.defs import AgentAction, AgentState
from src.learning.tracker import ActionTracker
from src.metacognition.confidence_estimator import ConfidenceEstimate, ConfidenceEstimator
from src.metacognition.failure_predictor import FailurePrediction, FailurePredictor
from src.metacognition.human_handoff import HandoffChannel, HumanHandoff, HumanResponse
from src.metacognition.intervention import Intervention, InterventionType
from src.metacognition.loop_detector import LoopDetector


@dataclass
class MonitoringState:
    """State of the metacognitive monitor."""

    is_stuck: bool = False
    confidence_level: float = 0.5
    failure_risk: float = 0.0
    last_intervention: Optional[Intervention] = None
    intervention_count: int = 0
    actions_since_intervention: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_stuck": self.is_stuck,
            "confidence_level": self.confidence_level,
            "failure_risk": self.failure_risk,
            "last_intervention": (
                self.last_intervention.to_dict() if self.last_intervention else None
            ),
            "intervention_count": self.intervention_count,
            "actions_since_intervention": self.actions_since_intervention,
            "created_at": self.created_at.isoformat(),
        }


class MetacognitiveMonitor:
    """External supervisor that watches the primary agent.

    Inspired by VIGIL framework - decoupled from task execution.
    Monitors agent behavior and triggers interventions when needed.

    Components:
    - LoopDetector: Detect repetitive behavior
    - FailurePredictor: Predict impending failures
    - ConfidenceEstimator: Estimate confidence in approach
    - HumanHandoff: Request human assistance
    """

    # Thresholds for interventions
    LOOP_BREAK_THRESHOLD = 3  # Repetitions before breaking loop
    FAILURE_PREDICTION_THRESHOLD = 0.7  # Probability to trigger replan
    CONFIDENCE_HANDOFF_THRESHOLD = 0.3  # Confidence to trigger handoff
    MAX_CONSECUTIVE_FAILURES = 5  # Failures before abort

    def __init__(
        self,
        action_tracker: Optional[ActionTracker] = None,
        enable_human_handoff: bool = True,
        handoff_channel: HandoffChannel = HandoffChannel.CONSOLE,
    ):
        """Initialize metacognitive monitor.

        Args:
            action_tracker: Optional tracker for history-based prediction
            enable_human_handoff: Whether to enable human handoff
            handoff_channel: Default channel for human communication
        """
        # Initialize components
        self._loop_detector = LoopDetector(repetition_threshold=self.LOOP_BREAK_THRESHOLD)
        self._failure_predictor = FailurePredictor(action_tracker=action_tracker)
        self._confidence_estimator = ConfidenceEstimator()
        self._human_handoff = HumanHandoff(default_channel=handoff_channel)

        self._enable_handoff = enable_human_handoff
        self._tracker = action_tracker

        # State
        self._state = MonitoringState()
        self._intervention_history: List[Intervention] = []
        self._consecutive_failures = 0

        logger.info("MetacognitiveMonitor initialized")

    def set_action_tracker(self, tracker: ActionTracker) -> None:
        """Set the action tracker.

        Args:
            tracker: ActionTracker instance
        """
        self._tracker = tracker
        self._failure_predictor.set_tracker(tracker)

    async def monitor(
        self,
        action: str,
        agent_state: AgentState,
        context: Dict[str, Any],
        goal: Optional[str] = None,
        plan: Optional[Dict[str, Any]] = None,
        available_actions: Optional[List[str]] = None,
    ) -> Intervention:
        """Main monitoring method - called before each action execution.

        Args:
            action: Planned action
            agent_state: Current agent state
            context: Current context
            goal: Current goal
            plan: Current plan
            available_actions: List of available action names

        Returns:
            Intervention (CONTINUE if no intervention needed)
        """
        self._state.actions_since_intervention += 1

        # 1. Check for loops
        loop_intervention = self._check_loops(action, context, available_actions)
        if loop_intervention.type != InterventionType.CONTINUE:
            return self._record_intervention(loop_intervention)

        # 2. Predict failures
        failure_intervention = self._check_failure_prediction(action, context)
        if failure_intervention.type != InterventionType.CONTINUE:
            return self._record_intervention(failure_intervention)

        # 3. Check confidence
        confidence_intervention = await self._check_confidence(action, goal, plan, context)
        if confidence_intervention.type != InterventionType.CONTINUE:
            return self._record_intervention(confidence_intervention)

        # 4. Check consecutive failures
        if self._consecutive_failures >= self.MAX_CONSECUTIVE_FAILURES:
            abort = Intervention.abort(
                reason=f"Too many consecutive failures ({self._consecutive_failures})",
                context={"consecutive_failures": self._consecutive_failures},
            )
            return self._record_intervention(abort)

        # No intervention needed
        return Intervention.continue_execution()

    async def monitor_action(
        self,
        action: AgentAction,
        agent_state: AgentState,
        context: Dict[str, Any],
        goal: Optional[str] = None,
        plan: Optional[Dict[str, Any]] = None,
    ) -> Intervention:
        """Monitor for AgentAction enum.

        Args:
            action: AgentAction to monitor
            agent_state: Current state
            context: Current context
            goal: Current goal
            plan: Current plan

        Returns:
            Intervention
        """
        available = [a.value for a in AgentAction]
        return await self.monitor(
            action=action.value,
            agent_state=agent_state,
            context=context,
            goal=goal,
            plan=plan,
            available_actions=available,
        )

    def _check_loops(
        self,
        action: str,
        context: Dict[str, Any],
        available_actions: Optional[List[str]],
    ) -> Intervention:
        """Check for loop patterns.

        Args:
            action: Current action
            context: Current context
            available_actions: Available actions for alternatives

        Returns:
            Intervention
        """
        context_hash = str(hash(frozenset(context.items())))[:8]

        if self._loop_detector.is_stuck(action, context_hash):
            self._state.is_stuck = True

            # Get alternative action
            alternatives = []
            if available_actions:
                suggestion = self._loop_detector.suggest_break_action(available_actions)
                if suggestion:
                    alternatives.append(suggestion)

            return Intervention.break_loop(
                reason=self._loop_detector.get_loop_description(),
                suggested_action=alternatives[0] if alternatives else None,
                alternatives=alternatives,
            )

        self._state.is_stuck = False
        return Intervention.continue_execution()

    def _check_failure_prediction(
        self,
        action: str,
        context: Dict[str, Any],
    ) -> Intervention:
        """Check failure prediction for action.

        Args:
            action: Action to check
            context: Current context

        Returns:
            Intervention
        """
        prediction = self._failure_predictor.predict(action, context)
        self._state.failure_risk = prediction.probability

        if prediction.is_high_risk:
            if prediction.suggested_alternatives:
                return Intervention.fallback(
                    reason=", ".join(prediction.reason_details),
                    suggested_action=prediction.suggested_alternatives[0],
                    alternatives=prediction.suggested_alternatives,
                )

            if prediction.wait_seconds > 0:
                return Intervention.pause(
                    reason=", ".join(prediction.reason_details),
                    wait_seconds=prediction.wait_seconds,
                )

            return Intervention.preemptive_replan(
                reason=", ".join(prediction.reason_details),
                context={"prediction": prediction.to_dict()},
            )

        return Intervention.continue_execution()

    async def _check_confidence(
        self,
        action: str,
        goal: Optional[str],
        plan: Optional[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> Intervention:
        """Check confidence level.

        Args:
            action: Current action
            goal: Current goal
            plan: Current plan
            context: Current context

        Returns:
            Intervention
        """
        # Get success rate from tracker if available
        success_rate = 0.5
        if self._tracker:
            success_rate = self._tracker.get_success_rate(action)

        estimate = self._confidence_estimator.estimate(
            goal=goal,
            plan=plan,
            context=context,
            success_rate=success_rate,
            error_state=context.get("error_state", False),
        )

        self._state.confidence_level = estimate.level

        if estimate.should_request_help and self._enable_handoff:
            # Request human help
            return Intervention.human_handoff(
                reason=estimate.explanation,
                context={
                    "confidence": estimate.to_dict(),
                    "goal": goal,
                    "action": action,
                    "would_benefit_from": estimate.would_benefit_from,
                },
            )

        return Intervention.continue_execution()

    def _record_intervention(self, intervention: Intervention) -> Intervention:
        """Record an intervention.

        Args:
            intervention: Intervention to record

        Returns:
            The same intervention
        """
        self._state.last_intervention = intervention
        self._state.intervention_count += 1
        self._state.actions_since_intervention = 0
        self._intervention_history.append(intervention)

        logger.warning(f"Intervention triggered: {intervention}")
        return intervention

    def record_action_result(
        self,
        action: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Record the result of an action for monitoring.

        Args:
            action: Action that was executed
            success: Whether it succeeded
            error_message: Optional error message
        """
        if success:
            self._consecutive_failures = 0
        else:
            self._consecutive_failures += 1

            # Record failure for predictor
            if self._tracker:
                from src.learning.tracker import ActionOutcome

                outcome = ActionOutcome(
                    id="failure",
                    action=action,
                    context_key="failure",
                    reward=-1.0,
                    success=False,
                    metadata={"error": error_message} if error_message else {},
                )
                self._failure_predictor.record_failure(outcome)

    async def request_human_help(
        self,
        question: str,
        context: Dict[str, Any],
        options: Optional[List[str]] = None,
        timeout: float = 3600.0,
    ) -> Optional[HumanResponse]:
        """Request help from a human.

        Args:
            question: Question to ask
            context: Context information
            options: Optional choices
            timeout: Timeout in seconds

        Returns:
            HumanResponse or None
        """
        if not self._enable_handoff:
            logger.warning("Human handoff is disabled")
            return None

        return await self._human_handoff.request_help(
            question=question,
            context=context,
            options=options,
            timeout=timeout,
        )

    async def report_uncertainty(
        self,
        what_im_doing: str,
        what_im_unsure_about: str,
        options_im_considering: List[str],
    ) -> None:
        """Report uncertainty to human.

        Args:
            what_im_doing: Current task
            what_im_unsure_about: Uncertainty
            options_im_considering: Options being considered
        """
        await self._human_handoff.report_uncertainty(
            what_im_doing=what_im_doing,
            what_im_unsure_about=what_im_unsure_about,
            options_im_considering=options_im_considering,
        )

    def get_state(self) -> MonitoringState:
        """Get current monitoring state.

        Returns:
            MonitoringState
        """
        return self._state

    def get_loop_detector(self) -> LoopDetector:
        """Get the loop detector.

        Returns:
            LoopDetector instance
        """
        return self._loop_detector

    def get_failure_predictor(self) -> FailurePredictor:
        """Get the failure predictor.

        Returns:
            FailurePredictor instance
        """
        return self._failure_predictor

    def get_confidence_estimator(self) -> ConfidenceEstimator:
        """Get the confidence estimator.

        Returns:
            ConfidenceEstimator instance
        """
        return self._confidence_estimator

    def get_human_handoff(self) -> HumanHandoff:
        """Get the human handoff handler.

        Returns:
            HumanHandoff instance
        """
        return self._human_handoff

    def get_intervention_history(self, limit: int = 50) -> List[Intervention]:
        """Get recent interventions.

        Args:
            limit: Maximum interventions to return

        Returns:
            List of Intervention
        """
        return self._intervention_history[-limit:]

    def clear(self) -> None:
        """Clear monitor state."""
        self._loop_detector.clear()
        self._failure_predictor.clear()
        self._human_handoff.clear()
        self._intervention_history.clear()
        self._consecutive_failures = 0
        self._state = MonitoringState()
        logger.debug("MetacognitiveMonitor cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get monitor statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "state": self._state.to_dict(),
            "loop_detector": self._loop_detector.get_statistics(),
            "failure_predictor": self._failure_predictor.get_statistics(),
            "human_handoff": self._human_handoff.get_statistics(),
            "total_interventions": len(self._intervention_history),
            "consecutive_failures": self._consecutive_failures,
            "handoff_enabled": self._enable_handoff,
        }

    def estimate_confidence(
        self,
        goal: Optional[str] = None,
        has_memories: bool = False,
        success_rate: float = 0.5,
        error_state: bool = False,
    ) -> ConfidenceEstimate:
        """Quick confidence estimation.

        Args:
            goal: Current goal
            has_memories: Whether memories exist
            success_rate: Recent success rate
            error_state: Whether in error state

        Returns:
            ConfidenceEstimate
        """
        return self._confidence_estimator.estimate(
            goal=goal,
            memory_matches=[{}] if has_memories else None,
            success_rate=success_rate,
            error_state=error_state,
        )

    def predict_failure(
        self,
        action: str,
        context: Dict[str, Any],
    ) -> FailurePrediction:
        """Predict failure for an action.

        Args:
            action: Action to predict for
            context: Current context

        Returns:
            FailurePrediction
        """
        return self._failure_predictor.predict(action, context)
