"""FastAPI entry point for the MealMind AI service.

One job: expose the LangGraph agent over HTTP so Spring Boot can call it.
Run locally:  uvicorn app.main:app --reload --port 8000
Swagger UI:   http://localhost:8000/docs
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, HTTPException

from app.agent.graph import run_plan
from app.schemas import PlanRequest, PlanResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("mealmind")

app = FastAPI(
    title="MealMind AI Service",
    description="LangGraph meal-planning agent backed by Claude.",
    version="0.2.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agent/plan", response_model=PlanResponse)
def plan(request: PlanRequest) -> PlanResponse:
    """Generate a constraint-satisfying weekly meal plan + grocery list.

    Errors from the LLM (bad key, timeout, malformed output) are turned into a
    clean 502 so the caller never sees a raw stack trace.
    """
    started = time.monotonic()
    try:
        result = run_plan(request)
    except Exception as exc:  # noqa: BLE001 — convert any agent failure to a clean error
        log.exception("agent failed")
        raise HTTPException(
            status_code=502,
            detail="The meal-planning agent failed to generate a plan. Please try again.",
        ) from exc

    elapsed = time.monotonic() - started
    # Observability: a cheap LangSmith stand-in. Shows the agent's behavior in logs.
    log.info(
        "plan generated: days=%d revisions=%d pantry_util=%d%% elapsed=%.1fs",
        len(result.days),
        result.revisions,
        result.waste_report.pantry_utilization_pct,
        elapsed,
    )
    return result
