"""End-to-end tests of the LangGraph agent using a scripted fake LLM.

These prove the agentic behavior without any API key:
 - a clean plan passes on the first try and produces a correct waste report
 - a bad plan (allergen + wasted expiring item) triggers a re-plan, and the
   agent recovers when the next attempt is clean
"""
from __future__ import annotations

from datetime import date

from app.agent.graph import build_agent
from app.schemas import PantryItem, PlanRequest
from tests.fakes import GarbageLLM, ScriptedLLM, good_plan, plan_with_allergen


def _request(**overrides) -> PlanRequest:
    base = dict(
        goal="lose weight",
        daily_calorie_target=1800,
        dietary_pattern="vegetarian",
        allergies=["peanut"],
        pantry=[
            PantryItem(name="rice"),
            PantryItem(name="spinach", expires_on=date(2026, 6, 10)),
            PantryItem(name="oats"),
        ],
        days=2,
        today=date(2026, 6, 9),
    )
    base.update(overrides)
    return PlanRequest(**base)


def test_clean_plan_passes_first_try():
    llm = ScriptedLLM([good_plan()])
    agent = build_agent(llm_factory=lambda: llm)

    result = agent.invoke({"request": _request()})
    response = result["response"]

    assert response.revisions == 1  # planned once, no re-plan
    assert llm.calls == 1
    assert len(response.days) == 2
    # The good plan uses rice, spinach, oats → 100% utilization, spinach rescued.
    assert response.waste_report.pantry_utilization_pct == 100
    assert response.waste_report.expiring_soon_used == 1
    assert response.waste_report.unused_items == []


def test_allergen_plan_triggers_replan_then_recovers():
    # First attempt: peanut allergen + spinach (expiring) unused → must re-plan.
    # Second attempt: clean plan → passes.
    llm = ScriptedLLM([plan_with_allergen(), good_plan()])
    agent = build_agent(llm_factory=lambda: llm)

    result = agent.invoke({"request": _request()})
    response = result["response"]

    assert llm.calls == 2  # the agent re-planned exactly once
    assert response.revisions == 2
    # Final plan is clean: no peanut anywhere.
    all_ing = [i for d in response.days for m in d.meals for i in m.ingredients]
    assert not any("peanut" in i.lower() for i in all_ing)


def test_persistently_bad_plan_returns_best_effort():
    # The fake only ever returns the allergen plan → agent exhausts revisions.
    llm = ScriptedLLM([plan_with_allergen()])
    agent = build_agent(llm_factory=lambda: llm)

    result = agent.invoke({"request": _request()})
    response = result["response"]

    assert response.revisions == 3  # hit MAX_REVISIONS
    assert "best-effort" in response.notes
    assert response.waste_report is not None  # still returns a structured answer


def test_empty_plan_is_flagged_and_retried():
    # The LLM never returns valid JSON → every draft is empty. The agent must
    # NOT pass a blank plan; it should re-plan up to MAX_REVISIONS then return
    # a best-effort (empty) response with a note, not crash.
    llm = GarbageLLM()
    agent = build_agent(llm_factory=lambda: llm)

    result = agent.invoke({"request": _request()})
    response = result["response"]

    assert llm.calls == 3  # retried to the limit instead of accepting empty
    assert response.days == []
    assert response.notes  # carries a best-effort note


def test_grocery_list_excludes_pantry_items():
    llm = ScriptedLLM([good_plan()])
    agent = build_agent(llm_factory=lambda: llm)

    response = agent.invoke({"request": _request()})["response"]
    # Pantry has rice, spinach, oats — none should appear on the grocery list.
    lowered = [g.lower() for g in response.grocery_list]
    assert not any("rice" in g for g in lowered)
    assert not any("oats" in g for g in lowered)
    # But things not in the pantry (e.g. tofu, lentils) should.
    assert any("tofu" in g for g in lowered) or any("lentils" in g for g in lowered)
