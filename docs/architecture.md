# MigrationOps Copilot: Architecture & Technical Deep Dive

This document expands on the implementation and structural design of MigrationOps Copilot.

## System Architecture: Data Flow

Data precisely cascades down the sequence. An agent only sees the prompt constraint, the tool outputs, and the raw text transmitted from the previous agent.

```mermaid
flowchart LR
    SNA[Discover Tools <br/> Snapshot JSON] -->|Comparison| RA[Triager Agent]
    RA -->|Markdown Context| DX[Diagnostician Agent]
    DX -->|Markdown Context| PL[Planner Agent]
    PL -->|Markdown Context| AP{Approval Gate}
    AP -->|Approved Plan| EX[Executor Agent]
```

## Core Technical Concepts

- **Sequential Pipeline vs Autonomous Loop:** By strictly moving from Discovery -> Triager -> Planner, the system limits the LLM's capability to hallucinate context or loop endlessly on simple tasks.
- **Data Grounding:** The foundation of all reasoning is a structured, deterministically compared JSON diff (`before_snapshot` vs `after_snapshot`). The LLM does not perform the inspection; it only interprets the hard data.
- **Security-First Mutability:** Destructive tooling (`tools/remediation.py`) explicitly mocks out its behavior. The orchestration logic is proven while keeping environments 100% safe.

## Key Modules

### `pipeline.py`
- **Purpose:** Central nervous system of the repository.
- **Inputs:** `source_url`, `target_url`, `use_mcp`.
- **Outputs:** Consolidated JSON dict enclosing all agent outputs.
- **Dependencies:** `agents.*`, `tools.*`, `azure_client`.

### `agents/triager.py`
- **Purpose:** Initial risk classification.
- **Inputs:** Snapshot comparison string.
- **Outputs:** Risk level, blocking status string.

### `tools/baseline.py`
- **Purpose:** Pure network IO execution.
- **Outputs:** Deduplicated finding IDs and an aggregate Health Score.
- **Relationships:** Powers the entire "Real" part of the application before LLM abstraction.

## Architecture Decisions

**Observed:**
- **Human Governance Native:** The approval step is physically hard-coded into `main.py` and decoupled cleanly in `app.py` via asynchronous polling mechanisms. The system assumes autonomous mutation on infrastructure is fundamentally unsafe without a gate.
- **Model Context Protocol Validation:** By abstracting the network tools through an MCP Server, the repository proves that external logic networks can safely audit an environment even if the agent processing lives securely off-premises.

**Inferred:**
- **Ephemeral State Architecture:** In `app.py`, state is held loosely in a Python global dictionary (`analysis_store`). This removes database scaffolding dependencies for the Hackathon context, implying it's optimized for stateless rapid deployment (e.g., Azure App Service containers).

## Current Limitations

- **Stateless API Memory:** As currently configured, restarting the `app.py` container clears the `analysis_store`, losing pending Execution states.
- **Deep DOM Spidering:** Health checks are restricted to SSL, DNS, and root index status. It does not recursive-spider applications for nested 404 links post-migration.
- **Simulated Executor Constraints:** The `simulate_cert_renewal()` tools intentionally stop short of actual system modifications. 

## Roadmap & Likely Next Steps

- *(Inferred)* Implementation of a Redis or SQLite storage backend for `analysis_store` to support distributed horizontal scaling.
- *(Inferred)* Expanding toolkits to actual Azure/AWS API execution layers integrating proper IAC modifying libraries.
- Expanding the Discovery agent suite to parse multi-page HTTP paths and deeper latency distribution graphs.

## Why this repo is technically interesting

MigrationOps Copilot demonstrates a masterclass in **Agentic Workflow Mapping**. Most initial LLM AI deployments errantly assign infinite tooling arrays to a single unbounded agent, resulting in context confusion, looping, and unpredictable infrastructure states. 

This repository enforces a **Supply Chain of AI Reasoning**. It fuses System 1 reasoning (deterministic, rapid Python network IO) perfectly with System 2 reasoning (deliberate, multi-stage Agent Swarms). It uses explicit sequential boundaries, effectively stopping hallucinations at the perimeter. It is a premium, structurally-sound exploration of modern SRE automation.
