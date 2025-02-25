# **Tools**

## Overview

Tools are integral components that empower Nevron to interact with external services and execute specific actions. Each tool is designed to handle distinct functionality, enhancing the agent's versatility and capability. Tools act as modular utilities that can be seamlessly integrated into workflows to perform specialized tasks. They enable connectivity with external services, third-party APIs, search engines, and custom functions, making Nevron highly adaptable and efficient.

All tools are organized within the `src/tools/` directory.

---

## How It Works

Tools in Nevron are specialized modules that handle specific tasks within the system, integrating with workflows to provide seamless interactions with external platforms. Here's how the tools work at a high level:

1. **Integration with Workflows:**
   Tools serve as reusable components that workflows rely on for executing key tasks such as publishing content, fetching data, or processing input.

2. **Purpose-Built Functionality:**
   Each tool is uniquely designed to address a specific need, such as interacting with Twitter, Telegram, or external APIs. This ensures workflows remain focused and efficient.

3. **Technical Features:**
   All tools share the following core capabilities:
   - **Error Handling:** Tools catch and log errors clearly, ensuring smooth operation.
   - **Logging:** Use `loguru` for consistent, detailed logs.
   - **Configuration Management:** Centralized settings allow easy updates and customization.
   - **Asynchronous Execution:** Async/await ensures non-blocking performance.
   - **Custom Exceptions:** Each tool defines specific error types for clarity (e.g., `TwitterError`, `TelegramError`, `APIError`).

---

## Available Tools

### 1. Twitter Integration (`twitter.py`)
The Twitter tool automates content publishing to Twitter using both v1.1 and v2 of the Twitter API.

#### Features:
- Supports image uploads and tweet threads.
- Combines the strengths of v1.1 (better for media) and v2 (better for posting).
- Smart rate-limiting with 3-second delays between tweets.

#### How It Works:
1. **For Media:**
      - Downloads the image.
      - Converts it to grayscale.
      - Uploads it to Twitter.
2. **For Tweet Threads:**
      - Posts tweets sequentially, linking them together as a thread.
      - Delays are added between posts to avoid API rate limits.
3. **Output:**
      - Returns the status of each posted tweet.

---

### 2. Telegram Integration (`tg.py`)
The Telegram tool simplifies posting content to a specific Telegram channel while managing message length constraints.

#### Features:
- Smart message splitting for handling Telegram's character limit.
- HTML formatting support, including links.

#### How It Works:
1. Takes an HTML-formatted message.
2. Splits the message into smaller chunks if it exceeds Telegram's length limit.
3. Posts each chunk sequentially.
4. Returns the IDs of all successfully posted messages.

---

### 3. Perplexity Search Tool (`search_with_perplexity.py`)
The Perplexity tool leverages AI to search for cryptocurrency-related news using Perplexity's advanced API.

#### Features:
- Powered by the "llama-3.1-sonar-small-128k-online" model.
- Tracks token usage and estimates costs ($0.2 per million tokens).

#### How It Works:
1. Takes a search query as input.
2. Sends the query to Perplexity's API with preconfigured settings (temperature 0.3, top_p 0.8).
3. Receives AI-processed search results.
4. Formats the results for easy consumption and returns them.

---

## How to Add a New Tool?

Adding a new tool to Nevron is a straightforward process. Follow these steps:

1. **Create a New File:**
   Add a new Python file in the `src/tools/` directory (e.g., `new_tool.py`).

2. **Implement the Tool's Functionality:**
   Define the tool's purpose and logic, adhering to Nevron's modular architecture.

3. **Test Thoroughly:**
   Ensure the tool works as expected by writing and running tests.

4. **Integrate into Workflows:**
   Once the tool is ready, it can be imported and used in workflows to enhance functionality.

---

## Best Practices

1. **Error Handling:** Ensure all tools implement robust error handling for smooth operation.
2. **Logging:** Use `loguru` to maintain detailed and consistent logs across all tools.
3. **Asynchronous Execution:** Leverage `asyncio` where applicable for non-blocking performance.
4. **Reusability:** Design tools as modular and reusable components for seamless integration into multiple workflows.

---

Nevron's tools form the backbone of its ability to automate tasks, interact with external systems, and deliver actionable insights.

From publishing on social media to conducting advanced AI-driven searches, tools are modular, reusable, and integral to the agent's success.

---

If you have any questions or need further assistance, please refer to the [GitHub Discussions](https://github.com/axioma-ai-labs/nevron/discussions).

