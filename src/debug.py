import asyncio

from src.llm.llm import LLM


async def main():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello, how are you?"},
    ]

    llm = LLM()
    response = await llm.generate_response(messages)
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
