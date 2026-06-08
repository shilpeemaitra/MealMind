"""The MealMind agent, built as a LangGraph state machine.

Mental model (you're new to agents — read this once):
  - An AGENT is an LLM run in a loop. Each step it can think, optionally call a
    TOOL (a function you wrote), read the result, and decide what to do next.
  - LangGraph models that loop as a GRAPH: nodes = steps, edges = where to go next.
  - STATE is a shared dict that flows between nodes. Each node reads it and returns
    updates to it.

The graph:

    parse_request → plan_meals → check_limits ──fail──▶ (back to plan_meals)
                                      │ pass
                                      ▼
                                 waste_report → grocery_list → END

THE UNIQUENESS FACTOR — pantry-first 'use it up' optimization:
`check_limits` enforces three things and routes *back* to re-plan on any failure:
  1. No allergens.
  2. Daily calories within a band around the target.
  3. The plan USES UP enough of the pantry — especially items expiring soon.

That third constraint is what makes this novel: the agent minimizes food waste
and grocery cost, not just hitting macros. The plan→check→re-plan back-edge is
the self-correction loop that separates an 'agent' from a one-shot prompt.

Testability: the LLM is injected via a factory (`llm_factory`), so tests can run
the entire graph with a deterministic fake LLM and need no API key.
"""
from __future__ import annotations

import json
import os
from datetime import date
from typing import Annotated, Callable, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agent.tools import (
    contains_allergen,
    expiring_soon,
    missing_from_pantry,
    nutrition_lookup,
    pantry_utilization,
    used_pantry_items,
)
from app.schemas import DayPlan, Meal, PantryItem, PlanRequest, PlanResponse, WasteReport

# How many times we let the agent re-plan before returning best effort.
MAX_REVISIONS = 3

# Minimum fraction of pantry items a plan must use to pass (when a pantry exists).
MIN_PANTRY_UTILIZATION = 0.5

# Calorie band: a day must land within +/- this fraction of the target.
CALORIE_BAND = 0.15

# Model id comes from env so you can swap Sonnet/Haiku without touching code.
AGENT_MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-4-6")


def _default_llm() -> BaseChatModel:
    """Build the real Claude client. Imported lazily so tests that inject a fake
    LLM don't require langchain-anthropic or an API key at import time."""
    from langchain_anthropic import ChatAnthropic

    # max_retries handles transient 429/529 (common on the free tier) with backoff.
    return ChatAnthropic(model=AGENT_MODEL, max_tokens=4096, timeout=60, max_retries=3)


# ---------------------------------------------------------------------------
# State: the shared dict that flows through the graph.
# ---------------------------------------------------------------------------
class AgentState(TypedDict, total=False):
    request: PlanRequest
    draft_days: list[dict]          # raw plan from the LLM (list of day dicts)
    violations: Annotated[list[str], "constraint failures from the last check"]
    revisions: int                  # how many times we've re-planned
    waste_report: WasteReport
    response: PlanResponse          # the final answer


# ---------------------------------------------------------------------------
# Node 1: parse_request — normalize input, initialize counters.
# ---------------------------------------------------------------------------
def parse_request(state: AgentState) -> AgentState:
    return {"revisions": 0, "violations": []}


