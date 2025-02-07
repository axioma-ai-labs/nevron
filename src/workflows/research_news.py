from typing import Optional

from loguru import logger

from src.llm.llm import LLM
<<<<<<< HEAD
from src.memory.memory_module import MemoryModule, get_memory_module
from src.tools.link_parser import LinkParserTool
=======
>>>>>>> 74f5caf (Tools refactoring and executors implementation)
from src.tools.perplexity import PerplexityTool
from src.tools.twitter import TwitterTool


async def analyze_news_workflow(
    news: str, memory: MemoryModule = get_memory_module(), link: Optional[str] = None
) -> Optional[str]:
    """Workflow for analyzing news and posting to Twitter."""

    try:
        logger.info("Analyzing news...")
<<<<<<< HEAD
        if link:
            # Parse link content
            link_parser = LinkParserTool()
            search_results = link_parser.search_links("Latest crypto news")
            context = "\n\n".join(
                f"Title: {result['title']}\n"
                f"Description: {result['description']}\n"
                f"Content: {result['text_data'][:500]}..."  # Limit content length temporarily
                for result in search_results
            )
        else:
            # Get recent news context using Perplexity
            context = await PerplexityTool().search("Latest crypto news")
=======
        # Get recent news context using Perplexity
        context = await PerplexityTool().search("Latest crypto news")
>>>>>>> 74f5caf (Tools refactoring and executors implementation)

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
