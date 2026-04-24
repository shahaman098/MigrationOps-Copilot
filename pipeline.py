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
from azure_client import (
    create_azure_openai_client,
    get_mcp_server_url,
    is_azure_openai_configured,
    is_foundry_configured,
)
from tools.baseline import compare_snapshots, snapshot_site
from tools.health_checks import check_http_status
from tools.remediation import (
    simulate_cache_purge,
    simulate_cert_renewal,
    simulate_config_update,
)

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


def _should_use_hosted_mcp(mcp_server_url: str) -> bool:
    return is_foundry_configured() and mcp_server_url.lower().startswith("https://")


def _format_change_descriptions(changes: list[dict[str, object]], severities: set[str]) -> str:
    selected = [
        str(change["description"])
        for change in changes
        if str(change.get("severity", "")).lower() in severities
    ]
    return ", ".join(selected) if selected else "None"


def _fallback_recommendation(overall_risk: str) -> str:
    if overall_risk in {"CRITICAL", "HIGH"}:
        return "BLOCK MIGRATION"
    if overall_risk == "MEDIUM":
        return "PROCEED WITH CAUTION"
    return "PROCEED"


def _fallback_risk_assessment(comparison: dict[str, object]) -> str:
    changes = list(comparison["changes"])
    blocking_issues = sum(
        1 for change in changes if str(change.get("severity", "")).lower() in {"critical", "high"}
    )
    overall_risk = str(comparison["overall_risk"])
    recommendation = _fallback_recommendation(overall_risk)
    summary = comparison["summary"]

    risk_summary = (
        f"The target environment shows {summary['total_changes']} detected changes with a migration "
        f"health score of {summary['migration_health_score']}. "
        f"Critical and high-severity findings are treated as blocking because they can affect "
        "availability, trust, or routing immediately after cutover."
    )

    return (
        "---\n"
        "MIGRATION RISK ASSESSMENT\n"
        f"Overall Risk: {overall_risk}\n"
        f"Blocking Issues: {blocking_issues}\n"
        f"Expected Changes: {_format_change_descriptions(changes, {'info'})}\n"
        f"Unexpected Changes: {_format_change_descriptions(changes, {'critical', 'high', 'warning'})}\n"
        f"Risk Summary: {risk_summary}\n"
        f"Recommendation: {recommendation}\n"
        "---"
    )


def _categorize_change(change: dict[str, object]) -> tuple[str, str, str]:
    change_id = str(change.get("id", ""))
    description = str(change.get("description", "Migration issue detected."))

    if change_id.startswith("ssl_"):
        root_cause = (
            "The target environment likely lacks the correct certificate binding or is presenting "
            "an unexpected certificate chain after migration."
        )
        category = "SSL Configuration"
        urgency = "Immediate"
    elif change_id.startswith("http_status_regressed_5xx") or change_id.startswith("http_status_failed"):
        root_cause = (
            "The target host is reachable but the application or upstream routing appears unhealthy, "
            "which often indicates backend misconfiguration after cutover."
        )
        category = "Application Error"
        urgency = "Immediate"
    elif change_id.startswith("http_"):
        root_cause = (
            "The target application is responding differently from the source, suggesting route, "
            "origin, or application behavior changed during migration."
        )
        category = "Hosting Mismatch"
        urgency = "Can Wait"
    elif change_id.startswith("dns_"):
        root_cause = (
            "The target DNS state differs from the source, which usually points to incomplete record "
            "updates, propagation lag, or destination infrastructure drift."
        )
        category = "DNS Propagation"
        urgency = "Can Wait"
    else:
        root_cause = "The migration introduced a state change that should be reviewed before go-live."
        category = "Expected Change"
        urgency = "Informational"

    return description, root_cause, category, urgency


def _fallback_diagnostics(comparison: dict[str, object]) -> str:
    changes = list(comparison["changes"])
    if not changes:
        return (
            "MIGRATION DIAGNOSTICS\n"
            "Issue: No blocking migration issues detected\n"
            "Root Cause: Source and target snapshots are materially aligned for SSL, DNS, and HTTP.\n"
            "Category: Expected Change\n"
            "Evidence: The structured comparison reported no changes.\n"
            "Urgency: Informational"
        )

    lines = ["MIGRATION DIAGNOSTICS"]
    for change in changes:
        description, root_cause, category, urgency = _categorize_change(change)
        evidence = (
            f"{description} Before={change.get('before', 'n/a')} After={change.get('after', 'n/a')}"
        )
        lines.extend(
            [
                f"Issue: {description}",
                f"Root Cause: {root_cause}",
                f"Category: {category}",
                f"Evidence: {evidence}",
                f"Urgency: {urgency}",
            ],
        )
    return "\n".join(lines)


