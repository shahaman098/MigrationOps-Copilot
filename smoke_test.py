"""What is REAL: framework install, Azure connection, LLM response.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import asyncio
import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv


async def main() -> None:
    load_dotenv()

    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    deployment_name = os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"]

    credential = AzureCliCredential()
    client = AzureOpenAIResponsesClient(
        endpoint=endpoint,
        deployment_name=deployment_name,
        credential=credential,
    )

    agent = client.as_agent(
        name="test",
        instructions="You are helpful.",
    )

    result = await agent.run("Say hello in one sentence.")
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
