"""FastAPI entry point for the MealMind AI service.

One job: expose the LangGraph agent over HTTP so Spring Boot can call it.
Run locally:  uvicorn app.main:app --reload --port 8000
Swagger UI:   http://localhost:8000/docs
"""
from __future__ import annotations

from fastapi import FastAPI

from app.agent.graph import run_plan
from app.schemas import PlanRequest, PlanResponse

app = FastAPI(
    title="MealMind AI Service",
    description="LangGraph meal-planning agent backed by Claude.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/agent/plan", response_model=PlanResponse)
def plan(request: PlanRequest) -> PlanResponse:
    """Generate a constraint-satisfying weekly meal plan + grocery list."""
    return run_plan(request)
