from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.core.exceptions import SpotifyError, YouTubeError
from src.execution.base import ActionExecutor
from src.tools.spotify import SpotifyTool
from src.tools.youtube import YouTubeTool


class SearchYouTubeVideoExecutor(ActionExecutor):
    """Executor for searching YouTube videos."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> YouTubeTool:
        """Initialize YouTube tool client."""
        return YouTubeTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["query", "max_results"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute YouTube video search."""
        try:
            if not self.validate_context(context):
                return False, "Missing required query in context"

            query = context.get("query")
            max_results = context.get("max_results", 5)

            logger.info(f"Searching YouTube for: {query}")
            results = self.client.search_videos(query, max_results=max_results)

            if results:
                return True, f"Found {len(results)} matching videos"
            return False, "No matching videos found"

        except YouTubeError as e:
            error_msg = f"Failed to search YouTube: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while searching YouTube: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class RetrieveYouTubePlaylistExecutor(ActionExecutor):
    """Executor for retrieving YouTube playlist items."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> YouTubeTool:
        """Initialize YouTube tool client."""
        return YouTubeTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["playlist_id", "max_results"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute YouTube playlist retrieval."""
        try:
            if not self.validate_context(context):
                return False, "Missing required playlist_id in context"

            playlist_id = context.get("playlist_id")
            max_results = context.get("max_results", 50)

            logger.info(f"Retrieving YouTube playlist: {playlist_id}")
            results = self.client.get_playlist_items(playlist_id, max_results=max_results)

            if results:
                return True, f"Retrieved {len(results)} items from playlist"
            return False, "No items found in playlist"

        except YouTubeError as e:
            error_msg = f"Failed to retrieve YouTube playlist: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while retrieving YouTube playlist: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class SearchSpotifySongExecutor(ActionExecutor):
    """Executor for searching Spotify songs."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> SpotifyTool:
        """Initialize Spotify tool client."""
        return SpotifyTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["query", "limit", "access_token"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Spotify song search."""
        try:
            if not self.validate_context(context):
                return False, "Missing required query in context"

            query = context.get("query")
            limit = context.get("limit", 1)
            access_token = context.get("access_token")
            logger.info(f"Searching Spotify for: {query}")
            results = await self.client.search_song(access_token, query, limit=limit)

            if results:
                return True, f"Found {len(results)} matching songs"
            return False, "No matching songs found"

        except SpotifyError as e:
            error_msg = f"Failed to search Spotify: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while searching Spotify: {str(e)}"
            logger.error(error_msg)
            return False, error_msg


class RetrieveSpotifyPlaylistExecutor(ActionExecutor):
    """Executor for retrieving Spotify playlists."""

    def __init__(self):
        super().__init__()
        self.client = self._initialize_client()

    def _initialize_client(self) -> SpotifyTool:
        """Initialize Spotify tool client."""
        return SpotifyTool()

    def get_required_context(self) -> List[str]:
        """Get required context fields."""
        return ["access_token"]

    async def execute(self, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Execute Spotify playlist retrieval."""
        if not self.validate_context(context):
            return False, "Missing required arguments in context"
        try:
            access_token = context.get("access_token")
            logger.info("Retrieving Spotify playlists")
            playlists = await self.client.get_user_playlists(access_token)

            if playlists:
                return True, f"Retrieved {len(playlists)} playlists"
            return False, "No playlists found"

        except SpotifyError as e:
            error_msg = f"Failed to retrieve Spotify playlists: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error while retrieving Spotify playlists: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
