"""What is REAL: Azure OpenAI client creation using environment-backed auth.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def _create_default_credential() -> DefaultAzureCredential:
    """Use Azure CLI locally and managed identity in App Service without interactive prompts."""

    return DefaultAzureCredential(exclude_interactive_browser_credential=True)


def is_foundry_configured() -> bool:
    """Return True when a Foundry project endpoint is configured."""

    load_dotenv()
    return bool(os.environ.get("AZURE_AI_PROJECT_ENDPOINT"))


def get_model_deployment_name() -> str:
    """Resolve the model deployment name across direct Azure OpenAI and Foundry modes."""

    load_dotenv()
    return os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME") or os.environ[
        "AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"
    ]


def get_mcp_server_url() -> str:
    """Resolve the MCP server URL for local or Azure-hosted discovery."""

    load_dotenv()
    return os.environ.get("MCP_SERVER_URL", "http://localhost:8081/mcp")


def create_azure_openai_client() -> AzureOpenAIResponsesClient:
    """Create an Azure OpenAI / Foundry-backed client using the configured auth path."""

    load_dotenv()

    project_endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    deployment_name = get_model_deployment_name()
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    credential = _create_default_credential()

    if project_endpoint:
        return AzureOpenAIResponsesClient(
            project_endpoint=project_endpoint,
            deployment_name=deployment_name,
            credential=credential,
        )

    endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]

    if api_key:
        return AzureOpenAIResponsesClient(
            endpoint=endpoint,
            deployment_name=deployment_name,
            api_key=api_key,
        )

    return AzureOpenAIResponsesClient(
        endpoint=endpoint,
        deployment_name=deployment_name,
        credential=credential,
    )