def _before_go_live_step(change: dict[str, object]) -> tuple[str, str, str, str]:
    change_id = str(change.get("id", ""))
    if change_id.startswith("ssl_"):
        return (
            "Validate the target certificate binding and rotate the correct certificate into the target edge",
            "Manual",
            "20-40 minutes",
            "BLOCKING",
        )
    if change_id.startswith("http_status_regressed_5xx") or change_id.startswith("http_status_failed"):
        return (
            "Review origin routing and application health checks on the target environment",
            "Manual",
            "15-30 minutes",
            "BLOCKING",
        )
    if change_id.startswith("http_"):
        return (
            "Compare source and target route behavior and correct any mismatched application configuration",
            "Manual",
            "15-25 minutes",
            "BLOCKING",
        )
    if change_id.startswith("dns_"):
        return (
            "Confirm target DNS records, expected IP destinations, and TTL settings before cutover",
            "Manual",
            "10-20 minutes",
            "BLOCKING",
        )
    return (
        "Review the unexpected migration delta and confirm whether it is safe to accept",
        "Manual",
        "10-15 minutes",
        "NON-BLOCKING",
    )


def _fallback_planner(comparison: dict[str, object]) -> str:
    changes = list(comparison["changes"])
    before_steps = []
    seen = set()
    for change in changes:
        step = _before_go_live_step(change)
        if step not in seen:
            seen.add(step)
            before_steps.append(step)

    if not before_steps:
        before_steps.append(
            (
                "No blocking remediation required. Validate the target once more before approving cutover",
                "Manual",
                "5-10 minutes",
                "NON-BLOCKING",
            ),
        )

    monitoring_steps = [
        (
            "Monitor target HTTP status and latency after cutover",
            "30-60 minutes",
            "Watch for status regressions, elevated latency, or unexpected redirects",
        ),
        (
            "Re-check DNS and SSL presentation after traffic shifts",
            "15-30 minutes",
            "Confirm the target resolves as expected and serves the intended certificate",
        ),
    ]

    estimated_minutes = 20 * len(before_steps)
    lines = ["---", "MIGRATION REMEDIATION PLAN", "", "BEFORE GO-LIVE:"]
    for index, step in enumerate(before_steps, start=1):
        lines.append(f"{index}. {step[0]} — {step[1]} — {step[2]} — {step[3]}")

    lines.extend(["", "POST GO-LIVE MONITORING:"])
    for index, step in enumerate(monitoring_steps, start=1):
        lines.append(f"{index}. {step[0]} — {step[1]} — {step[2]}")

    lines.extend(
        [
            "",
            f"ESTIMATED TIME TO MIGRATION-READY: {estimated_minutes}-{estimated_minutes + 20} minutes",
            "---",
        ],
    )
    return "\n".join(lines)


def _format_http_verification(target_url: str) -> tuple[str, bool]:
    verification = json.loads(check_http_status(target_url))
    if verification.get("status") == "error":
        return (
            f"Real HTTP verification against {target_url} failed: {verification.get('error', 'Unknown error')}.",
            False,
        )

    status_code = verification.get("status_code", "unknown")
    response_time_ms = verification.get("response_time_ms", "unknown")
    success = isinstance(status_code, int) and 200 <= status_code < 400
    return (
        f"Real HTTP verification against {target_url} returned {status_code} in {response_time_ms} ms.",
        success,
    )


def _fallback_executor(target_url: str, outputs: dict[str, str]) -> str:
    comparison = json.loads(outputs["comparison"])
    hostname = _extract_hostname(target_url)
    changes = list(comparison["changes"])
    execution_log: list[str] = []

    if not changes:
        execution_log.append(
            "SIMULATED: No remediation actions were required because the deterministic comparison reported no migration issues.",
        )

    for change in changes:
        change_id = str(change.get("id", ""))
        if change_id.startswith("ssl_"):
            execution_log.append(json.loads(simulate_cert_renewal(hostname))["message"])
            execution_log.append(
                json.loads(simulate_config_update("tls_binding", "validated_target_certificate"))["message"],
            )
        elif change_id.startswith("dns_"):
            execution_log.append(
                json.loads(simulate_config_update("dns_record_set", "verified_target_destination"))["message"],
            )
        elif change_id.startswith("http_"):
            execution_log.append(
                json.loads(simulate_config_update("origin_routing", "matched_source_behavior"))["message"],
            )
            execution_log.append(json.loads(simulate_cache_purge(hostname))["message"])

    verification_line, verification_passed = _format_http_verification(target_url)
    final_status = (
        "Executed deterministic simulated remediation plan. Verification passed, but infrastructure changes "
        "were simulated only."
        if verification_passed
        else "Executed deterministic simulated remediation plan. Verification still failed, which indicates "
        "the target requires real infrastructure changes before cutover."
    )

    return "\n".join(
        [
            "Execution Log:",
            *[f"- {entry}" for entry in execution_log],
            "",
            "Verification:",
            f"- {verification_line}",
            "",
            "Final Status:",
            final_status,
        ],
    )


