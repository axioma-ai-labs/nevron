from unittest.mock import patch

import aiohttp
import pytest

from src.core.exceptions import SpotifyError
from src.tools.spotify import SpotifyTool


@pytest.fixture
def spotify_tool():
    return SpotifyTool()


@pytest.fixture
def mock_token_response():
    return {"access_token": "mock_access_token", "token_type": "Bearer", "expires_in": 3600}


@pytest.fixture
def mock_playlists_response():
    return {
        "items": [
            {"id": "playlist1", "name": "Test Playlist 1", "tracks": {"total": 10}},
            {"id": "playlist2", "name": "Test Playlist 2", "tracks": {"total": 5}},
        ]
    }


@pytest.fixture
def mock_search_response():
    return {
        "tracks": {
            "items": [{"id": "track1", "name": "Test Track", "artists": [{"name": "Test Artist"}]}]
        }
    }


class MockResponse:
    def __init__(self, data, status=200):
        self._data = data
        self.status = status

    async def json(self):
        return self._data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientError(f"HTTP {self.status}")


@pytest.mark.asyncio
async def test_authenticate_success(spotify_tool, mock_token_response):
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value = MockResponse(mock_token_response)
        token = await spotify_tool.authenticate()
        assert token == "mock_access_token"


@pytest.mark.asyncio
async def test_authenticate_failure(spotify_tool):
    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_post.return_value = MockResponse({}, status=401)
        with pytest.raises(SpotifyError):
            await spotify_tool.authenticate()


@pytest.mark.asyncio
async def test_get_user_playlists_success(spotify_tool, mock_playlists_response):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.return_value = MockResponse(mock_playlists_response)
        playlists = await spotify_tool.get_user_playlists("mock_token")
        assert len(playlists) == 2
        assert playlists[0]["name"] == "Test Playlist 1"


@pytest.mark.asyncio
async def test_search_song_success(spotify_tool, mock_search_response):
    with patch("aiohttp.ClientSession.get") as mock_get:
        mock_get.return_value = MockResponse(mock_search_response)
        tracks = await spotify_tool.search_song("mock_token", "test query")
        assert len(tracks) == 1
        assert tracks[0]["name"] == "Test Track"


@pytest.mark.asyncio
async def test_control_playback_success(spotify_tool):
    with patch("aiohttp.ClientSession.put") as mock_put:
        mock_put.return_value = MockResponse({})
        await spotify_tool.control_playback("mock_token", "play")
        mock_put.assert_called_once()


@pytest.mark.asyncio
async def test_control_playback_invalid_action(spotify_tool):
    with pytest.raises(ValueError):
        await spotify_tool.control_playback("mock_token", "invalid_action")


@pytest.mark.asyncio
async def test_control_playback_failure(spotify_tool):
    with patch("aiohttp.ClientSession.put") as mock_put:
        mock_put.return_value = MockResponse({}, status=403)
        with pytest.raises(SpotifyError):
            await spotify_tool.control_playback("mock_token", "play")
