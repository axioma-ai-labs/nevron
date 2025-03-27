from typing import Optional

from loguru import logger

from src.llm.llm import LLM
from src.memory.memory_module import MemoryModule, get_memory_module
from src.tools.link_parser import LinkParserTool
from src.tools.perplexity import PerplexityTool
from src.tools.twitter import TwitterTool


async def analyze_news_workflow(
    news: str, memory: MemoryModule = get_memory_module(), link: Optional[str] = None
) -> Optional[str]:
    """Workflow for analyzing news and posting to Twitter."""

    try:
        logger.info("Analyzing news...")
        if link:
            # Parse link content
            link_parser = LinkParserTool()
            search_results = link_parser.search_links(
                "Latest crypto news",
                gl="DE",  # Country code for Germany
                hl="de",  # Language code for German
                num=5,  # Number of results to return
            )
            context = "\n\n".join(
                f"Title: {result['title']}\n"
                f"Description: {result['description']}\n"
                f"Content: {result['content']}"
                for result in search_results
            )
        else:
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
        logger.info("X thread posted successfully!")
        logger.info(
            f"Storing in memory:\n"
            f"Event: {context[:200]}...\n"  # Truncate for readability
            f"Action: analyze_news\n"
            f"Outcome: Tweet posted: {tweet_text}\n"
            f"Metadata: tweet_id={result}"
        )

        # Store the processed signal in memory
        await memory.store(
            event=context,
            action="analyze_news",
            outcome=f"Tweet posted: {tweet_text}",
            metadata={"tweet_id": result},
        )

        return ";".join(str(res) for res in result)
    except Exception as e:
        logger.error(f"Error in analyze_news_workflow: {e}")
        return None
