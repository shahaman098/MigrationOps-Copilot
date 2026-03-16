"""What is REAL: Azure OpenAI agent reasoning against mock migration inputs.
What is MOCKED: Nothing.
What is SIMULATED: Executor remediation actions only.
"""

import os
from pathlib import Path
import shutil
import sys

from dotenv import load_dotenv
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.diagnostician import create_diagnostician_agent
from agents.executor import create_executor_agent
from agents.planner import create_planner_agent
from agents.triager import create_risk_assessor_agent


def _ensure_azure_runtime() -> None:
    load_dotenv()
    has_openai_endpoint = bool(os.environ.get("AZURE_OPENAI_ENDPOINT"))
    has_foundry_endpoint = bool(os.environ.get("AZURE_AI_PROJECT_ENDPOINT"))
    has_deployment = bool(
        os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
        or os.environ.get("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME")
    )

    if not has_openai_endpoint and not has_foundry_endpoint:
        pytest.skip("No Azure OpenAI endpoint or Azure AI project endpoint is configured.")
    if not has_deployment:
        pytest.skip("No Azure model deployment name is configured.")
    if not os.environ.get("AZURE_OPENAI_API_KEY") and shutil.which("az") is None:
        pytest.skip("Azure auth is not available. Configure AZURE_OPENAI_API_KEY or install Azure CLI.")


@pytest.mark.asyncio
async def test_risk_assessor_critical() -> None:
    _ensure_azure_runtime()
    agent = create_risk_assessor_agent()
    result = await agent.run(
        "MIGRATION COMPARISON REPORT\n"
        "Source: https://google.com\n"
        "Target: https://expired.badssl.com\n\n"
        "Changes Detected:\n"
        '[{"id":"ssl_expired","severity":"critical","description":"Target SSL certificate is expired."}]\n\n'
        "Overall Risk: CRITICAL\n\n"
        "Please assess the migration risk based on this comparison."
    )
    output = str(result).upper()
    assert "CRITICAL" in output or "BLOCK" in output, output


@pytest.mark.asyncio
async def test_risk_assessor_clean() -> None:
    _ensure_azure_runtime()
    agent = create_risk_assessor_agent()
    result = await agent.run(
        "MIGRATION COMPARISON REPORT\n"
        "Source: https://google.com\n"
        "Target: https://google.com\n\n"
        "Changes Detected:\n"
        "[]\n\n"
        "Overall Risk: LOW\n\n"
        "Please assess the migration risk based on this comparison."
    )
    output = str(result).upper()
    assert "LOW" in output or "PROCEED" in output, output


@pytest.mark.asyncio
async def test_diagnostician() -> None:
    _ensure_azure_runtime()
    agent = create_diagnostician_agent()
    result = await agent.run(
        "---\n"
        "MIGRATION RISK ASSESSMENT\n"
        "Overall Risk: CRITICAL\n"
        "Blocking Issues: 1\n"
        "Expected Changes: []\n"
        'Unexpected Changes: ["Target SSL certificate is expired."]\n'
        "Risk Summary: The migration is blocked by an expired TLS certificate.\n"
        "Recommendation: BLOCK MIGRATION\n"
        "---"
    )
    output = str(result).lower()
    assert "root cause" in output or "ssl" in output, output


@pytest.mark.asyncio
async def test_planner() -> None:
    _ensure_azure_runtime()
    agent = create_planner_agent()
    result = await agent.run(
        "---\n"
        "MIGRATION DIAGNOSTICS\n"
        "Issue: Target SSL certificate is expired.\n"
        "Root Cause: The target host is serving an expired certificate.\n"
        "Category: SSL Configuration\n"
        "Evidence: Certificate expiry is in the past.\n"
        "Urgency: Immediate\n"
        "---"
    )
    output = str(result)
    assert "1." in output or "BEFORE GO-LIVE" in output, output


@pytest.mark.asyncio
async def test_executor_simulated() -> None:
    _ensure_azure_runtime()
    agent = create_executor_agent()
    result = await agent.run(
        "Source URL:\nhttps://google.com\n\n"
        "Target URL:\nhttps://expired.badssl.com\n\n"
        "Target hostname:\nexpired.badssl.com\n\n"
        "Approved Migration Remediation Plan:\n"
        "Renew the certificate, validate the HTTPS endpoint, and purge caches if needed."
    )
    output = str(result).lower()
    assert "simulated" in output, output
