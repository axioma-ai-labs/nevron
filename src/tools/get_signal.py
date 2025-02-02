from datetime import datetime, timedelta
from typing import Dict

import httpx
from loguru import logger

from src.core.config import settings
from src.core.exceptions import CoinstatsError


#: Coinstatst API
COINSTATS_BASE_URL = "https://openapiv1.coinstats.app"

#: Coinstats API headers
COINSTATS_HEADERS = {
    "accept": "application/json",
    "X-API-KEY": settings.COINSTATS_API_KEY,
}


async def get_coinstats_news() -> Dict[str, str]:
    """get news from coinstats api"""
    logger.debug("RETRIEVING NEWS")
    try:
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        url = (
            f"{COINSTATS_BASE_URL}/news?limit=30&"
            f"from={yesterday.strftime('%Y-%m-%d')}&"
            f"to={now.strftime('%Y-%m-%d')}"
        )

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=COINSTATS_HEADERS)
            response.raise_for_status()
            data = response.json()

        logger.debug(f"COINSTATS NEWS | SUCCESSFULLY RETRIEVED {len(data['result'])} ARTICLES")
        return data
    except Exception as e:
        logger.error(f"ERROR RETRIEVING NEWS: {str(e)}")
        raise CoinstatsError("News data currently unavailable")


async def fetch_signal() -> dict:
    """
    Fetch a crypto signal from the Coinstats API.

    Returns:
        dict: Parsed JSON response containing actionable crypto news or updates.
            Format: {"status": str, "content": str}
            - status: "new_signal", "no_data", or "error"
            - content: title of the latest news article if status is "new_signal"
    """
    try:
        data = await get_coinstats_news()
        if data and data.get("result") and len(data["result"]) > 0:
            latest_news = data["result"][0]
            logger.debug(f"Signal fetched: {latest_news}")
            signal = latest_news.get("title", None)  # type: ignore
            if not signal:
                return {"status": "no_data"}
            return {"status": "new_signal", "content": signal}
        else:
            logger.error("No news data available in the response")
            return {"status": "no_data"}
    except CoinstatsError as e:
        logger.error(f"Error fetching signal from Coinstats: {e}")
        return {"status": "error"}
