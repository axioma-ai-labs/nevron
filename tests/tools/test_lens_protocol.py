from unittest.mock import Mock, patch

import pytest

from src.tools.lens_protocol import LensProtocolTool


@pytest.fixture
def mock_settings():
    with patch("src.tools.lens_protocol.settings") as mock_settings:
        mock_settings.LENS_API_KEY = "test_api_key"
        mock_settings.LENS_PROFILE_ID = "default_profile_id"
        yield mock_settings


@pytest.fixture
def mock_gql_client():
    with patch("src.tools.lens_protocol.Client") as mock_client:
        yield mock_client


@pytest.fixture
def mock_transport():
    with patch("src.tools.lens_protocol.RequestsHTTPTransport") as mock_transport:
        yield mock_transport


class TestLensProtocolTool:
    def test_initialization_success(self, mock_settings, mock_gql_client, mock_transport):
        """Test successful initialization"""
        lens_tool = LensProtocolTool()

        mock_transport.assert_called_once_with(
            url="https://api-v2.lens.dev", headers={"x-api-key": "test_api_key"}
        )
        mock_gql_client.assert_called_once()
        assert lens_tool.profile_id == "default_profile_id"

    def test_initialization_failure(self, mock_settings, mock_gql_client):
        """Test initialization failure"""
        mock_settings.LENS_API_KEY = ""

        lens_tool = LensProtocolTool()

        assert lens_tool.client is None

    def test_get_profile_success(self, mock_settings):
        """Test successful profile retrieval"""
        lens_tool = LensProtocolTool()
        # Mock GraphQL response
        mock_client = Mock()
        mock_client.execute.return_value = {
            "profile": {
                "id": "test.lens",
                "handle": "test_handle",
                "bio": "Test bio",
                "stats": {"totalFollowers": 100, "totalFollowing": 50},
            }
        }
        lens_tool.client = mock_client

        result = lens_tool.get_profile("test.lens")

        assert result == {
            "id": "test.lens",
            "handle": "test_handle",
            "bio": "Test bio",
            "followers": 100,
            "following": 50,
        }

    def test_get_profile_default_id(self, mock_settings):
        """Test profile retrieval with default profile ID"""
        lens_tool = LensProtocolTool()
        mock_client = Mock()
        mock_client.execute.return_value = {
            "profile": {
                "id": "default_profile_id",
                "handle": "test_handle",
                "bio": "Test bio",
                "stats": {"totalFollowers": 100, "totalFollowing": 50},
            }
        }
        lens_tool.client = mock_client

        result = lens_tool.get_profile()

        assert result is not None
        assert result["id"] == "default_profile_id"
        mock_client.execute.assert_called_once()

    def test_get_profile_not_initialized(self, mock_settings):
        """Test profile retrieval with uninitialized client"""
        lens_tool = LensProtocolTool()
        lens_tool.client = None

        result = lens_tool.get_profile("test.lens")

        assert result is None

    def test_publish_content_success(self, mock_settings):
        """Test successful content publication"""
        lens_tool = LensProtocolTool()
        # Mock GraphQL response
        mock_client = Mock()
        mock_client.execute.return_value = {
            "createPostTypedData": {
                "id": "pub-123",
                "content": "Test content",
                "createdAt": "2024-01-01T12:00:00Z",
            }
        }
        lens_tool.client = mock_client

        result = lens_tool.publish_content("Test content")

        assert result == {
            "id": "pub-123",
            "content": "Test content",
            "timestamp": "2024-01-01T12:00:00Z",
        }

    def test_publish_content_failure(self, mock_settings):
        """Test content publication failure"""
        lens_tool = LensProtocolTool()
        mock_client = Mock()
        mock_client.execute.side_effect = Exception("Publication failed")
        lens_tool.client = mock_client

        result = lens_tool.publish_content("Test content")

        assert result is None

    def test_fetch_content_success(self, mock_settings):
        """Test successful content fetching"""
        lens_tool = LensProtocolTool()
        # Mock GraphQL response
        mock_client = Mock()
        mock_client.execute.return_value = {
            "explorePublications": {
                "items": [
                    {
                        "id": "pub-123",
                        "profile": {"id": "profile-123"},
                        "metadata": {"content": "Test content"},
                        "createdAt": "2024-01-01T12:00:00Z",
                        "stats": {
                            "totalAmountOfComments": 10,
                            "totalAmountOfMirrors": 5,
                            "totalAmountOfReactions": 20,
                        },
                    }
                ]
            }
        }
        lens_tool.client = mock_client

        query_params = {"limit": 1, "orderBy": "TOP_REACTED"}
        result = lens_tool.fetch_content(query_params)

        assert len(result) == 1
        assert result[0] == {
            "id": "pub-123",
            "profile_id": "profile-123",
            "content": "Test content",
            "timestamp": "2024-01-01T12:00:00Z",
            "stats": {"comments": 10, "mirrors": 5, "reactions": 20},
        }

    def test_fetch_content_empty_result(self, mock_settings):
        """Test content fetching with empty result"""
        lens_tool = LensProtocolTool()
        mock_client = Mock()
        mock_client.execute.return_value = {"explorePublications": {"items": []}}
        lens_tool.client = mock_client

        query_params = {"limit": 1}
        result = lens_tool.fetch_content(query_params)

        assert result == []

    def test_fetch_content_not_initialized(self, mock_settings):
        """Test content fetching with uninitialized client"""
        lens_tool = LensProtocolTool()
        lens_tool.client = None

        query_params = {"limit": 1}
        result = lens_tool.fetch_content(query_params)

        assert result == []
