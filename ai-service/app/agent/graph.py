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
                                 grocery_list → END

The agentic bit is the `check_limits → plan_meals` back-edge: if a generated plan
violates a constraint (too many calories, contains an allergen), the graph routes
*back* to re-plan with feedback, instead of returning a bad answer. That self-
correction loop is what separates an "agent" from a one-shot prompt.
"""
from __future__ import annotations

import json
import os
from typing import Annotated, TypedDict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.agent.tools import contains_allergen, missing_from_pantry, nutrition_lookup
from app.schemas import DayPlan, Meal, PlanRequest, PlanResponse

# How many times we let the agent re-plan before giving up and returning best effort.
MAX_REVISIONS = 3

# Model id comes from env so you can swap Sonnet/Haiku without touching code.
AGENT_MODEL = os.getenv("AGENT_MODEL", "claude-sonnet-4-6")


# ---------------------------------------------------------------------------
# State: the shared dict that flows through the graph.
# ---------------------------------------------------------------------------
class AgentState(TypedDict, total=False):
    request: PlanRequest
    draft_days: list[dict]          # raw plan from the LLM (list of day dicts)
    violations: Annotated[list[str], "constraint failures from the last check"]
    revisions: int                  # how many times we've re-planned
    response: PlanResponse          # the final answer


def _llm() -> ChatAnthropic:
    # Opus 4.8 / 4.7 / Sonnet 4.6 use adaptive thinking; langchain-anthropic
    # passes model kwargs straight through. We keep it simple here.
    return ChatAnthropic(model=AGENT_MODEL, max_tokens=4096, timeout=60)


# ---------------------------------------------------------------------------
# Node 1: parse_request — normalize input, initialize counters.
# ---------------------------------------------------------------------------
def parse_request(state: AgentState) -> AgentState:
    return {"revisions": 0, "violations": []}


# ---------------------------------------------------------------------------
# Node 2: plan_meals — ask Claude for a plan. Includes prior violations as
# feedback so each re-plan attempt is smarter than the last.
# ---------------------------------------------------------------------------
def plan_meals(state: AgentState) -> AgentState:
    req = state["request"]
    violations = state.get("violations", [])

    feedback = ""
    if violations:
        feedback = (
            "\n\nYour previous plan had these problems — FIX them this time:\n- "
            + "\n- ".join(violations)
        )

    system = SystemMessage(
        content=(
            "You are a meal-planning assistant. Produce a JSON meal plan ONLY — no prose. "
            "The JSON must be an array of day objects, each shaped like: "
            '{"day": "Monday", "meals": [{"name": "...", "calories": 0, '
            '"ingredients": ["...", "..."]}]}. '
            "Plan breakfast, lunch, and dinner for each day. Prefer using the user's "
            "pantry ingredients. Respect the dietary pattern and avoid all allergens. "
            "Keep each day's total close to the calorie target."
        )
    )
    human = HumanMessage(
        content=(
            f"Goal: {req.goal}\n"
            f"Daily calorie target: {req.daily_calorie_target}\n"
            f"Dietary pattern: {req.dietary_pattern}\n"
            f"Allergies (must avoid): {', '.join(req.allergies) or 'none'}\n"
            f"Pantry (prefer these): {', '.join(req.pantry) or 'none'}\n"
            f"Plan {req.days} day(s)."
            f"{feedback}"
        )
    )

    raw = _llm().invoke([system, human]).content
    draft_days = _extract_json_array(raw)

    return {
        "draft_days": draft_days,
        "revisions": state.get("revisions", 0) + 1,
    }


# ---------------------------------------------------------------------------
# Node 3: check_limits — validate the draft against the hard constraints.
# This is deterministic Python (not the LLM): allergens and calorie budget.
# ---------------------------------------------------------------------------
def check_limits(state: AgentState) -> AgentState:
    req = state["request"]
    violations: list[str] = []

    for day in state.get("draft_days", []):
        day_name = day.get("day", "a day")
        all_ingredients: list[str] = []
        for meal in day.get("meals", []):
            all_ingredients.extend(meal.get("ingredients", []))

        # Allergen check
        hits = contains_allergen(all_ingredients, req.allergies)
        if hits:
            violations.append(f"{day_name} contains allergen(s): {', '.join(hits)}")

        # Calorie check (allow a 15% band around the target)
        total = sum(
            meal.get("calories") or _meal_calories(meal) for meal in day.get("meals", [])
        )
        upper = req.daily_calorie_target * 1.15
        lower = req.daily_calorie_target * 0.85
        if total > upper:
            violations.append(
                f"{day_name} has {total} cal, over the {req.daily_calorie_target} target."
            )
        elif total < lower:
            violations.append(
                f"{day_name} has only {total} cal, under the {req.daily_calorie_target} target."
            )

    return {"violations": violations}


# ---------------------------------------------------------------------------
# Conditional edge: did the plan pass? If not (and we have revisions left),
# route back to plan_meals. Otherwise continue to grocery_list.
# ---------------------------------------------------------------------------
def route_after_check(state: AgentState) -> str:
    violations = state.get("violations", [])
    revisions = state.get("revisions", 0)
    if violations and revisions < MAX_REVISIONS:
        return "replan"
    return "finish"


# ---------------------------------------------------------------------------
# Node 4: grocery_list — assemble the final response + grocery list.
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


def _extract_json_array(raw: str) -> list[dict]:
    """Pull a JSON array out of the model's text response, tolerating stray prose."""
    if isinstance(raw, list):  # some content blocks come back as a list
        raw = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in raw)
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return []


# ---------------------------------------------------------------------------
# Build the graph once at import time.
# ---------------------------------------------------------------------------
def build_agent():
    g = StateGraph(AgentState)
    g.add_node("parse_request", parse_request)
    g.add_node("plan_meals", plan_meals)
    g.add_node("check_limits", check_limits)
    g.add_node("grocery_list", build_grocery_list)

    g.set_entry_point("parse_request")
    g.add_edge("parse_request", "plan_meals")
    g.add_edge("plan_meals", "check_limits")
    g.add_conditional_edges(
        "check_limits",
        route_after_check,
        {"replan": "plan_meals", "finish": "grocery_list"},
    )
    g.add_edge("grocery_list", END)
    return g.compile()


_AGENT = build_agent()


def run_plan(request: PlanRequest) -> PlanResponse:
    """Entry point called by the FastAPI route."""
    final_state = _AGENT.invoke({"request": request})
    return final_state["response"]
