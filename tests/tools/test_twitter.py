# from unittest.mock import MagicMock, patch

# import pytest
# from requests_html import HTMLSession

# from src.core.exceptions import TwitterError as TwitterPostError
# from src.tools.twitter import post_twitter_thread, upload_media_v1


# @pytest.fixture
# def mock_twitter_v1():
#     """Mock Twitter API v1.1 client."""
#     return MagicMock()


# @pytest.fixture
# def mock_twitter_v2():
#     """Mock Twitter API v2 client."""
#     return MagicMock()


# @pytest.mark.asyncio
# async def test_upload_media_v1_success(mock_twitter_v1):
#     """Test successful media upload using Twitter API v1.1."""
#     # Arrange
#     mock_media_id = "123456789"
#     mock_media = MagicMock()
#     mock_media.media_id = mock_media_id

#     with patch("src.tools.twitter.get_twitter_conn_v1", return_value=mock_twitter_v1):
#         with patch.object(HTMLSession, "get", return_value=MagicMock(content=b"image data")):
#             with patch("PIL.Image.open", return_value=MagicMock()):
#                 mock_twitter_v1.media_upload.return_value = mock_media

#                 # Act
#                 media_id = await upload_media_v1("http://example.com/image.jpg")

#                 # Assert
#                 assert media_id == mock_media_id
#                 mock_twitter_v1.media_upload.assert_called_once()


# @pytest.mark.asyncio
# async def test_upload_media_v1_failure(mock_twitter_v1):
#     """Test media upload failure."""
#     with patch("src.tools.twitter.get_twitter_conn_v1", return_value=mock_twitter_v1):
#         with patch.object(HTMLSession, "get", side_effect=Exception("Network error")):
#             # Act
#             media_id = await upload_media_v1("http://example.com/image.jpg")

#             # Assert
#             assert media_id is None


# @pytest.mark.asyncio
# async def test_post_twitter_thread_success(mock_twitter_v2):
#     """Test posting a Twitter thread successfully."""
#     tweets = {"tweet1": "Hello world!", "tweet2": "Follow-up tweet."}
#     mock_tweet_id_1 = "1111111"
#     mock_tweet_id_2 = "2222222"

#     mock_tweet_response_1 = MagicMock(data={"id": mock_tweet_id_1})
#     mock_tweet_response_2 = MagicMock(data={"id": mock_tweet_id_2})

#     with patch("src.tools.twitter.get_twitter_conn_v2", return_value=mock_twitter_v2):
#         # Mock the async create_tweet method
#         mock_twitter_v2.create_tweet.side_effect = [mock_tweet_response_1, mock_tweet_response_2]

#         # Act
#         result = await post_twitter_thread(tweets)

#         # Assert
#         assert result == [mock_tweet_id_1, mock_tweet_id_2]
#         assert mock_twitter_v2.create_tweet.call_count == 2


# @pytest.mark.asyncio
# async def test_post_twitter_thread_with_media(mock_twitter_v2, mock_twitter_v1):
#     """Test posting a Twitter thread with media."""
#     tweets = {"tweet1": "Hello world!", "tweet2": "Follow-up tweet."}
#     media_url = "http://example.com/image.jpg"
#     mock_media_id = "9999999"
#     mock_tweet_id_1 = "1111111"
#     mock_tweet_id_2 = "2222222"

#     mock_tweet_response_1 = MagicMock(data={"id": mock_tweet_id_1})
#     mock_tweet_response_2 = MagicMock(data={"id": mock_tweet_id_2})

#     with patch("src.tools.twitter.get_twitter_conn_v2", return_value=mock_twitter_v2):
#         with patch("src.tools.twitter.upload_media_v1", return_value=mock_media_id):
#             # Mock the async create_tweet method
#             mock_twitter_v2.create_tweet.side_effect = [
#                 mock_tweet_response_1,
#                 mock_tweet_response_2,
#             ]

#             # Act
#             result = await post_twitter_thread(tweets, media_url=media_url)

#             # Assert
#             assert result == [mock_tweet_id_1, mock_tweet_id_2]
#             assert mock_twitter_v2.create_tweet.call_count == 2
#             mock_twitter_v2.create_tweet.assert_any_call(
#                 text="Hello world!", media_ids=[mock_media_id]
#             )


# @pytest.mark.asyncio
# async def test_post_twitter_thread_failure(mock_twitter_v2):
#     """Test failure during posting a Twitter thread."""
#     tweets = {"tweet1": "Hello world!"}

#     with patch("src.tools.twitter.get_twitter_conn_v2", return_value=mock_twitter_v2):
#         mock_twitter_v2.create_tweet.side_effect = Exception("Twitter API error")

#         # Act & Assert
#         with pytest.raises(TwitterPostError):
#             await post_twitter_thread(tweets)
