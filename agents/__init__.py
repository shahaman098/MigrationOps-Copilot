"""What is REAL: Agent exports for the live multi-agent pipeline.
What is MOCKED: Nothing.
What is SIMULATED: Executor-stage remediation actions.
"""

from agents.diagnostician import (
    DIAGNOSTICIAN_INSTRUCTIONS,
    create_diagnostician_agent,
)
from agents.executor import EXECUTOR_INSTRUCTIONS, create_executor_agent
from agents.monitor import MONITOR_INSTRUCTIONS, create_monitor_agent
from agents.planner import PLANNER_INSTRUCTIONS, create_planner_agent
from agents.triager import (
    RISK_ASSESSOR_INSTRUCTIONS,
    TRIAGER_INSTRUCTIONS,
    create_risk_assessor_agent,
    create_triager_agent,
)

__all__ = [
    "MONITOR_INSTRUCTIONS",
    "RISK_ASSESSOR_INSTRUCTIONS",
    "TRIAGER_INSTRUCTIONS",
    "DIAGNOSTICIAN_INSTRUCTIONS",
    "PLANNER_INSTRUCTIONS",
    "EXECUTOR_INSTRUCTIONS",
    "create_monitor_agent",
    "create_risk_assessor_agent",
    "create_triager_agent",
    "create_diagnostician_agent",
    "create_planner_agent",
    "create_executor_agent",
]
