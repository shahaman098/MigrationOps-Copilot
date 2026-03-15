"""What is REAL: FastAPI web access to the live migration-analysis pipeline.
What is MOCKED: Nothing.
What is SIMULATED: Executor-stage remediation actions after approval.
"""

import json
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from pipeline import run_executor, run_migration_analysis

load_dotenv()

app = FastAPI(title="MigrationOps Copilot")
analysis_store: dict[str, dict[str, object]] = {}
INDEX_PATH = Path(__file__).resolve().parent / "static" / "index.html"


class AnalyzeRequest(BaseModel):
    source_url: str
    target_url: str
    use_mcp: bool = False


class ExecuteRequest(BaseModel):
    analysis_id: str
    approved: bool


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(INDEX_PATH)


@app.post("/api/analyze")
async def analyze(request: AnalyzeRequest) -> dict[str, object]:
    outputs = await run_migration_analysis(
        request.source_url,
        request.target_url,
        use_mcp=request.use_mcp,
    )
    comparison = json.loads(outputs["comparison"])
    analysis_id = str(uuid4())
    analysis_store[analysis_id] = {
        "source_url": request.source_url,
        "target_url": request.target_url,
        "outputs": outputs,
    }

    return {
        "analysis_id": analysis_id,
        "discovery": {
            "comparison_report": outputs["discovery"],
            "changes": comparison["changes"],
            "summary": comparison["summary"],
            "risk_level": comparison["overall_risk"],
            "health_score": comparison["summary"]["migration_health_score"],
        },
        "risk_assessor": outputs["risk_assessor"],
        "diagnostician": outputs["diagnostician"],
        "planner": outputs["planner"],
        "status": "awaiting_approval",
    }


@app.post("/api/execute")
async def execute(request: ExecuteRequest) -> dict[str, object]:
    analysis = analysis_store.get(request.analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Unknown analysis_id.")

    if not request.approved:
        return {
            "status": "rejected",
            "message": "Migration execution rejected. No remediation actions were run.",
        }

    executor_output = await run_executor(
        str(analysis["source_url"]),
        str(analysis["target_url"]),
        analysis["outputs"],
    )
    return {
        "status": "executed",
        "executor": executor_output,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
