from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.config import settings
from src.core.exceptions import TwitterError as TwitterPostError
from src.tools.twitter import TwitterTool


@pytest.fixture
def twitter_tool():
    """Fixture to create a TwitterTool instance."""
    return TwitterTool()


@pytest.fixture
def mock_twitter_v1():
    """Mock Twitter API v1.1 client."""
    return MagicMock()


@pytest.fixture
def mock_twitter_v2():
    """Mock Twitter API v2 client."""
    return MagicMock()


@pytest.mark.asyncio
async def test_upload_media_success(twitter_tool, mock_twitter_v1):
    """Test successful media upload using Twitter API v1.1."""
    # Arrange
    mock_media_id = "123456789"
    mock_media = MagicMock()
    mock_media.media_id = mock_media_id

    # Mock the file processing chain
    mock_file = MagicMock()
    mock_file.seek = MagicMock()

    with (
        patch.object(twitter_tool, "client_v1", mock_twitter_v1),
        patch(
            "src.tools.twitter.HTMLSession",
            return_value=MagicMock(
                get=MagicMock(
                    return_value=MagicMock(content=b"image data", raise_for_status=MagicMock())
                )
            ),
        ),
        patch(
            "src.tools.twitter.Image.open",
            return_value=MagicMock(convert=MagicMock(return_value=MagicMock(save=MagicMock()))),
        ),
        patch("src.tools.twitter.io.BytesIO", return_value=mock_file),
    ):
        mock_twitter_v1.media_upload.return_value = mock_media

        # Act
        media_id = await twitter_tool.upload_media("http://example.com/image.jpg")

        # Assert
        assert media_id == mock_media_id
        mock_twitter_v1.media_upload.assert_called_once()


@pytest.mark.asyncio
async def test_upload_media_failure(twitter_tool, mock_twitter_v1):
    """Test media upload failure."""
    with patch.object(twitter_tool, "client_v1", mock_twitter_v1):
        mock_twitter_v1.media_upload.side_effect = Exception("Upload failed")

        # Act
        media_id = await twitter_tool.upload_media("http://example.com/image.jpg")

        # Assert
        assert media_id is None


@pytest.mark.asyncio
async def test_post_thread_success(twitter_tool, mock_twitter_v2):
    """Test posting a Twitter thread successfully."""
    # Arrange
    tweets = {"tweet1": "Hello world!", "tweet2": "Follow-up tweet."}
    mock_tweet_id_1 = "1111111"
    mock_tweet_id_2 = "2222222"

    mock_tweet_response_1 = MagicMock(data={"id": mock_tweet_id_1})
    mock_tweet_response_2 = MagicMock(data={"id": mock_tweet_id_2})

    with patch.object(twitter_tool, "client_v2", mock_twitter_v2):
        mock_twitter_v2.create_tweet.side_effect = [mock_tweet_response_1, mock_tweet_response_2]

        # Act
        result = await twitter_tool.post_thread(tweets)

        # Assert
        assert result == [mock_tweet_id_1, mock_tweet_id_2]
        assert mock_twitter_v2.create_tweet.call_count == 2


@pytest.mark.asyncio
async def test_post_thread_with_media(twitter_tool, mock_twitter_v2):
    """Test posting a Twitter thread with media."""
    # Arrange
    tweets = {"tweet1": "Hello world!", "tweet2": "Follow-up tweet."}
    mock_media_id = "9999999"
    mock_tweet_id_1 = "1111111"
    mock_tweet_id_2 = "2222222"

    mock_tweet_response_1 = MagicMock(data={"id": mock_tweet_id_1})
    mock_tweet_response_2 = MagicMock(data={"id": mock_tweet_id_2})

    with (
        patch.object(twitter_tool, "client_v2", mock_twitter_v2),
        patch.object(twitter_tool, "upload_media", AsyncMock(return_value=mock_media_id)),
    ):
        mock_twitter_v2.create_tweet.side_effect = [mock_tweet_response_1, mock_tweet_response_2]

        # Act
        result = await twitter_tool.post_thread(tweets, media_url="http://example.com/image.jpg")

        # Assert
        assert result == [mock_tweet_id_1, mock_tweet_id_2]
        assert mock_twitter_v2.create_tweet.call_count == 2
        mock_twitter_v2.create_tweet.assert_any_call(text="Hello world!", media_ids=[mock_media_id])


@pytest.mark.asyncio
async def test_post_thread_failure(twitter_tool, mock_twitter_v2):
    """Test failure during posting a Twitter thread."""
    # Arrange
    tweets = {"tweet1": "Hello world!"}

    with patch.object(twitter_tool, "client_v2", mock_twitter_v2):
        mock_twitter_v2.create_tweet.side_effect = Exception("Twitter API error")

        # Act & Assert
        with pytest.raises(TwitterPostError):
            await twitter_tool.post_thread(tweets)


@pytest.mark.asyncio
async def test_twitter_credentials_used():
    """Test that Twitter credentials from config are used."""
    # We need to mock the entire TwitterTool initialization
    with (
        patch("tweepy.OAuth1UserHandler") as mock_auth,
        patch("tweepy.API") as mock_api,
        patch("tweepy.Client") as mock_client,
    ):
        # Create a new instance to trigger the initialization with our mocks
        TwitterTool()

        # Verify v1 credentials
        mock_auth.assert_called_once_with(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET_KEY)
        mock_auth.return_value.set_access_token.assert_called_once_with(
            settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET
        )
        mock_api.assert_called_once()

        # Verify v2 credentials
        mock_client.assert_called_once_with(
            consumer_key=settings.TWITTER_API_KEY,
            consumer_secret=settings.TWITTER_API_SECRET_KEY,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
        )
