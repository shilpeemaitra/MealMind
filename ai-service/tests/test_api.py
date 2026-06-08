"""API tests for the FastAPI service using a fake agent (no API key needed)."""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from app import main
from app.agent.graph import build_agent
from app.schemas import PlanRequest
from tests.fakes import ScriptedLLM, good_plan


def test_health():
    client = TestClient(main.app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


def test_plan_endpoint_with_fake_agent(monkeypatch):
    # Route /agent/plan through a fake-LLM agent instead of calling Claude.
    fake_agent = build_agent(llm_factory=lambda: ScriptedLLM([good_plan()]))

    def fake_run_plan(req: PlanRequest):
        return fake_agent.invoke({"request": req})["response"]

    monkeypatch.setattr(main, "run_plan", fake_run_plan)

    client = TestClient(main.app)
    payload = {
        "goal": "lose weight",
        "daily_calorie_target": 1800,
        "dietary_pattern": "vegetarian",
        "allergies": ["peanut"],
        "pantry": [
            {"name": "rice"},
            {"name": "spinach", "expires_on": "2026-06-10"},
            {"name": "oats"},
        ],
        "days": 2,
        "today": "2026-06-09",
    }
    res = client.post("/agent/plan", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert "days" in body and len(body["days"]) == 2
    assert "waste_report" in body
    assert body["waste_report"]["pantry_utilization_pct"] == 100
    # snake_case contract is honored
    assert "grocery_list" in body


def test_plan_endpoint_validates_input():
    client = TestClient(main.app)
    # Missing required daily_calorie_target → 422
    res = client.post("/agent/plan", json={"goal": "bulk up"})
    assert res.status_code == 422
