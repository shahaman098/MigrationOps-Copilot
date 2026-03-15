"""What is REAL: Real source/target snapshots, snapshot comparison, live Azure OpenAI agent reasoning, and optional MCP-backed discovery.
What is MOCKED: Nothing.
What is SIMULATED: Remediation actions performed by the Executor stage.
"""

import json
from datetime import UTC, datetime
from urllib.parse import urlparse

from agents.diagnostician import create_diagnostician_agent
from agents.executor import create_executor_agent
from agents.planner import create_planner_agent
from agents.triager import create_risk_assessor_agent
from azure_client import create_azure_openai_client
from tools.baseline import compare_snapshots, snapshot_site

DISCOVERY_AGENT_INSTRUCTIONS = """You are the Discovery agent in the MigrationOps Copilot system.

Your job is to create a single migration snapshot for one website by using MCP health check tools.

Rules:
1. Always call all three tools:
   - check_ssl_certificate(hostname)
   - check_http_status(url)
   - check_dns_resolution(hostname)
2. Extract the hostname from the full URL before calling hostname-based tools.
3. Output only valid JSON with no markdown, prose, or code fences.
4. The JSON schema must be:
   {
     "url": "<full url>",
     "hostname": "<hostname>",
     "timestamp": "<ISO-8601 UTC timestamp>",
     "ssl": { ... parsed SSL tool output ... },
     "http": { ... parsed HTTP tool output ... },
     "dns": { ... parsed DNS tool output ... }
   }
5. The ssl/http/dns values must be JSON objects, not quoted JSON strings.
6. Do not add any extra keys.
"""


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
        f"Overall Risk: {comparison['overall_risk']}\n"
        f"Migration Health Score: {comparison['summary']['migration_health_score']}\n\n"
        "Please assess the migration risk based on this comparison."
    )


def _extract_json_object(raw_output: str) -> dict[str, object]:
    candidate = raw_output.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(candidate[start : end + 1])


def _normalize_discovery_snapshot(raw_output: str, url: str) -> dict[str, object]:
    snapshot = _extract_json_object(raw_output)
    hostname = _extract_hostname(url)

    snapshot["url"] = snapshot.get("url") or url
    snapshot["hostname"] = snapshot.get("hostname") or hostname
    snapshot["timestamp"] = datetime.now(UTC).isoformat()

    for key in ("ssl", "http", "dns"):
        value = snapshot.get(key)
        if isinstance(value, str):
            snapshot[key] = json.loads(value)
        elif not isinstance(value, dict):
            raise ValueError(f"Discovery agent output missing JSON object for '{key}'.")

    return snapshot


def _create_mcp_discovery_agent(mcp_tool):
    client = create_azure_openai_client()
    return client.as_agent(
        name="Discovery",
        instructions=DISCOVERY_AGENT_INSTRUCTIONS,
        tools=mcp_tool,
    )


async def _snapshot_site_via_mcp(discovery_agent, url: str) -> str:
    result = await discovery_agent.run(
        "Create a migration snapshot for this URL and return JSON only:\n"
        f"{url}"
    )
    snapshot = _normalize_discovery_snapshot(str(result), url)
    return json.dumps(snapshot)


async def run_migration_analysis(
    source_url: str,
    target_url: str,
    use_mcp: bool = False,
) -> dict[str, str]:
    """Run the migration-analysis pipeline using manual orchestration."""

    print(f"[DISCOVERY] Snapshotting source: {source_url}")

    if use_mcp:
        from agent_framework import MCPStreamableHTTPTool

        async with MCPStreamableHTTPTool(
            name="health_checks",
            url="http://localhost:8081/mcp",
        ) as mcp_tool:
            discovery_agent = _create_mcp_discovery_agent(mcp_tool)
            before_snapshot_json = await _snapshot_site_via_mcp(discovery_agent, source_url)

            print(f"[DISCOVERY] Snapshotting target: {target_url}")
            after_snapshot_json = await _snapshot_site_via_mcp(discovery_agent, target_url)
    else:
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
        f"risk={comparison['overall_risk']}, "
        f"health_score={comparison['summary']['migration_health_score']}",
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
