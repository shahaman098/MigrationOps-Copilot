"""What is REAL: Azure OpenAI reasoning and live tool calls for SSL, HTTP, and DNS.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

from tools.health_checks import (
    check_dns_resolution,
    check_http_status,
    check_ssl_certificate,
)

MONITOR_INSTRUCTIONS = """You are the Monitor agent for SiteOps Guardian.

Your job is to assess the health of a single website incident target using all available tools.

Rules:
1. Always run all three tools for every investigation:
   - check_ssl_certificate(hostname)
   - check_http_status(url)
   - check_dns_resolution(hostname)
2. Extract the hostname correctly from the user input before calling hostname-based tools.
3. Do not skip tools even if one of them reports an error.
4. Base your output only on tool results.
5. Produce a structured health report with these sections:
   - Target
   - SSL Status
   - HTTP Status
   - DNS Status
   - Incident Summary
6. Include concrete evidence such as expiry days, HTTP status code, redirect behavior, resolved IPs, and any tool errors.
7. If SSL is expired or expiring soon, call that out explicitly.
8. If DNS or HTTP checks fail, state that clearly and do not invent causes.
9. Keep the report concise but operationally useful for downstream agents.
"""


def create_monitor_agent():
    load_dotenv()

    credential = AzureCliCredential()
    client = AzureOpenAIResponsesClient(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=credential,
    )

    return client.as_agent(
        name="Monitor",
        instructions=MONITOR_INSTRUCTIONS,
        tools=[
            check_ssl_certificate,
            check_http_status,
            check_dns_resolution,
        ],
    )
