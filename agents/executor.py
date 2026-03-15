"""What is REAL: LLM reasoning and live HTTP verification checks.
What is MOCKED: Nothing.
What is SIMULATED: Certificate renewal, cache purge, and configuration update actions.
"""

import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

from tools.health_checks import check_http_status
from tools.remediation import (
    simulate_cache_purge,
    simulate_cert_renewal,
    simulate_config_update,
)

EXECUTOR_INSTRUCTIONS = """You are the Executor agent in the MigrationOps Copilot system.

You receive the approved migration remediation context for one website migration.

Your job:
1. Execute only simulated migration remediation tools. Never claim a real infrastructure change happened.
2. For SSL migration issues, prefer simulate_cert_renewal first.
3. Use simulate_config_update when the plan implies TLS, routing, or hosting configuration changes.
4. Use simulate_cache_purge when the context suggests cache or CDN invalidation is relevant to the migration.
5. Always run check_http_status(url) after the simulated actions as a real verification step against the target URL.
6. Be explicit when verification still fails because the remediation actions were only simulated.

Output format:
Execution Log:
- <tool action and result>
- <tool action and result>

Verification:
- <real HTTP verification result>

Final Status:
<Executed simulated plan. Verification passed/failed, with brief explanation.>
"""


def create_executor_agent():
    load_dotenv()

    credential = AzureCliCredential()
    client = AzureOpenAIResponsesClient(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=credential,
    )

    return client.as_agent(
        name="Executor",
        instructions=EXECUTOR_INSTRUCTIONS,
        tools=[
            simulate_cert_renewal,
            simulate_cache_purge,
            simulate_config_update,
            check_http_status,
        ],
    )
