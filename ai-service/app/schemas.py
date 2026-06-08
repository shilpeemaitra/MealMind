"""Request/response models for the AI service API.

These define the JSON contract between Spring Boot and this service. Keep them
in sync with the Java DTOs in `api/src/main/java/com/mealmind/api`.
"""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PantryItem(BaseModel):
    """An ingredient the user already has, with optional expiry.

    Expiry is what powers the 'use it up' optimization: the agent prioritizes
    ingredients that will spoil soonest, minimizing food waste.
    """

    name: str = Field(..., examples=["spinach"])
    quantity: str = Field("", examples=["1 bag", "200g"])
    expires_on: date | None = Field(
        None,
        description="ISO date the item expires. Items expiring sooner are prioritized.",
        examples=["2026-06-12"],
    )


class PlanRequest(BaseModel):
    """What the user wants the agent to plan."""

    goal: str = Field(..., examples=["lose weight"])
    daily_calorie_target: int = Field(..., gt=0, examples=[1800])
    dietary_pattern: str = Field("none", examples=["vegetarian", "none", "vegan"])
    allergies: list[str] = Field(default_factory=list, examples=[["peanuts"]])
    pantry: list[PantryItem] = Field(
        default_factory=list,
        description="Ingredients the user already has. The agent optimizes to use these up.",
    )
    days: int = Field(7, ge=1, le=7)
    # Anchor date for expiry math; defaults to today on the server if omitted.
    today: date | None = Field(None, description="Reference date for expiry urgency.")


class Meal(BaseModel):
    name: str
    calories: int
    ingredients: list[str]
    # Which of the user's pantry items this meal uses up (for the waste story).
    uses_pantry: list[str] = Field(default_factory=list)


class DayPlan(BaseModel):
    day: str
    meals: list[Meal]
    total_calories: int


class WasteReport(BaseModel):
    """The signature output: how well the plan uses up the pantry."""

    pantry_items_total: int
    pantry_items_used: int
    pantry_utilization_pct: int = Field(
        ..., description="% of pantry items the plan actually consumes."
    )
    expiring_soon_total: int = Field(
        ..., description="Pantry items expiring within 3 days of the reference date."
    )
    expiring_soon_used: int = Field(
        ..., description="How many of those at-risk items the plan rescues."
    )
    unused_items: list[str] = Field(default_factory=list)


class PlanResponse(BaseModel):
    """The agent's final answer."""

    days: list[DayPlan]
    grocery_list: list[str] = Field(
        description="Ingredients to buy = needed minus what's already in the pantry."
    )
    waste_report: WasteReport
    notes: str = Field("", description="Any caveats or adjustments the agent made.")
    revisions: int = Field(
        0, description="How many times the agent re-planned to satisfy constraints."
    )
