import logging
from functools import lru_cache

from googleapiclient.discovery import build

from src.core.config import settings


logger = logging.getLogger(__name__)


class YouTubeClient:
    """YouTube API client for handling all YouTube-related operations."""

    def __init__(self, api_key=None):
        """Initialize YouTube client with optional API key override."""
        self.api_key = api_key or settings.YOUTUBE_API_KEY

    @property
    @lru_cache(maxsize=1)
    def client(self):
        """Cached YouTube API client instance."""
        return build("youtube", "v3", developerKey=self.api_key)

    def search_videos(self, query, max_results=5, **kwargs):
        """
        Search for videos on YouTube.

        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            **kwargs: Additional parameters to pass to the API

        Returns:
            list: List of video items
        """
        params = {
            "q": query,
            "part": "snippet",
            "maxResults": max_results,
            "type": "video",
            **kwargs,
        }

        response = self.client.search().list(**params).execute()
        return response.get("items", [])

    def get_video_details(self, video_id, parts=None):
        """
        Retrieve details for a specific video.

        Args:
            video_id (str): YouTube video ID
            parts (list): List of parts to retrieve (e.g., ['snippet', 'statistics'])

        Returns:
            dict: Video details
        """
        parts = parts or ["snippet", "statistics"]
        response = self.client.videos().list(id=video_id, part=",".join(parts)).execute()
        return response.get("items", [])[0]

    def get_channel_details(self, channel_id, parts=None):
        """
        Retrieve details for a specific channel.

        Args:
            channel_id (str): YouTube channel ID
            parts (list): List of parts to retrieve (e.g., ['snippet', 'statistics'])

        Returns:
            dict: Channel details
        """
        parts = parts or ["snippet", "statistics"]
        response = self.client.channels().list(id=channel_id, part=",".join(parts)).execute()
        return response.get("items", [])[0]

    def get_comments(self, video_id, max_results=100):
        """
        Retrieve comments for a video.

        Args:
            video_id (str): YouTube video ID
            max_results (int): Maximum number of comments to return

        Returns:
            list: List of comments or empty list if comments are disabled
        """
        try:
            # First check if comments are enabled by getting video details
            video_details = self.get_video_details(video_id, parts=["statistics"])
            if "commentCount" not in video_details.get("statistics", {}):
                logger.info(f"Comments are disabled for video {video_id}")
                return []

            # If comments are enabled, proceed to fetch them
            response = (
                self.client.commentThreads()
                .list(videoId=video_id, part="snippet", maxResults=max_results)
                .execute()
            )
            return response.get("items", [])
        except Exception as e:
            logger.error(f"Error fetching comments: {str(e)}")
            return []

    def get_playlist_items(self, playlist_id=None, max_results=50):
        """
        Retrieve items from a playlist.

        Args:
            playlist_id (str, optional): YouTube playlist ID. If None, uses ID from settings
            max_results (int): Maximum number of results to return

        Returns:
            list: List of playlist items
        """
        playlist_id = playlist_id or settings.YOUTUBE_PLAYLIST_ID
        response = (
            self.client.playlistItems()
            .list(playlistId=playlist_id, part="snippet", maxResults=max_results)
            .execute()
        )
        return response.get("items", [])
