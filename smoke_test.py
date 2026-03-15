"""What is REAL: framework install, Azure connection, LLM response.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import asyncio

from azure_client import create_azure_openai_client


async def main() -> None:
    client = create_azure_openai_client()

    agent = client.as_agent(
        name="test",
        instructions="You are helpful.",
    )

    result = await agent.run("Say hello in one sentence.")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
