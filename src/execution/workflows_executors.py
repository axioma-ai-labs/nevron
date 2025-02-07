from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.execution.base import ActionExecutor
from src.workflows.analyze_signal import analyze_signal
from src.workflows.research_news import analyze_news_workflow


class AnalyzeNewsExecutor(ActionExecutor):
    """Executor for news analysis action."""

    def _initialize_client(self) -> None:
        """No client needed for workflow."""
        return None

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["news_text"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        try:
            news_text = context.get("news_text")
            if not news_text:
                return False, "No news text provided in context"

            result = await analyze_news_workflow(news=news_text)
            return True, f"News analyzed: {result}"
        except Exception as e:
            logger.error(f"Failed to analyze news: {e}")
            return False, str(e)


class CheckSignalExecutor(ActionExecutor):
    """Executor for signal checking action."""

    def _initialize_client(self) -> None:
        """No client needed for workflow."""
        return None

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        try:
            result = await analyze_signal()
            return True, f"Signal checked: {result}"
        except Exception as e:
            logger.error(f"Failed to check signal: {e}")
            return False, str(e)


class IdleExecutor(ActionExecutor):
    """Executor for idle action."""

    def _initialize_client(self) -> None:
        """No client needed for idle."""
        return None

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        return True, "Idle completed"
