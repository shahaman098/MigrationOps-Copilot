# MigrationOps Copilot — Demo Script (2 minutes)

## 0:00-0:10 — Hook
"Website migrations break things. Every time. SSL certs don't transfer. DNS doesn't propagate. Pages disappear. And you don't find out until your users do."

## 0:10-0:20 — Solution
"MigrationOps Copilot is your AI migration validation team. Give it your source site and your target site, and it validates the migration with five specialized AI agents."

## 0:20-0:35 — Architecture (show diagram)
Show the architecture diagram from README. Point out:
"Discovery phase snapshots both sites with real SSL, HTTP, and DNS checks. Then a Risk Assessor, Diagnostician, and Planner analyze the differences. You approve the plan. The Executor simulates the fix."

## 0:35-0:45 — Start Demo
"Let me show you. I'm migrating from google.com to a target site where the SSL cert has expired."
Run: `python main.py https://google.com https://expired.badssl.com`

## 0:45-1:00 — Discovery Phase
Show the discovery output. Point out:
"It snapshotted both sites. The comparison found critical changes — the SSL certificate is expired on the target, and the DNS IPs are different."

## 1:00-1:15 — Risk Assessment
Show Risk Assessor output. "The Risk Assessor classified this as CRITICAL and recommends blocking the migration until SSL is fixed."

## 1:15-1:25 — Diagnosis + Plan
Show Diagnostician and Planner output. "The Diagnostician identified SSL misconfiguration as the root cause. The Planner created a remediation plan."

## 1:25-1:35 — Approval
Show the approval prompt. Type `y`. "I approve the plan. The Executor now simulates the fix."

## 1:35-1:50 — Execution
Show Executor output with simulated remediation and real verification check.

## 1:50-2:00 — Close
"MigrationOps Copilot. Five AI agents. Real health checks. Human-in-the-loop governance. Built with Microsoft Agent Framework and Azure OpenAI. Your AI migration validation team."
