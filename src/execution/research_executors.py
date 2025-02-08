from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.core.exceptions import CoinstatsError, PerplexityError, TavilyError
from src.execution.base import ActionExecutor
from src.tools.get_signal import CoinstatsTool
from src.tools.perplexity import PerplexityTool
from src.tools.tavily import TavilyTool


class SearchTavilyExecutor(ActionExecutor):
    """Executor for searching using Tavily API."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> TavilyTool:
        """Initialize Tavily tool client."""
        return TavilyTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["query"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Tavily search."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            query = context.get("query")
            filters = context.get("filters", {})  # Optional filters

            logger.info(f"Executing Tavily search for query: {query}")
            results = await self.client.search(query, filters)
            parsed_results = self.client.parse_results(results)

            if parsed_results:
                return True, f"Found {len(parsed_results)} results"
            return False, "No results found"

        except TavilyError as e:
            error_msg = f"Failed to execute Tavily search: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while executing Tavily search: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class PerplexityExecutor(ActionExecutor):
    """Executor for querying Perplexity API."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> PerplexityTool:
        """Initialize Perplexity tool client."""
        return PerplexityTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["query"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Perplexity query."""
        try:
            if not self.validate_context(context):
                return False, "Missing required arguments in context"

            query = context.get("query")

            logger.info(f"Executing Perplexity query: {query}")
            results = await self.client.search(query)

            if results:
                return True, results
            return False, "No results found from Perplexity"

        except PerplexityError as e:
            error_msg = f"Failed to execute Perplexity query: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while executing Perplexity query: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class CoinstatsExecutor(ActionExecutor):
    """Executor for querying Coinstats API for signals and news."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> CoinstatsTool:
        """Initialize Coinstats tool client."""
        return CoinstatsTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return []  # No specific context required for basic signal fetching

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Coinstats signal fetching."""
        try:
            # Fetch signal using the Coinstats tool
            logger.info("Fetching signal from Coinstats")
            signal_data = await self.client.fetch_signal()
            if signal_data:
                return True, signal_data
            return False, "No news found from Coinstats"
        except CoinstatsError as e:
            error_msg = f"Failed to fetch from Coinstats: {str(e)}"
            logger.error(error_msg)

            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while fetching from Coinstats: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
