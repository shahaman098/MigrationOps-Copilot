"""What is REAL: LLM reasoning.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

RISK_ASSESSOR_INSTRUCTIONS = """You are the Risk Assessor agent in the MigrationOps Copilot system.

Your role is to assess migration risk based on a comparison report between a source (pre-migration) site and a target (post-migration) site.

You will receive a MIGRATION COMPARISON REPORT containing:
- Pre-migration snapshot
- Post-migration snapshot
- List of detected changes with severity levels
- Overall risk classification

Output format:
---
MIGRATION RISK ASSESSMENT
Overall Risk: [CRITICAL / HIGH / MEDIUM / LOW]
Blocking Issues: [count]
Expected Changes: [list]
Unexpected Changes: [list]
Risk Summary: [2-3 sentence explanation]
Recommendation: [PROCEED / PROCEED WITH CAUTION / BLOCK MIGRATION]
---
"""


TRIAGER_INSTRUCTIONS = RISK_ASSESSOR_INSTRUCTIONS


def create_risk_assessor_agent():
    load_dotenv()

    credential = AzureCliCredential()
    client = AzureOpenAIResponsesClient(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=credential,
    )

    return client.as_agent(
        name="RiskAssessor",
        instructions=RISK_ASSESSOR_INSTRUCTIONS,
        tools=[],
    )


def create_triager_agent():
    return create_risk_assessor_agent()
