from typing import Any, Dict, List

import requests
from loguru import logger

from src.core.config import settings


class LinkParserTool:
    """Tool for fetching and parsing web content from links using Jina AI Reader."""

    def __init__(self):
        self.get_request_headers = {
            "Authorization": f"Bearer {settings.JINA_READER_API_KEY}",
            "Accept": "application/json",
            "X-Timeout": str(settings.JINA_READER_TIMEOUT),
            "X-Token-Budget": str(settings.JINA_READER_TOKEN_BUDGET),
            "X-Target-Selector": "body, .class, #id",
            "X-With-Generated-Alt": "true",  # Captions all images at the specified URL, adding 'Image [idx]: [caption]' as an alt tag for those without one
            "X-With-Images-Summary": "true",  # Generates a summary of all images at the specified URL
        }
        self.search_request_headers = {
            "Authorization": f"Bearer {settings.JINA_READER_API_KEY}",
            "Accept": "application/json",
            "X-Site": str(
                settings.JINA_SEARCH_WEBSITE
            ),  # Returns the search results only from the specified website or domain. By default it searches the entire web
            "X-With-Generated-Alt": "true",
            "X-With-Images-Summary": "true",
        }

    def parse_link(self, url: str) -> Dict[str, Any]:
        """
        Fetch and parse content from a web link using Jina Reader.

        Returns:
            Dict containing:
            - url: str
            - title: str
            - description: str
            - content: str
            - images: Dict
            - timestamp: Optional[str]
            - tokens: int
        """
        try:
            # Validate URL format
            if not url.startswith(("http://", "https://")):
                logger.error(f"Invalid URL format: {url}")
                raise ValueError("URL must start with http(s)://")

            # Construct the Jina Reader URL
            reader_url = f"https://r.jina.ai/{url}"
            logger.debug(f"Fetching content from: {reader_url}")

            # Fetch the content
            response = requests.get(reader_url, headers=self.get_request_headers)
            response.raise_for_status()

            # Parse JSON response
            try:
                data = response.json()  # .text
            except ValueError as e:
                logger.error(f"Invalid JSON response from {url}: {e}")
                logger.debug(f"Response content: {response.text}...")  # Log first 200 chars
                raise ValueError("Invalid JSON response from server")
            # Validate response structure
            if not isinstance(data, dict) or "data" not in data:
                logger.error(f"Malformed response from {url}")
                logger.debug(f"Full response: {data}")
                raise ValueError("Malformed response structure")

            # Extract relevant data from the response
            result_data = data.get("data", {})

            # Return structured data
            return {
                "url": result_data.get("url", ""),
                "title": result_data.get("title", ""),
                "description": result_data.get("description", ""),
                "content": result_data.get("content", ""),
                "images": result_data.get("images", {}),
                "timestamp": result_data.get("publishedTime", ""),
                "tokens": result_data.get("usage", {}).get("tokens", 0),
            }

        except requests.RequestException as e:
            logger.error(f"Error while fetching {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while parsing content from {url}: {e}")
            raise

    def search_links(self, query: str, **custom_params: Any) -> List[Dict[str, Any]]:
        """
        Search for content using Jina Reader's search mode.

        Args:
            query: Search query string (required)
            **custom_params: Optional keyword arguments that will be added as URL parameters.
                Examples:
                - gl: Country code (e.g., "DE" for Germany)
                - location: Location for search (e.g., "Berlin")
                - hl: Language code (e.g., "en" for English)
                - num: Number of results to return

                Usage:
                search_links(query="search term", gl="US", hl="en", num=10)
                This will create URL: https://s.jina.ai/?q=search+term&gl=US&hl=en&num=10

        Returns:
            List of Dicts, each containing:
            - url: str
            - title: str
            - description: str
            - content: str
            - total_tokens: int
        """
        try:
            # Validate query
            if not query or not query.strip():
                logger.error("Empty search query")
                raise ValueError("Search query cannot be empty")

            # Build query parameters
            params = {"q": query}
            # Add all custom parameters
            params.update(custom_params)

            # Construct the search URL
            search_url = "https://s.jina.ai/"
            logger.debug(f"Searching with URL: {search_url} and params: {params}")

            # Fetch the content
            response = requests.get(search_url, headers=self.search_request_headers, params=params)
            response.raise_for_status()

            # Parse JSON response
            try:
                data = response.json()
            except ValueError as e:
                logger.error(f"Invalid JSON response for search {query}: {e}")
                logger.debug(f"Response content: {response.text}...")
                raise ValueError("Invalid JSON response from server")

            # Validate response structure
            if not isinstance(data, dict) or "data" not in data:
                logger.error(f"Malformed search response for query: {query}")
                logger.debug(f"Full response: {data}")
                raise ValueError("Malformed response structure")

            # Extract relevant data from the response
            result_data = data.get("data", [{}])

            # Return list of search results
            return [
                {
                    "url": item.get("url", ""),
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "content": item.get("content", ""),
                    "total_tokens": data.get("meta", {}).get("usage", {}).get("tokens", 0),
                }
                for item in result_data
            ]

        except requests.RequestException as e:
            logger.error(f"Error while searching for {query}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while searching for {query}: {e}")
            raise

    def fetch_signal_link(self, url: str) -> Dict[str, Any]:
        """
        Fetch and parse content from a web link, returning the same structure as fetch_signal.

        Returns:
            Dict containing:
            - status: str ("new_signal" or "no_data")
            - content: Dict with parsed link data (JSON)
        """
        try:
            parsed_content = self.parse_link(url)

            # Check if any meaningful content was parsed
            if not parsed_content or not any(
                [
                    parsed_content.get("title"),
                    parsed_content.get("description"),
                    parsed_content.get("content"),
                ]
            ):
                return {"status": "no_data"}

            return {
                "status": "new_signal",
                "content": (
                    f"Title:{str(parsed_content.get('title', ''))}\n"
                    f"Description:{str(parsed_content.get('description', ''))}\n"
                    f"Content:{str(parsed_content.get('content', ''))}\n"
                    f"Timestamp:{str(parsed_content.get('timestamp', ''))}\n"
                ),
            }
        except Exception as e:
            logger.error(f"Error in fetch_link_signal: {e}")
            return {"status": "no_data"}
