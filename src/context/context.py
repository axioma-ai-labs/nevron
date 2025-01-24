"""Context module for maintaining agent's persistent state and history."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger
from pydantic import BaseModel, Field

from src.core.defs import AgentAction, AgentState


class ActionContext(BaseModel):
    """Context for a single action."""

    timestamp: datetime = datetime.now(timezone.utc)
    action: AgentAction
    state: AgentState
    outcome: Optional[str] = None
    reward: Optional[float] = None
    metadata: Dict = Field(default_factory=dict)


class AgentContext(BaseModel):
    """Main context container for the agent."""

    actions_history: List[ActionContext] = Field(default_factory=list)
    last_state: AgentState = AgentState.DEFAULT
    total_actions: int = 0
    total_rewards: float = 0.0
    metadata: Dict = Field(default_factory=dict)

    def add_action(
        self,
        action: AgentAction,
        state: AgentState,
        outcome: Optional[str] = None,
        reward: Optional[float] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Add a new action to the context.

        Args:
            action: The action taken
            state: The state when action was taken
            outcome: Optional outcome of the action
            reward: Optional reward received
            metadata: Optional additional metadata
        """
        action_context = ActionContext(
            action=action,
            state=state,
            outcome=outcome,
            reward=reward,
            metadata=metadata or {},
        )
        self.actions_history.append(action_context)
        self.last_state = state
        self.total_actions += 1
        if reward is not None:
            self.total_rewards += reward

    def get_recent_actions(self, n: int = 5) -> List[ActionContext]:
        """Get the n most recent actions."""
        return self.actions_history[-n:]

    def get_actions_in_state(self, state: AgentState) -> List[ActionContext]:
        """Get all actions taken in a specific state."""
        return [ac for ac in self.actions_history if ac.state == state]

    def get_actions_by_type(self, action_type: AgentAction) -> List[ActionContext]:
        """Get all actions of a specific type."""
        return [ac for ac in self.actions_history if ac.action == action_type]


class ContextManager:
    """Manages persistence of agent context."""

    def __init__(self, context_path: str = "lib/agent_context.json"):
        """
        Initialize the context manager.

        Args:
            context_path: Path to the context file
        """
        self.context_path = Path(context_path)
        self.context = self._load_context()

    def _load_context(self) -> AgentContext:
        """Load context from file or create new if doesn't exist."""
        if self.context_path.exists():
            try:
                with open(self.context_path, "r") as f:
                    data = json.load(f)
                    return AgentContext.model_validate_json(data)
            except Exception as e:
                logger.error(f"Failed to load context: {e}")
                return AgentContext()
        return AgentContext()

    def save_context(self) -> None:
        """Save current context to file."""
        try:
            # Create directory if it doesn't exist
            self.context_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.context_path, "w") as f:
                f.write(self.context.model_dump_json(indent=2))
            logger.debug(f"Context saved to {self.context_path}")
        except Exception as e:
            logger.error(f"Failed to save context: {e}")

    def add_action(
        self,
        action: AgentAction,
        state: AgentState,
        outcome: Optional[str] = None,
        reward: Optional[float] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Add action to context and persist.

        Args:
            action: The action taken
            state: The state when action was taken
            outcome: Optional outcome of the action
            reward: Optional reward received
            metadata: Optional additional metadata
        """
        self.context.add_action(action, state, outcome, reward, metadata)
        self.save_context()

    def get_context(self) -> AgentContext:
        """Get the current context."""
        return self.context
