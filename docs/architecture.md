# MigrationOps Copilot Architecture

## Overview

MigrationOps Copilot is a CLI-first, multi-agent migration validation system built on Microsoft Agent Framework and Azure OpenAI. It compares a known-good source site with a migrated target site, identifies risky differences, explains likely root causes, proposes remediation, and requires human approval before any simulated action is taken.

## High-Level Flow

1. The user runs `python main.py <source_url> <target_url>`.
2. The discovery phase snapshots the source site with real SSL, HTTP, and DNS checks.
3. The discovery phase snapshots the target site with the same real checks.
4. A comparison engine produces a structured diff and overall risk level.
5. The Risk Assessor agent evaluates whether the migration is safe.
6. The Diagnostician agent explains why any blocking differences appeared.
7. The Planner agent creates a prioritized remediation plan.
8. A human approves or rejects the plan in the CLI.
9. If approved, the Executor agent runs simulated remediation actions and a real post-action HTTP verification check.

## Agent Roles

### Discovery

- Implemented as plain Python functions in `tools/baseline.py`, not as an active agent in the main migration flow
- Captures:
  - SSL certificate state
  - HTTP response behavior
  - DNS resolution state
- Produces:
  - pre-migration snapshot
  - post-migration snapshot
  - structured comparison report

### Risk Assessor

- Implemented in `agents/triager.py`
- Receives the migration comparison report
- Classifies overall migration risk as `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`
- Separates expected changes from unexpected or blocking changes

### Diagnostician

- Implemented in `agents/diagnostician.py`
- Receives the risk assessment
- Performs root cause analysis for each migration issue
- Categorizes problems such as:
  - DNS propagation
  - SSL configuration
  - hosting mismatch
  - application error
  - expected change

### Planner

- Implemented in `agents/planner.py`
- Receives the diagnostics report
- Produces a prioritized remediation plan
- Splits recommendations into:
  - Before Go-Live
  - Post Go-Live Monitoring

### Executor

- Implemented in `agents/executor.py`
- Receives the approved remediation plan and migration context
- Runs simulated remediation tools only
- Performs a real HTTP verification check against the target URL

## Data Flow

### 1. Snapshot Collection

`snapshot_site(url)` in `tools/baseline.py`:
- extracts the hostname from the URL
- calls `check_ssl_certificate(hostname)`
- calls `check_http_status(url)`
- calls `check_dns_resolution(hostname)`
- combines all three JSON results into one JSON snapshot

### 2. Baseline Comparison

`compare_snapshots(before, after)`:
- parses the two snapshot JSON strings
- compares key SSL, HTTP, and DNS fields
- emits a list of structured changes with severity
- calculates:
  - total changes
  - critical changes
  - warning changes
  - info changes
  - overall risk

Key comparison rules include:
- SSL expired or SSL error → critical
- HTTP changed from healthy to failing → critical
- DNS failure → critical
- SSL issuer change → high
- response time increase >2x → warning
- DNS IP change → info

### 3. Agent Pipeline

The pipeline in `pipeline.py` uses manual orchestration:

1. Discovery builds the comparison report
2. Risk Assessor runs on the comparison report
3. Diagnostician runs on the Risk Assessor output
4. Planner runs on the Diagnostician output
5. Executor runs only after approval

This keeps the implementation simple and reliable by passing `str(previous_output)` between stages.

## Tooling

### Real Tools

Defined in `tools/health_checks.py`:

- `check_ssl_certificate(hostname)`
  - real TLS handshake
  - returns certificate expiry and metadata
- `check_http_status(url)`
  - real HTTP request
  - returns status code, latency, and redirect behavior
- `check_dns_resolution(hostname)`
  - real DNS lookup
  - returns resolved IPs and timing

### Simulated Tools

Defined in `tools/remediation.py`:

- `simulate_cert_renewal(hostname)`
- `simulate_cache_purge(hostname)`
- `simulate_config_update(setting, value)`

These are intentionally simulated and clearly labeled as such in both code and output.

## Approval Flow

The approval gate is implemented in `main.py`.

- The user sees the discovery output, risk assessment, diagnostics, and remediation plan.
- The CLI prompts:
  - `Approve this migration remediation plan? (y/n):`
- If rejected:
  - execution stops cleanly
- If approved:
  - the Executor runs simulated remediation plus real verification

This creates a human-in-the-loop safety boundary between reasoning and action.

## Microsoft Technology Integration Points

### Microsoft Agent Framework

- All five agents are created with `AzureOpenAIResponsesClient`
- Real agent tools use the `@tool` decorator
- The system uses the RC4 Agent Framework package already validated in the repo

### Azure OpenAI

- All reasoning agents use Azure OpenAI as the model backend
- Credentials are supplied through `AzureCliCredential`
- Endpoint and deployment are configured via `.env`

### Azure MCP

- Not implemented in the current repo
- The architecture leaves room to move discovery tools behind an MCP server later if needed

### GitHub Copilot Agent Mode

- Used during development to accelerate implementation of the multi-agent workflow

## Why This Architecture Works

- It keeps data collection real and grounded in live network checks
- It isolates high-risk infrastructure actions behind simulation and human approval
- It uses specialized agents instead of one generic prompt
- It creates an auditable migration workflow that is easy to demo and easy to extend