# ---------------------------------------------------------------------------
# Node 2: plan_meals — ask the LLM for a plan. Includes prior violations and an
# explicit list of expiring items as feedback so each attempt is smarter.
# ---------------------------------------------------------------------------
def _make_plan_meals(llm: BaseChatModel) -> Callable[[AgentState], AgentState]:
    def plan_meals(state: AgentState) -> AgentState:
        req = state["request"]
        ref = req.today or date.today()
        violations = state.get("violations", [])

        at_risk = expiring_soon(req.pantry, ref)
        at_risk_names = [p.name for p in at_risk]
        pantry_names = [p.name for p in req.pantry]

        feedback = ""
        if violations:
            feedback = (
                "\n\nYour previous plan had these problems — FIX them this time:\n- "
                + "\n- ".join(violations)
            )

        system = SystemMessage(
            content=(
                "You are a pantry-first meal-planning assistant whose top priority is "
                "to USE UP the ingredients the user already has — especially ones "
                "expiring soon — to minimize food waste and grocery cost. "
                "Produce a JSON meal plan ONLY — no prose. The JSON must be an array "
                "of day objects, each shaped like: "
                '{"day": "Monday", "meals": [{"name": "...", "calories": 0, '
                '"ingredients": ["...", "..."], "uses_pantry": ["..."]}]}. '
                'In "uses_pantry", list which of the user\'s pantry items that meal '
                "consumes. Plan breakfast, lunch, and dinner for each day. Respect the "
                "dietary pattern, avoid all allergens, and keep each day's total close "
                "to the calorie target."
            )
        )
        human = HumanMessage(
            content=(
                f"Goal: {req.goal}\n"
                f"Daily calorie target: {req.daily_calorie_target}\n"
                f"Dietary pattern: {req.dietary_pattern}\n"
                f"Allergies (must avoid): {', '.join(req.allergies) or 'none'}\n"
                f"Pantry (USE THESE UP): {', '.join(pantry_names) or 'none'}\n"
                f"Expiring SOON — prioritize: {', '.join(at_risk_names) or 'none'}\n"
                f"Plan {req.days} day(s)."
                f"{feedback}"
            )
        )

        raw = llm.invoke([system, human]).content
        draft_days = _extract_json_array(raw)

        return {
            "draft_days": draft_days,
            "revisions": state.get("revisions", 0) + 1,
        }

    return plan_meals


# ---------------------------------------------------------------------------
# Node 3: check_limits — validate the draft against the hard constraints.
# Deterministic Python (not the LLM): allergens, calorie budget, pantry use.
# ---------------------------------------------------------------------------
def check_limits(state: AgentState) -> AgentState:
    req = state["request"]
    ref = req.today or date.today()
    violations: list[str] = []

    draft_days = state.get("draft_days", [])

    # An empty draft (LLM returned no parseable JSON) must NOT silently pass —
    # otherwise the user gets a blank plan with a misleading 100% waste score.
    # Flag it so the agent re-plans.
    if not draft_days:
        return {"violations": ["The plan was empty or unparseable; regenerate it."]}

    all_ingredients: list[str] = []
    for day in draft_days:
        day_name = day.get("day", "a day")
        day_ingredients: list[str] = []
        for meal in day.get("meals", []):
            day_ingredients.extend(meal.get("ingredients", []))
        all_ingredients.extend(day_ingredients)

        # Allergen check
        hits = contains_allergen(day_ingredients, req.allergies)
        if hits:
            violations.append(f"{day_name} contains allergen(s): {', '.join(hits)}")

        # Calorie check (band around the target)
        total = sum(
            meal.get("calories") or _meal_calories(meal) for meal in day.get("meals", [])
        )
        upper = req.daily_calorie_target * (1 + CALORIE_BAND)
        lower = req.daily_calorie_target * (1 - CALORIE_BAND)
        if total > upper:
            violations.append(
                f"{day_name} has {total} cal, over the {req.daily_calorie_target} target."
            )
        elif total < lower:
            violations.append(
                f"{day_name} has only {total} cal, under the {req.daily_calorie_target} target."
            )

    # Pantry-utilization check (the uniqueness constraint)
    if req.pantry:
        util = pantry_utilization(all_ingredients, req.pantry)
        if util < MIN_PANTRY_UTILIZATION:
            violations.append(
                f"Plan only uses {round(util * 100)}% of the pantry; "
                f"use at least {round(MIN_PANTRY_UTILIZATION * 100)}% to cut waste."
            )

        # Expiring items must be rescued
        at_risk = expiring_soon(req.pantry, ref)
        used_names = {n.lower() for n in used_pantry_items(all_ingredients, req.pantry)}
        wasted_at_risk = [p.name for p in at_risk if p.name.lower() not in used_names]
        if wasted_at_risk:
            violations.append(
                "These items expire soon but go unused: " + ", ".join(wasted_at_risk)
            )

    return {"violations": violations}


# ---------------------------------------------------------------------------
# Conditional edge: did the plan pass? If not (and revisions remain), re-plan.
# ---------------------------------------------------------------------------
def route_after_check(state: AgentState) -> str:
    violations = state.get("violations", [])
    revisions = state.get("revisions", 0)
    if violations and revisions < MAX_REVISIONS:
        return "replan"
    return "finish"


