"""Request/response models for the AI service API.

These define the JSON contract between Spring Boot and this service. Keep them
in sync with the Java DTOs in `api/src/main/java/com/mealmind/api`.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    """What the user wants the agent to plan."""

    goal: str = Field(..., examples=["lose weight"])
    daily_calorie_target: int = Field(..., gt=0, examples=[1800])
    dietary_pattern: str = Field("none", examples=["vegetarian", "none", "vegan"])
    allergies: list[str] = Field(default_factory=list, examples=[["peanuts"]])
    pantry: list[str] = Field(
        default_factory=list,
        description="Ingredients the user already has at home.",
        examples=[["rice", "eggs", "spinach", "olive oil"]],
    )
    days: int = Field(7, ge=1, le=7)


class Meal(BaseModel):
    name: str
    calories: int
    ingredients: list[str]


class DayPlan(BaseModel):
    day: str
    meals: list[Meal]
    total_calories: int


class PlanResponse(BaseModel):
    """The agent's final answer."""

    days: list[DayPlan]
    grocery_list: list[str] = Field(
        description="Ingredients to buy = needed minus what's already in the pantry."
    )
    notes: str = Field("", description="Any caveats or adjustments the agent made.")
    revisions: int = Field(
        0, description="How many times the agent re-planned to satisfy constraints."
    )
