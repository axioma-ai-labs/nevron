# from unittest.mock import MagicMock, patch

# import pytest

# from src.tools.youtube import YouTubeClient


# @pytest.fixture
# def mock_youtube_client():
#     """Mock the YouTube client."""
#     client = MagicMock()
#     return client


# def test_youtube_client_init(mock_youtube_client):
#     """Test YouTubeClient initialization with mocked client."""
#     with patch("src.tools.youtube.build", return_value=mock_youtube_client):
#         client = YouTubeClient(api_key="test_key")
#         assert client.api_key == "test_key"


# def test_search_videos(mock_youtube_client):
#     """Test searching for videos."""
#     mock_response: dict = {
#         "items": [{"id": {"videoId": "test_id"}, "snippet": {"title": "Test Video"}}]
#     }

#     mock_youtube_client.search().list().execute.return_value = mock_response

#     with patch("src.tools.youtube.build", return_value=mock_youtube_client):
#         client = YouTubeClient()
#         results = client.search_videos("test query")

#         assert len(results) == 1
#         assert results[0]["id"]["videoId"] == "test_id"


# def test_get_video_details(mock_youtube_client):
#     """Test getting video details."""
#     mock_video_response: dict = {
#         "items": [
#             {
#                 "id": "test_id",
#                 "snippet": {"title": "Test Video"},
#                 "statistics": {"viewCount": "100"},
#             }
#         ]
#     }

#     mock_youtube_client.videos().list().execute.return_value = mock_video_response

#     with patch("src.tools.youtube.build", return_value=mock_youtube_client):
#         client = YouTubeClient()
#         result = client.get_video_details("test_id")

#         assert result["id"] == "test_id"
#         assert result["statistics"]["viewCount"] == "100"
