import json

import httpx
from loguru import logger

from src.core.config import settings
from src.core.defs import AgentAction, AgentState


class PlanningModule:
    """Centralized Planning Module using LLM for action selection."""

    def __init__(
        self, api_url: str = settings.PLANNING_API_URL, model: str = settings.PLANNING_MODEL
    ):
        """
        Initialize the Planning Module.

        Args:
            api_url (str): The URL for the LLM API.
            model (str): The model name (e.g., 'llama3.2').
        """
        self.api_url = api_url
        self.model = model

    async def get_next_action(self, state: AgentState) -> AgentAction:
        """
        Call the LLM to decide the next action.

        Args:
            context (dict): Context including state, previous actions, and outcomes.

        Returns:
            AgentAction: The next action to perform.
        """
        prompt = (
            "You are a helpful assistant, who only decides the next action to perform. "
            f"Following states are possible: {AgentState.__members__}. "
            f"You have the following possible actions: {AgentAction.__members__}. "
            "You need to decide the next action to perform. "
            "Return only the name of the action to perform and nothing else!"
            f"Current state of the agent: {state.value}. "
        )
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }
            async with httpx.AsyncClient() as client:
                logger.debug(f"Sending payload: {payload}")
                response = await client.post(self.api_url, json=payload)
                logger.debug(f"Received response: {response}")
                response.raise_for_status()

            data = response.json()
            logger.debug(f"LLM response: {data}")
            next_action = data.get("response")
            if not next_action or next_action not in AgentAction.__members__:
                logger.warning(f"Invalid action returned by LLM: {next_action}")
                return AgentAction.IDLE

            logger.info(f"LLM suggested action: {next_action}")
            return AgentAction[next_action]
        except Exception as e:
            logger.error(f"Failed to get next action from LLM: {e}")
            return AgentAction.IDLE
