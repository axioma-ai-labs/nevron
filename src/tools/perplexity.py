import httpx
from loguru import logger

from src.core.config import settings
from src.core.exceptions import APIError


class PerplexityTool:
    """Tool for interacting with the Perplexity API."""

    def __init__(self):
        """Initialize the Perplexity tool with API configuration."""
        if not settings.PERPLEXITY_API_KEY:
            raise APIError("Perplexity API key is not set")
        if not settings.PERPLEXITY_ENDPOINT:
            raise APIError("Perplexity endpoint is not set")

        self.headers = {
            "Authorization": f"Bearer {settings.PERPLEXITY_API_KEY}",
            "Content-Type": "application/json",
        }
        self.client = httpx.AsyncClient(verify=False)

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.aclose()

    async def search(self, query: str) -> str:
        """
        Perform a Perplexity search.

        Args:
            query (str): The search query

        Returns:
            str: Search results or an error message
        """
        try:
            payload = {
                "model": settings.PERPLEXITY_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a capable and efficient search assistant. "
                            "Your job is to find relevant and concise information about "
                            "cryptocurrencies based on the query provided."
                            "Validate the results for relevance and clarity. "
                            "Return the results ONLY in the following string - dictionary format "
                            "(include curly brackets): "
                            f'{{ "headline": "all news texts here ", "category": "choose relevant news '
                            f'category from {settings.PERPLEXITY_NEWS_CATEGORY_LIST} ", "timestamp": '
                            f'"dd-mm-yyyy" }}'
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"{query}",
                    },
                ],
                "temperature": 0.3,
                "top_p": 0.8,
                "search_domain_filter": ["perplexity.ai"],
                "return_images": False,
                "return_related_questions": False,
                "stream": False,
            }

            response = await self.client.post(
                settings.PERPLEXITY_ENDPOINT, json=payload, headers=self.headers
            )
            response.raise_for_status()
            data = response.json()

            logger.debug(f"Perplexity Search | Successfully retrieved results: {data}")
            summary = (
                data.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "No summary available.")
            )

            # Get the total tokens used from the response
            total_tokens = data.get("usage", {}).get("total_tokens", 0)

            # Estimate the cost
            estimated_cost = self.estimate_cost(total_tokens)
            logger.debug(f"Estimated cost for the request: ${estimated_cost:.6f}")
            logger.info(f"Perplexity Search output type: {type(summary)}")
            return f"Perplexity Search Results:\n{summary}"
        except httpx.TimeoutException as e:
            logger.error(f"Timeout during Perplexity search: {str(e)}")
            return "Perplexity search data is currently unavailable due to a timeout error."
        except Exception as e:
            logger.error(f"Error during Perplexity search: {str(e)}")
            return "Perplexity search data is currently unavailable."

    def estimate_cost(self, total_tokens: int) -> float:
        """
        Estimate the cost per request for the Perplexity search.

        Args:
            total_tokens (int): Total number of tokens used in the prompt + completion.

        Returns:
            float: Estimated cost of the request.
        """
        # Define the cost per token
        TOKEN_COST_PER_MILLION = (
            0.2  # $0.2 per 1M tokens:  https://docs.perplexity.ai/guides/pricing
        )
        TOKEN_COST = TOKEN_COST_PER_MILLION / 1_000_000  # Cost per token

        # Calculate the estimated cost
        estimated_cost = total_tokens * TOKEN_COST
        return estimated_cost
