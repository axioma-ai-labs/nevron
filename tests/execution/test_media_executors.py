import unittest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import SpotifyError, YouTubeError
from src.execution.media_executors import (
    RetrieveSpotifyPlaylistExecutor,
    RetrieveYouTubePlaylistExecutor,
    SearchSpotifySongExecutor,
    SearchYouTubeVideoExecutor,
)


class TestSearchYouTubeVideoExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked YouTube client
        self.patcher = patch("src.execution.media_executors.YouTubeTool")
        self.mock_youtube_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_youtube_tool.return_value = self.mock_client
        self.executor = SearchYouTubeVideoExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_initialize_client(self):
        """Test that _initialize_client returns a YouTubeTool instance."""
        # Create a new instance without calling __init__
        executor = SearchYouTubeVideoExecutor.__new__(SearchYouTubeVideoExecutor)

        # Mock hasn't been called yet for this new instance
        self.mock_youtube_tool.reset_mock()

        # Call the method directly
        client = executor._initialize_client()

        # Verify the result
        self.assertEqual(client, self.mock_youtube_tool.return_value)
        self.mock_youtube_tool.assert_called_once()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["query", "max_results"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful YouTube video search."""
        # Set up mock return value for search_videos
        mock_results: List[Dict[str, Any]] = [
            {"id": {"videoId": "video1"}, "snippet": {"title": "Test Video 1"}},
            {"id": {"videoId": "video2"}, "snippet": {"title": "Test Video 2"}},
        ]
        self.mock_client.search_videos = MagicMock(return_value=mock_results)

        # Test with valid context
        context: Dict[str, Any] = {"query": "test search", "max_results": 5}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Found 2 matching videos")
        self.mock_client.search_videos.assert_called_once_with("test search", max_results=5)

    @pytest.mark.asyncio
    async def test_execute_no_results(self):
        """Test when no results are found."""
        # Set up mock to return empty list
        self.mock_client.search_videos = MagicMock(return_value=[])

        # Test with valid context
        context: Dict[str, Any] = {"query": "nonexistent video", "max_results": 5}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No matching videos found")
        self.mock_client.search_videos.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing query
        context: Dict[str, int] = {
            "max_results": 5
            # Missing "query"
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required query in context")
        self.mock_client.search_videos.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_youtube_error(self):
        """Test handling of YouTube errors."""
        # Set up mock to raise YouTubeError
        error_message: str = "API quota exceeded"
        self.mock_client.search_videos = MagicMock(side_effect=YouTubeError(error_message))

        # Test with valid context
        context: Dict[str, Any] = {"query": "test search", "max_results": 5}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to search YouTube", str(message))
        self.assertIn("API quota exceeded", str(message))
        self.mock_client.search_videos.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Unexpected failure"
        self.mock_client.search_videos = MagicMock(side_effect=Exception(error_message))

        # Test with valid context
        context: Dict[str, Any] = {"query": "test search", "max_results": 5}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while searching YouTube", str(message))
        self.assertIn("Unexpected failure", str(message))
        self.mock_client.search_videos.assert_called_once()


class TestRetrieveYouTubePlaylistExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked YouTube client
        self.patcher = patch("src.execution.media_executors.YouTubeTool")
        self.mock_youtube_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_youtube_tool.return_value = self.mock_client
        self.executor = RetrieveYouTubePlaylistExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_initialize_client(self):
        """Test that _initialize_client returns a YouTubeTool instance."""
        # Create a new instance without calling __init__
        executor = RetrieveYouTubePlaylistExecutor.__new__(RetrieveYouTubePlaylistExecutor)

        # Mock hasn't been called yet for this new instance
        self.mock_youtube_tool.reset_mock()

        # Call the method directly
        client = executor._initialize_client()

        # Verify the result
        self.assertEqual(client, self.mock_youtube_tool.return_value)
        self.mock_youtube_tool.assert_called_once()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["playlist_id", "max_results"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful YouTube playlist retrieval."""
        # Set up mock return value for get_playlist_items
        mock_results: List[Dict[str, Any]] = [
            {"snippet": {"title": "Playlist Item 1", "resourceId": {"videoId": "video1"}}},
            {"snippet": {"title": "Playlist Item 2", "resourceId": {"videoId": "video2"}}},
        ]
        self.mock_client.get_playlist_items = MagicMock(return_value=mock_results)

        # Test with valid context
        context: Dict[str, Any] = {"playlist_id": "PL1234567890", "max_results": 50}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Retrieved 2 items from playlist")
        self.mock_client.get_playlist_items.assert_called_once_with("PL1234567890", max_results=50)

    @pytest.mark.asyncio
    async def test_execute_empty_playlist(self):
        """Test when playlist is empty."""
        # Set up mock to return empty list
        self.mock_client.get_playlist_items = MagicMock(return_value=[])

        # Test with valid context
        context: Dict[str, Any] = {"playlist_id": "PL1234567890", "max_results": 50}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No items found in playlist")
        self.mock_client.get_playlist_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing playlist_id
        context: Dict[str, int] = {
            "max_results": 50
            # Missing "playlist_id"
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required playlist_id in context")
        self.mock_client.get_playlist_items.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_youtube_error(self):
        """Test handling of YouTube errors."""
        # Set up mock to raise YouTubeError
        error_message: str = "Playlist not found"
        self.mock_client.get_playlist_items = MagicMock(side_effect=YouTubeError(error_message))

        # Test with valid context
        context: Dict[str, Any] = {"playlist_id": "invalid_playlist", "max_results": 50}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to retrieve YouTube playlist", str(message))
        self.assertIn("Playlist not found", str(message))
        self.mock_client.get_playlist_items.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Server error"
        self.mock_client.get_playlist_items = MagicMock(side_effect=Exception(error_message))

        # Test with valid context
        context: Dict[str, Any] = {"playlist_id": "PL1234567890", "max_results": 50}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while retrieving YouTube playlist", str(message))
        self.assertIn("Server error", str(message))
        self.mock_client.get_playlist_items.assert_called_once()


class TestSearchSpotifySongExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Spotify client
        self.patcher = patch("src.execution.media_executors.SpotifyTool")
        self.mock_spotify_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_spotify_tool.return_value = self.mock_client
        self.executor = SearchSpotifySongExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_initialize_client(self):
        """Test that _initialize_client returns a SpotifyTool instance."""
        # Create a new instance without calling __init__
        executor = SearchSpotifySongExecutor.__new__(SearchSpotifySongExecutor)

        # Mock hasn't been called yet for this new instance
        self.mock_spotify_tool.reset_mock()

        # Call the method directly
        client = executor._initialize_client()

        # Verify the result
        self.assertEqual(client, self.mock_spotify_tool.return_value)
        self.mock_spotify_tool.assert_called_once()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["query", "limit", "access_token"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Spotify song search."""
        # Set up mock return value for search_song
        mock_results: List[Dict[str, Any]] = [
            {"id": "track1", "name": "Song 1", "artists": [{"name": "Artist 1"}]},
            {"id": "track2", "name": "Song 2", "artists": [{"name": "Artist 2"}]},
        ]
        self.mock_client.search_song = AsyncMock(return_value=mock_results)

        # Test with valid context
        context: Dict[str, Any] = {"query": "test song", "limit": 5, "access_token": "dummy_token"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Found 2 matching songs")
        self.mock_client.search_song.assert_called_once_with("dummy_token", "test song", limit=5)

    @pytest.mark.asyncio
    async def test_execute_no_results(self):
        """Test when no songs are found."""
        # Set up mock to return empty list
        self.mock_client.search_song = AsyncMock(return_value=[])

        # Test with valid context
        context: Dict[str, Any] = {
            "query": "nonexistent song",
            "limit": 5,
            "access_token": "dummy_token",
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No matching songs found")
        self.mock_client.search_song.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing query
        context: Dict[str, Any] = {
            "limit": 5,
            "access_token": "dummy_token",
            # Missing "query"
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required query in context")
        self.mock_client.search_song.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_spotify_error(self):
        """Test handling of Spotify errors."""
        # Set up mock to raise SpotifyError
        error_message: str = "Invalid access token"
        self.mock_client.search_song = AsyncMock(side_effect=SpotifyError(error_message))

        # Test with valid context
        context: Dict[str, Any] = {
            "query": "test song",
            "limit": 5,
            "access_token": "invalid_token",
        }
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to search Spotify", str(message))
        self.assertIn("Invalid access token", str(message))
        self.mock_client.search_song.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Connection error"
        self.mock_client.search_song = AsyncMock(side_effect=Exception(error_message))

        # Test with valid context
        context: Dict[str, Any] = {"query": "test song", "limit": 5, "access_token": "dummy_token"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while searching Spotify", str(message))
        self.assertIn("Connection error", str(message))
        self.mock_client.search_song.assert_called_once()


class TestRetrieveSpotifyPlaylistExecutor(unittest.TestCase):
    def setUp(self):
        # Set up the executor with a mocked Spotify client
        self.patcher = patch("src.execution.media_executors.SpotifyTool")
        self.mock_spotify_tool = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_spotify_tool.return_value = self.mock_client
        self.executor = RetrieveSpotifyPlaylistExecutor()

    def tearDown(self):
        self.patcher.stop()

    def test_initialize_client(self):
        """Test that _initialize_client returns a SpotifyTool instance."""
        # Create a new instance without calling __init__
        executor = RetrieveSpotifyPlaylistExecutor.__new__(RetrieveSpotifyPlaylistExecutor)

        # Mock hasn't been called yet for this new instance
        self.mock_spotify_tool.reset_mock()

        # Call the method directly
        client = executor._initialize_client()

        # Verify the result
        self.assertEqual(client, self.mock_spotify_tool.return_value)
        self.mock_spotify_tool.assert_called_once()

    def test_get_required_context(self):
        """Test that required context fields are returned."""
        required = self.executor.get_required_context()
        self.assertEqual(required, ["access_token"])

    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful Spotify playlist retrieval."""
        # Set up mock return value for get_user_playlists
        mock_results: List[Dict[str, Any]] = [
            {"id": "playlist1", "name": "My Playlist 1", "tracks": {"total": 10}},
            {"id": "playlist2", "name": "My Playlist 2", "tracks": {"total": 20}},
        ]
        self.mock_client.get_user_playlists = AsyncMock(return_value=mock_results)

        # Test with valid context
        context: Dict[str, str] = {"access_token": "dummy_token"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertTrue(success)
        self.assertEqual(message, "Retrieved 2 playlists")
        self.mock_client.get_user_playlists.assert_called_once_with("dummy_token")

    @pytest.mark.asyncio
    async def test_execute_no_playlists(self):
        """Test when no playlists are found."""
        # Set up mock to return empty list
        self.mock_client.get_user_playlists = AsyncMock(return_value=[])

        # Test with valid context
        context: Dict[str, str] = {"access_token": "dummy_token"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "No playlists found")
        self.mock_client.get_user_playlists.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_missing_context(self):
        """Test execution with missing required context."""
        # Test with missing access_token
        context: Dict[str, Any] = {}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertEqual(message, "Missing required arguments in context")
        self.mock_client.get_user_playlists.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_spotify_error(self):
        """Test handling of Spotify errors."""
        # Set up mock to raise SpotifyError
        error_message: str = "Authorization failed"
        self.mock_client.get_user_playlists = AsyncMock(side_effect=SpotifyError(error_message))

        # Test with valid context
        context: Dict[str, str] = {"access_token": "expired_token"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Failed to retrieve Spotify playlists", str(message))
        self.assertIn("Authorization failed", str(message))
        self.mock_client.get_user_playlists.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_unexpected_error(self):
        """Test handling of unexpected errors."""
        # Set up mock to raise generic Exception
        error_message: str = "Service unavailable"
        self.mock_client.get_user_playlists = AsyncMock(side_effect=Exception(error_message))

        # Test with valid context
        context: Dict[str, str] = {"access_token": "dummy_token"}
        success, message = await self.executor.execute(context)

        # Verify results
        self.assertFalse(success)
        self.assertIn("Unexpected error while retrieving Spotify playlists", str(message))
        self.assertIn("Service unavailable", str(message))
        self.mock_client.get_user_playlists.assert_called_once()


if __name__ == "__main__":
    unittest.main()
