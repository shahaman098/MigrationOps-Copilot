"""What is REAL: Tool invocation and JSON result formatting.
What is MOCKED: Nothing.
What is SIMULATED: Certificate renewal, cache purge, and configuration update actions.
"""

import json
from typing import Annotated

from agent_framework import tool


@tool(
    name="simulate_cert_renewal",
    description="Simulate renewing an SSL certificate for a hostname without changing real infrastructure.",
)
def simulate_cert_renewal(
    hostname: Annotated[str, "The hostname whose certificate would be renewed."],
) -> str:
    # SIMULATED
    return json.dumps(
        {
            "action": "cert_renewal",
            "hostname": hostname,
            "simulated": True,
            "status": "simulated_success",
            "message": f"SIMULATED: Would trigger certificate renewal for {hostname}. No real infrastructure was changed.",
        },
    )


@tool(
    name="simulate_cache_purge",
    description="Simulate purging caches for a hostname without changing real infrastructure.",
)
def simulate_cache_purge(
    hostname: Annotated[str, "The hostname whose caches would be purged."],
) -> str:
    # SIMULATED
    return json.dumps(
        {
            "action": "cache_purge",
            "hostname": hostname,
            "simulated": True,
            "status": "simulated_success",
            "message": f"SIMULATED: Would purge caches for {hostname}. No real infrastructure was changed.",
        },
    )


@tool(
    name="simulate_config_update",
    description="Simulate a configuration update without changing real infrastructure.",
)
def simulate_config_update(
    setting: Annotated[str, "The configuration setting that would be updated."],
    value: Annotated[str, "The value that would be applied to the configuration setting."],
) -> str:
    # SIMULATED
    return json.dumps(
        {
            "action": "config_update",
            "setting": setting,
            "value": value,
            "simulated": True,
            "status": "simulated_success",
            "message": f"SIMULATED: Would update config '{setting}' to '{value}'. No real infrastructure was changed.",
        },
    )
