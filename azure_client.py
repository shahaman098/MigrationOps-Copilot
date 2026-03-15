"""What is REAL: Azure OpenAI client creation using environment-backed auth.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv


def create_azure_openai_client() -> AzureOpenAIResponsesClient:
    """Create an Azure OpenAI Responses client using API key or Azure CLI auth."""

    load_dotenv()

    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
    deployment_name = os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"]
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")

    if api_key:
        return AzureOpenAIResponsesClient(
            endpoint=endpoint,
            deployment_name=deployment_name,
            api_key=api_key,
        )

    return AzureOpenAIResponsesClient(
        endpoint=endpoint,
        deployment_name=deployment_name,
        credential=AzureCliCredential(),
    )
