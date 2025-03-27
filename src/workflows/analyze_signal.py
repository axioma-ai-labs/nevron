from typing import Optional

from loguru import logger

from src.llm.llm import LLM
from src.memory.memory_module import MemoryModule, get_memory_module
from src.tools.get_signal import CoinstatsTool
from src.tools.link_parser import LinkParserTool
from src.tools.twitter import TwitterTool


async def analyze_signal(
    memory: MemoryModule = get_memory_module(), link: Optional[str] = None
) -> Optional[str]:
    """Fetch a signal, analyze it with an LLM, and post the result on Twitter."""
    try:
        logger.info("Fetching signal...")
        if link:
            # Parse link content
            link_parser = LinkParserTool()
            signal = link_parser.fetch_signal_link(link)
        else:
            # Fetch signal from Coinstats
            signal = await CoinstatsTool().fetch_signal()

        if signal.get("status") == "new_signal" and "content" in signal:
            signal_content = signal["content"]
            logger.info(f"Received signal: {signal_content}")

            # Check if this signal was already processed
            recent_signals = await memory.search(signal_content, top_k=1)
            if recent_signals and recent_signals[0]["event"] == signal_content:
                logger.info("Signal already processed, skipping analysis")
                return None

            logger.info("New signal detected, analyzing...")
            # Retrieve recent memory for context
            recent_memories = await memory.search("recent events", top_k=3)
            context = "\n".join([f"- {mem['event']}: {mem['outcome']}" for mem in recent_memories])

            # Prepare LLM prompt
            llm = LLM()
            user_prompt = (
                f"Context:\n{context}\n\nSignal:\n{signal_content}\n\n"
                "Analyze the signal and provide insights. "
                "Finally make a concise tweet about the signal with a maximum of 280 characters."
            )
            messages = [{"role": "user", "content": user_prompt}]
            analysis = await llm.generate_response(messages)

            # Prepare tweet
            tweet_text = f"Breaking News:\n{analysis}\n#CryptoNews"

            # Publish tweet
            logger.info(f"Publishing tweet:\n{tweet_text}")
            result = await TwitterTool().post_thread(tweets={"tweet1": tweet_text})
            logger.info("Tweet posted successfully!")
            logger.info(
                f"Storing in memory:\n"
                f"Event: {signal_content[:100]}...\n"  # Truncate for readability
                f"Action: check_signal\n"
                f"Outcome: Tweet posted: {tweet_text}\n"
                f"Metadata: tweet_id={result}"
            )

            # Store the processed signal in memory
            await memory.store(
                event=signal_content,
                action="check_signal",
                outcome=f"Tweet posted: {tweet_text}",
                metadata={"tweet_id": result},
            )

            return ";".join(str(res) for res in result)

        elif signal.get("status") == "no_data":
            logger.info("No actionable signal detected.")
            return None
        else:
            logger.warning("Received an unknown signal format or an error occurred.")
            return None

    except Exception as e:
        logger.error(f"Error in analyze_and_post_signal workflow: {e}")
        return None
