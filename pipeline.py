"""What is REAL: Real source/target snapshots, snapshot comparison, and live Azure OpenAI agent reasoning.
What is MOCKED: Nothing.
What is SIMULATED: Remediation actions performed by the Executor stage.
"""

import json
from urllib.parse import urlparse

from agents.diagnostician import create_diagnostician_agent
from agents.executor import create_executor_agent
from agents.planner import create_planner_agent
from agents.triager import create_risk_assessor_agent
from tools.baseline import compare_snapshots, snapshot_site


def _extract_hostname(url: str) -> str:
    parsed = urlparse(url)
    return parsed.hostname or url


def _format_changes(changes: list[dict[str, object]]) -> str:
    if not changes:
        return "No changes detected."
    return json.dumps(changes, indent=2)


def _format_comparison_report(
    source_url: str,
    target_url: str,
    before_snapshot: dict[str, object],
    after_snapshot: dict[str, object],
    comparison: dict[str, object],
) -> str:
    return (
        "MIGRATION COMPARISON REPORT\n"
        f"Source: {source_url}\n"
        f"Target: {target_url}\n\n"
        "Pre-Migration Snapshot:\n"
        f"{json.dumps(before_snapshot, indent=2)}\n\n"
        "Post-Migration Snapshot:\n"
        f"{json.dumps(after_snapshot, indent=2)}\n\n"
        "Changes Detected:\n"
        f"{_format_changes(comparison['changes'])}\n\n"
        f"Overall Risk: {comparison['overall_risk']}\n\n"
        "Please assess the migration risk based on this comparison."
    )


async def run_migration_analysis(source_url: str, target_url: str) -> dict[str, str]:
    """Run the migration-analysis pipeline using manual orchestration."""

    print(f"[DISCOVERY] Snapshotting source: {source_url}")
    before_snapshot_json = await snapshot_site(source_url)

    print(f"[DISCOVERY] Snapshotting target: {target_url}")
    after_snapshot_json = await snapshot_site(target_url)

    comparison_json = compare_snapshots(before_snapshot_json, after_snapshot_json)

    before_snapshot = json.loads(before_snapshot_json)
    after_snapshot = json.loads(after_snapshot_json)
    comparison = json.loads(comparison_json)
    discovery_output = _format_comparison_report(
        source_url,
        target_url,
        before_snapshot,
        after_snapshot,
        comparison,
    )

    print("[DISCOVERY] Migration comparison complete")
    print(
        "[DISCOVERY] Summary: "
        f"{comparison['summary']['total_changes']} changes, "
        f"risk={comparison['overall_risk']}",
    )

    risk_assessor = create_risk_assessor_agent()
    diagnostician = create_diagnostician_agent()
    planner = create_planner_agent()

    risk_assessor_result = await risk_assessor.run(str(discovery_output))
    risk_assessor_output = str(risk_assessor_result)

    diagnostician_result = await diagnostician.run(str(risk_assessor_output))
    diagnostician_output = str(diagnostician_result)

    planner_result = await planner.run(str(diagnostician_output))
    planner_output = str(planner_result)

    return {
        "discovery": discovery_output,
        "before_snapshot": before_snapshot_json,
        "after_snapshot": after_snapshot_json,
        "comparison": comparison_json,
        "risk_assessor": risk_assessor_output,
        "diagnostician": diagnostician_output,
        "planner": planner_output,
    }


async def run_executor(source_url: str, target_url: str, outputs: dict[str, str]) -> str:
    """Run the Executor stage after human approval."""

    hostname = _extract_hostname(target_url)
    executor = create_executor_agent()
    executor_result = await executor.run(
        "Source URL:\n"
        f"{source_url}\n\n"
        "Target URL:\n"
        f"{target_url}\n\n"
        "Target hostname:\n"
        f"{hostname}\n\n"
        "Pre-Migration Snapshot:\n"
        f"{outputs['before_snapshot']}\n\n"
        "Post-Migration Snapshot:\n"
        f"{outputs['after_snapshot']}\n\n"
        "Migration Comparison:\n"
        f"{outputs['comparison']}\n\n"
        "Risk Assessment:\n"
        f"{outputs['risk_assessor']}\n\n"
        "Migration Diagnostics:\n"
        f"{outputs['diagnostician']}\n\n"
        "Approved Migration Remediation Plan:\n"
        f"{outputs['planner']}",
    )
    return str(executor_result)