# ---------------------------------------------------------------------------
# Node 4: waste_report — compute the signature 'use it up' metrics.
# ---------------------------------------------------------------------------
def build_waste_report(state: AgentState) -> AgentState:
    req = state["request"]
    ref = req.today or date.today()

    all_ingredients: list[str] = []
    for day in state.get("draft_days", []):
        for meal in day.get("meals", []):
            all_ingredients.extend(meal.get("ingredients", []))

    used = used_pantry_items(all_ingredients, req.pantry)
    used_lower = {n.lower() for n in used}
    at_risk = expiring_soon(req.pantry, ref)
    total = len(req.pantry)
    util_pct = round((len(used) / total) * 100) if total else 100

    report = WasteReport(
        pantry_items_total=total,
        pantry_items_used=len(used),
        pantry_utilization_pct=util_pct,
        expiring_soon_total=len(at_risk),
        expiring_soon_used=sum(1 for p in at_risk if p.name.lower() in used_lower),
        unused_items=[p.name for p in req.pantry if p.name.lower() not in used_lower],
    )
    return {"waste_report": report}


# ---------------------------------------------------------------------------
# Node 5: grocery_list — assemble the final response.
# ---------------------------------------------------------------------------
def build_grocery_list(state: AgentState) -> AgentState:
    req = state["request"]
    days: list[DayPlan] = []
    all_needed: list[str] = []

    for day in state.get("draft_days", []):
        meals: list[Meal] = []
        for meal in day.get("meals", []):
            ingredients = meal.get("ingredients", [])
            all_needed.extend(ingredients)
            meals.append(
                Meal(
                    name=meal.get("name", "Meal"),
                    calories=meal.get("calories") or _meal_calories(meal),
                    ingredients=ingredients,
                    uses_pantry=meal.get("uses_pantry", []),
                )
            )
        days.append(
            DayPlan(
                day=day.get("day", "Day"),
                meals=meals,
                total_calories=sum(m.calories for m in meals),
            )
        )

    grocery = missing_from_pantry(all_needed, req.pantry)
    notes = ""
    if state.get("violations"):
        notes = (
            "Returned best-effort plan after "
            f"{state.get('revisions', 0)} attempts; some targets may be slightly off."
        )

    response = PlanResponse(
        days=days,
        grocery_list=grocery,
        waste_report=state["waste_report"],
        notes=notes,
        revisions=state.get("revisions", 0),
    )
    return {"response": response}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _meal_calories(meal: dict) -> int:
    """Estimate a meal's calories from its ingredients if the LLM omitted them."""
    return sum(nutrition_lookup(i) for i in meal.get("ingredients", []))


def _extract_json_array(raw) -> list[dict]:
    """Pull a JSON array out of the model's text response, tolerating stray prose."""
    if isinstance(raw, list):  # some content blocks come back as a list of parts
        raw = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part) for part in raw
        )
    if not isinstance(raw, str):
        return []
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        parsed = json.loads(raw[start : end + 1])
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# Build the graph. `llm_factory` lets tests inject a fake LLM.
# ---------------------------------------------------------------------------
def build_agent(llm_factory: Callable[[], BaseChatModel] = _default_llm):
    llm = llm_factory()
    g = StateGraph(AgentState)
    g.add_node("parse_request", parse_request)
    g.add_node("plan_meals", _make_plan_meals(llm))
    g.add_node("check_limits", check_limits)
    # Node name must differ from the state key it writes ("waste_report").
    g.add_node("compute_waste", build_waste_report)
    g.add_node("grocery_list", build_grocery_list)

    g.set_entry_point("parse_request")
    g.add_edge("parse_request", "plan_meals")
    g.add_edge("plan_meals", "check_limits")
    g.add_conditional_edges(
        "check_limits",
        route_after_check,
        {"replan": "plan_meals", "finish": "compute_waste"},
    )
    g.add_edge("compute_waste", "grocery_list")
    g.add_edge("grocery_list", END)
    return g.compile()


# Lazily build the real agent on first use so importing this module never
# requires an API key (important for tests and for `--reload` dev startup).
_AGENT = None


def run_plan(request: PlanRequest) -> PlanResponse:
    """Entry point called by the FastAPI route."""
    global _AGENT
    if _AGENT is None:
        _AGENT = build_agent()
    final_state = _AGENT.invoke({"request": request})
    return final_state["response"]
