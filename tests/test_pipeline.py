"""What is REAL: Full migration pipeline integration tests with live checks and Azure OpenAI.
What is MOCKED: Nothing.
What is SIMULATED: Executor-stage remediation actions are not exercised in these tests.
"""

import json
import os
from pathlib import Path
import shutil
import sys

from dotenv import load_dotenv
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import run_migration_analysis


def _ensure_azure_runtime() -> None:
    load_dotenv()
    if not os.environ.get("AZURE_OPENAI_ENDPOINT"):
        pytest.skip("AZURE_OPENAI_ENDPOINT is not configured.")
    if not os.environ.get("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"):
        pytest.skip("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME is not configured.")
    if not os.environ.get("AZURE_OPENAI_API_KEY") and shutil.which("az") is None:
        pytest.skip("Azure auth is not available. Configure AZURE_OPENAI_API_KEY or install Azure CLI.")


@pytest.mark.asyncio
async def test_full_pipeline_broken_migration() -> None:
    _ensure_azure_runtime()
    outputs = await run_migration_analysis(
        "https://google.com",
        "https://expired.badssl.com",
    )
    comparison = json.loads(outputs["comparison"])

    assert {"discovery", "risk_assessor", "diagnostician", "planner"} <= outputs.keys(), outputs
    assert comparison["overall_risk"] == "CRITICAL", comparison
    assert "CRITICAL" in outputs["risk_assessor"].upper() or "BLOCK" in outputs["risk_assessor"].upper()


@pytest.mark.asyncio
async def test_full_pipeline_clean_migration() -> None:
    _ensure_azure_runtime()
    outputs = await run_migration_analysis(
        "https://google.com",
        "https://google.com",
    )
    comparison = json.loads(outputs["comparison"])

    assert comparison["overall_risk"] == "LOW", comparison
    assert "LOW" in outputs["risk_assessor"].upper() or "PROCEED" in outputs["risk_assessor"].upper()
