# MigrationOps Copilot Architecture

## Overview

MigrationOps Copilot validates a website migration by comparing a known source URL with a target URL, classifying the risk of the cutover, diagnosing unexpected differences, proposing remediation, and requiring human approval before any simulated action is taken.

The system is intentionally narrow:

- real SSL, HTTP, and DNS checks
- real Azure OpenAI reasoning
- simulated remediation
- CLI and web entry points
- optional MCP-based discovery path

## Runtime Flow

1. A user provides a source URL and a target URL from the CLI or web UI.
2. The discovery phase captures a live snapshot of both sites.
3. `compare_snapshots()` builds a structured migration diff.
4. The Risk Assessor agent classifies the migration as `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`.
5. The Diagnostician agent explains the likely root causes.
6. The Planner agent creates a prioritized remediation plan.
7. A human either approves or rejects the plan.
8. If approved, the Executor agent runs simulated remediation tools and a real HTTP verification check.

## Discovery And Comparison

### Direct discovery

The default discovery path uses `snapshot_site(url)` from `tools/baseline.py`.

For each URL it:

- extracts the hostname
- runs `check_ssl_certificate(hostname)`
- runs `check_http_status(url)`
- runs `check_dns_resolution(hostname)`
- combines the results into a single JSON snapshot

### Optional MCP discovery

If `use_mcp=True` or `--mcp` is passed on the CLI:

- `mcp_server/server.py` exposes the same health-check tools over MCP
- `pipeline.py` creates a Discovery agent with `MCPStreamableHTTPTool`
- the Discovery agent calls MCP tools and returns the same snapshot schema as the direct path

This keeps MCP additive. The default path remains the most reliable for demos and judging.

### Comparison engine

`compare_snapshots(before, after)` produces:

- a deduplicated list of findings
- stable finding IDs such as `ssl_expired` and `http_status_failed`
- severity levels
- summary counts
- `migration_health_score`
- `overall_risk`

Severity rules:

- `critical`: SSL check failure, expired cert, failed HTTP verification, 5xx regression, DNS failure
- `high`: SSL issuer/common-name changes, 2xx to 4xx regression
- `warning`: expiring-soon certs, large expiry drop, >2x latency increase
- `info`: DNS IP changes

`migration_health_score` starts at 100 and subtracts:

- 25 per critical finding
- 15 per high finding
- 5 per warning finding
- 0 per info finding

## Agents

### Risk Assessor

- File: `agents/triager.py`
- Input: migration comparison report
- Output: overall risk, blocking issues, expected vs unexpected changes, recommendation

### Diagnostician

- File: `agents/diagnostician.py`
- Input: risk assessment
- Output: root cause analysis for each issue

### Planner

- File: `agents/planner.py`
- Input: diagnostics report
- Output: before-go-live and post-go-live remediation plan

### Executor

- File: `agents/executor.py`
- Input: approved plan plus migration context
- Output: execution log, verification result, final status

The Executor uses:

- `simulate_cert_renewal`
- `simulate_cache_purge`
- `simulate_config_update`
- `check_http_status`

Only the verification call is real.

## Human Approval Flow

The approval boundary exists in both interfaces:

- CLI: `main.py`
- Web UI: `app.py` + `static/index.html`

The user sees discovery, risk, diagnostics, and planning output first. The Executor only runs after explicit approval.

This keeps the system grounded and makes the demo safer: reasoning is live, but infrastructure mutation is simulated.

## Interfaces

### CLI

```bash
python main.py <source_url> <target_url> [--mcp]
```

### Web UI

- `GET /` serves the single-page interface
- `POST /api/analyze` runs the pipeline and stores the result in memory
- `POST /api/execute` applies the approve/reject decision using the stored context

The web UI uses transient in-memory state keyed by `analysis_id`. There is no persistent storage.

## Authentication

`azure_client.py` centralizes Azure OpenAI client creation.

Supported auth paths:

- `AZURE_OPENAI_API_KEY` if present
- `AzureCliCredential` fallback for local development

This matters because local development is convenient with Azure CLI, but Azure App Service deployment is much more practical with API key auth for a hackathon prototype.

## Azure Deployment Path

The web UI is documented for Azure App Service deployment in `docs/azure-deploy.md`.

Supporting files:

- `Procfile`
- `startup.sh`

The default deployment path uses direct discovery. The optional MCP path would require a separate MCP server process.

## CI

GitHub Actions workflow: `.github/workflows/ci.yml`

It runs:

- syntax validation with `py_compile`
- non-Azure tests:
  - `tests/test_tools.py`
  - `tests/test_baseline.py`

Azure-backed tests are intentionally excluded from CI because they require credentials that are not available in GitHub Actions.

## Why This Architecture Fits The Hackathon

- It uses Microsoft Agent Framework directly for the reasoning agents.
- It has a real multi-stage handoff model instead of one generic prompt.
- It includes an optional MCP integration path for hero-tech alignment.
- It is narrow enough to demo clearly in under two minutes.
- It is honest about simulation boundaries while still grounding the workflow in real data.
