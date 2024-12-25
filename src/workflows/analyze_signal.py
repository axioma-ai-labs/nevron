from typing import Optional

from loguru import logger

from src.tools.get_signal import fetch_signal


async def analyze_signal() -> Optional[str]:
    """Workflow for analyzing a signal and returning the actionable signal."""
    signal = await fetch_signal()
    if signal.get("status") == "new_data" and "news" in signal:
        news = signal["news"]
        logger.info(f"Actionable signal received: {news}")

        return news
    elif signal.get("status") == "no_data":
        logger.info("No actionable signal detected.")
        return None
    else:
        logger.warning("Received an unknown signal format or an error occurred.")
        return None
