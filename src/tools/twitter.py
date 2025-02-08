import asyncio
import io
from typing import List, Optional

import tweepy
from loguru import logger
from PIL import Image
from requests_html import HTMLSession

from src.core.config import settings
from src.core.exceptions import TwitterError as TwitterPostError


class TwitterTool:
    """Tool for interacting with the Twitter API."""

    def __init__(self):
        """Initialize the Twitter tool with API connections."""
        self.client_v1 = self._get_twitter_conn_v1()
        self.client_v2 = self._get_twitter_conn_v2()

    def _get_twitter_conn_v1(self) -> tweepy.API:
        """Get Twitter API v1.1 connection."""
        auth = tweepy.OAuth1UserHandler(settings.TWITTER_API_KEY, settings.TWITTER_API_SECRET_KEY)
        auth.set_access_token(settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)
        return tweepy.API(auth)

    def _get_twitter_conn_v2(self) -> tweepy.Client:
        """Get Twitter API v2 connection."""
        return tweepy.Client(
            consumer_key=settings.TWITTER_API_KEY,
            consumer_secret=settings.TWITTER_API_SECRET_KEY,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
        )

    async def upload_media(self, url: str) -> Optional[str]:
        """Upload media to Twitter using API v1.1."""
        try:
            # Fetch the media
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                )
            }
            session = HTMLSession()
            response = session.get(url, headers=headers)
            response.raise_for_status()
            file_like_object = io.BytesIO(response.content)

            # Process the image
            image = Image.open(file_like_object)
            grayscale = image.convert("L")
            processed_file = io.BytesIO()
            grayscale.save(processed_file, format="JPEG")
            processed_file.seek(0)

            # Upload media
            media = self.client_v1.media_upload(filename="image.jpg", file=processed_file)
            logger.debug(f"Media uploaded successfully with media_id: {media.media_id}")
            return media.media_id
        except Exception as e:
            logger.error(f"Error uploading media: {e}")
            return None

    async def post_thread(self, tweets: dict, media_url: Optional[str] = None) -> List[int]:
        """Post a thread of tweets, optionally with media."""
        tweet_ids = []
        previous_tweet_id = None
        media_id = None

        try:
            # Upload media if provided
            if media_url:
                media_id = await self.upload_media(media_url)

            for idx, key in enumerate(sorted(tweets.keys())):
                tweet_text = tweets[key]
                if idx == 0:
                    # First tweet, optionally include media
                    if media_id:
                        tweet_response = self.client_v2.create_tweet(
                            text=tweet_text, media_ids=[media_id]
                        )
                    else:
                        tweet_response = self.client_v2.create_tweet(text=tweet_text)
                else:
                    tweet_response = self.client_v2.create_tweet(
                        text=tweet_text, in_reply_to_tweet_id=previous_tweet_id
                    )

                tweet_id = tweet_response.data["id"]
                tweet_ids.append(tweet_id)
                logger.debug(f"Tweet {key} posted successfully with ID: {tweet_id}")
                previous_tweet_id = tweet_id

                # Sleep for 3 seconds to avoid rate limits
                await asyncio.sleep(3)
        except Exception as e:
            logger.error(f"Error posting tweet thread: {e}")
            raise TwitterPostError from e

        return tweet_ids