async def run_migration_analysis(
    source_url: str,
    target_url: str,
    use_mcp: bool = False,
) -> dict[str, str]:
    """Run the migration-analysis pipeline using manual orchestration."""

    reasoning_mode = "azure-ai" if is_azure_openai_configured() else "deterministic"
    print(f"[DISCOVERY] Snapshotting source: {source_url}")

    if use_mcp and reasoning_mode == "azure-ai":
        client = create_azure_openai_client()
        mcp_server_url = get_mcp_server_url()

        if _should_use_hosted_mcp(mcp_server_url):
            print(f"[MCP] Using Azure-hosted MCP server: {mcp_server_url}")
            mcp_tool = client.get_mcp_tool(
                name="health_checks",
                url=mcp_server_url,
                description="Live SSL, HTTP, and DNS checks for migration validation.",
                allowed_tools=[
                    "check_ssl_certificate",
                    "check_http_status",
                    "check_dns_resolution",
                ],
                approval_mode="never_require",
            )
            discovery_agent = _create_mcp_discovery_agent([mcp_tool])
            before_snapshot_json = await _snapshot_site_via_mcp(discovery_agent, source_url)

            print(f"[DISCOVERY] Snapshotting target: {target_url}")
            after_snapshot_json = await _snapshot_site_via_mcp(discovery_agent, target_url)
        else:
            from agent_framework import MCPStreamableHTTPTool

            if is_foundry_configured() and not mcp_server_url.lower().startswith("https://"):
                print(
                    "[MCP] Foundry is configured, but MCP_SERVER_URL is not public HTTPS. "
                    "Falling back to direct local MCP client mode.",
                )
            else:
                print(f"[MCP] Using local MCP server: {mcp_server_url}")

            async with MCPStreamableHTTPTool(
                name="health_checks",
                url=mcp_server_url,
            ) as mcp_tool:
                discovery_agent = _create_mcp_discovery_agent(mcp_tool)
                before_snapshot_json = await _snapshot_site_via_mcp(discovery_agent, source_url)

                print(f"[DISCOVERY] Snapshotting target: {target_url}")
                after_snapshot_json = await _snapshot_site_via_mcp(discovery_agent, target_url)
    else:
        if use_mcp and reasoning_mode != "azure-ai":
            print("[DISCOVERY] Azure reasoning is not configured. Falling back to direct deterministic discovery.")
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

    if reasoning_mode == "azure-ai":
        risk_assessor = create_risk_assessor_agent()
        diagnostician = create_diagnostician_agent()
        planner = create_planner_agent()

        risk_assessor_result = await risk_assessor.run(str(discovery_output))
        risk_assessor_output = str(risk_assessor_result)

        diagnostician_result = await diagnostician.run(str(risk_assessor_output))
        diagnostician_output = str(diagnostician_result)

        planner_result = await planner.run(str(diagnostician_output))
        planner_output = str(planner_result)
    else:
        print("[REASONING] Azure AI not configured. Using deterministic fallback outputs.")
        risk_assessor_output = _fallback_risk_assessment(comparison)
        diagnostician_output = _fallback_diagnostics(comparison)
        planner_output = _fallback_planner(comparison)

    return {
        "discovery": discovery_output,
        "before_snapshot": before_snapshot_json,
        "after_snapshot": after_snapshot_json,
        "comparison": comparison_json,
        "risk_assessor": risk_assessor_output,
        "diagnostician": diagnostician_output,
        "planner": planner_output,
        "reasoning_mode": reasoning_mode,
    }


async def run_executor(source_url: str, target_url: str, outputs: dict[str, str]) -> str:
    """Run the Executor stage after human approval."""

    if outputs.get("reasoning_mode") == "deterministic":
        return _fallback_executor(target_url, outputs)

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
