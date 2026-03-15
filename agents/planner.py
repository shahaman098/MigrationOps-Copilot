"""What is REAL: LLM reasoning.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import os

from agent_framework.azure import AzureOpenAIResponsesClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

PLANNER_INSTRUCTIONS = """You are the Remediation Planner agent in the MigrationOps Copilot system.

Your role is to create a prioritized remediation plan for migration issues.

You will receive a diagnostics report with root causes for each migration issue. You must:
1. Create a numbered, prioritized list of remediation steps
2. For each step, specify:
   - What to do
   - Whether it is automatable or requires manual intervention
   - Expected time to resolve
   - Whether it blocks the migration going live
3. Separate steps into: "Before Go-Live" and "Post Go-Live Monitoring"

Output format:
---
MIGRATION REMEDIATION PLAN

BEFORE GO-LIVE:
1. [Step] — [Automatable/Manual] — [Time estimate] — [BLOCKING/NON-BLOCKING]
...

POST GO-LIVE MONITORING:
1. [What to monitor] — [How long] — [What to look for]
...

ESTIMATED TIME TO MIGRATION-READY: [estimate]
---
"""


def create_planner_agent():
    load_dotenv()

    credential = AzureCliCredential()
    client = AzureOpenAIResponsesClient(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        deployment_name=os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"],
        credential=credential,
    )

    return client.as_agent(
        name="Planner",
        instructions=PLANNER_INSTRUCTIONS,
        tools=[],
    )
