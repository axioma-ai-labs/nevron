import asyncio

from loguru import logger

from src.agent import Agent
from src.utils import log_settings


# Configure logging
logger.add("logs/debug.log", rotation="1 MB", retention="10 days", level="DEBUG")


async def async_main():
    """
    Async entry point for running the agent's runtime.
    """
    logger.info("Starting the agent runtime...")
    log_settings()

    # Initialize the agent runtime
    agent = Agent()

    try:
        # Start the async runtime loop
        await agent.start_runtime_loop()
    except Exception as global_error:
        logger.critical(f"Fatal error in the runtime: {global_error}")
    finally:
        logger.info("Agent runtime has stopped.")


def main():
    """
    Main entry point that runs the async runtime
    """
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Agent runtime interrupted by user. Shutting down gracefully...")
    except Exception as e:
        logger.critical(f"Fatal error in the main runtime: {e}")


if __name__ == "__main__":
    main()
