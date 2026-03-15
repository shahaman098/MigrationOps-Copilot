"""What is REAL: CLI-driven migration analysis, human approval, and live verification.
What is MOCKED: Nothing.
What is SIMULATED: Remediation actions executed after approval.
"""

import asyncio
import sys

from dotenv import load_dotenv

from pipeline import run_executor, run_migration_analysis


async def main() -> None:
    load_dotenv()

    if len(sys.argv) != 3:
        print("Usage: python main.py <source_url> <target_url>")
        raise SystemExit(1)

    source_url = sys.argv[1]
    target_url = sys.argv[2]
    outputs = await run_migration_analysis(source_url, target_url)

    print("[DISCOVERY]")
    print(outputs["discovery"])
    print()
    print("[RISK ASSESSOR]")
    print(outputs["risk_assessor"])
    print()
    print("[DIAGNOSTICIAN]")
    print(outputs["diagnostician"])
    print()
    print("[PLANNER]")
    print(outputs["planner"])

    approval = input("Approve this migration remediation plan? (y/n): ").strip().lower()
    if approval != "y":
        print()
        print("Migration execution rejected. Stopping before Executor stage.")
        return

    executor_output = await run_executor(source_url, target_url, outputs)
    print()
    print("[EXECUTOR]")
    print(executor_output)


if __name__ == "__main__":
    asyncio.run(main())
