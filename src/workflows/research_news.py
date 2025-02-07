from typing import Optional

from loguru import logger

from src.llm.llm import LLM
from src.tools.perplexity import PerplexityTool
from src.tools.twitter import TwitterTool


async def analyze_news_workflow(news: str) -> Optional[str]:
    """Workflow for analyzing news and posting to Twitter."""

    try:
        logger.info("Analyzing news...")
        # Get recent news context using Perplexity
        context = await PerplexityTool().search("Latest crypto news")

        # Prepare LLM prompt
        llm = LLM()
        user_prompt = (
            f"Context from recent news:\n{context}\n\nNews to analyze:\n{news}\n\n"
            "Analyze the news and provide insights. "
            "Finally make a concise tweet about the news with a maximum of 280 characters."
        )
        messages = [{"role": "user", "content": user_prompt}]
        analysis = await llm.generate_response(messages)

        # Prepare tweet
        tweet_text = f"Breaking News:\n{analysis}\n#StayInformed"

        # Publish tweet
        logger.info(f"Publishing tweet:\n{tweet_text}")
        result = await TwitterTool().post_thread(tweets={"tweet1": tweet_text})
        logger.info("Tweet posted successfully!")
        return ";".join(str(res) for res in result)
    except Exception as e:
        logger.error(f"Error in analyze_news_workflow: {e}")
        return None
