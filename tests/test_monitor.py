"""What is REAL: Azure OpenAI reasoning and live Monitor agent tool execution.
What is MOCKED: Nothing.
What is SIMULATED: Nothing.
"""

import asyncio
from pathlib import Path
import sys

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.monitor import create_monitor_agent


async def main() -> None:
    load_dotenv()
    agent = create_monitor_agent()
    result = await agent.run("Check the health of https://expired.badssl.com")
    output_text = str(result)

    assert "expired.badssl.com" in output_text.lower(), output_text
    assert "ssl" in output_text.lower(), output_text

    print(output_text)


if __name__ == "__main__":
    asyncio.run(main())
