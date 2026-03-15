"""What is REAL: Azure OpenAI reasoning and live Monitor agent tool execution.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
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

from agents.monitor import create_monitor_agent


def _ensure_azure_runtime() -> None:
    load_dotenv()
    if not os.environ.get("AZURE_OPENAI_ENDPOINT"):
        pytest.skip("AZURE_OPENAI_ENDPOINT is not configured.")
    if not os.environ.get("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"):
        pytest.skip("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME is not configured.")
    if not os.environ.get("AZURE_OPENAI_API_KEY") and shutil.which("az") is None:
        pytest.skip("Azure auth is not available. Configure AZURE_OPENAI_API_KEY or install Azure CLI.")


@pytest.mark.asyncio
async def test_monitor_reports_site_health() -> None:
    _ensure_azure_runtime()
    agent = create_monitor_agent()
    result = await agent.run("Check the health of https://expired.badssl.com")
    output_text = str(result)

    assert "expired.badssl.com" in output_text.lower(), output_text
    assert "ssl" in output_text.lower(), output_text
