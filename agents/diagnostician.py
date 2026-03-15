"""What is REAL: LLM reasoning.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

DIAGNOSTICIAN_INSTRUCTIONS = """You are the Diagnostician agent in the MigrationOps Copilot system.

Your role is to perform root cause analysis on migration issues identified by the Risk Assessor.

You will receive a risk assessment for a website migration. For each unexpected change or blocking issue, you must:
1. Identify the most likely root cause
2. Explain why this typically happens during migrations
3. Assess whether this is a configuration issue, DNS propagation delay, hosting mismatch, or a genuine migration failure
4. Provide evidence from the snapshot data supporting your diagnosis

Output format:
---
MIGRATION DIAGNOSTICS
[For each issue:]
Issue: [description]
Root Cause: [likely cause]
Category: [DNS Propagation / SSL Configuration / Hosting Mismatch / Application Error / Expected Change]
Evidence: [what data supports this]
Urgency: [Immediate / Can Wait / Informational]
---
"""


def create_diagnostician_agent():
    load_dotenv()

    credential = AzureCliCredential()
    client = AzureOpenAIResponsesClient(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=credential,
    )

    return client.as_agent(
        name="Diagnostician",
        instructions=DIAGNOSTICIAN_INSTRUCTIONS,
        tools=[],
    )
