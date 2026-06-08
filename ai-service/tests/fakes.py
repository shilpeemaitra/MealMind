"""Deterministic fake LLMs for testing the agent without an API key.

These implement just enough of the LangChain chat-model interface that the graph
uses: an `.invoke(messages)` method returning an object with a `.content` string.
"""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class _Reply:
    content: str


class GarbageLLM:
    """Always returns non-JSON prose — simulates a malformed LLM response."""

    def __init__(self):
        self.calls = 0

    def invoke(self, _messages) -> "_Reply":
        self.calls += 1
        return _Reply(content="Sorry, I couldn't make a plan right now.")


class ScriptedLLM:
    """Returns a pre-baked sequence of JSON plans, one per `.invoke` call.

    Lets a test drive the re-plan loop: e.g. first a bad plan, then a good one.
    The last reply repeats if `.invoke` is called more times than scripted.
    """

    def __init__(self, plans: list[list[dict]]):
        self._replies = [json.dumps(p) for p in plans]
        self.calls = 0

    def invoke(self, _messages) -> _Reply:
        idx = min(self.calls, len(self._replies) - 1)
        self.calls += 1
        return _Reply(content=self._replies[idx])


def good_plan() -> list[dict]:
    """A clean 2-day vegetarian plan ~1800 cal/day that uses the pantry."""
    return [
        {
            "day": "Monday",
            "meals": [
                {"name": "Oatmeal", "calories": 350, "ingredients": ["oats", "milk", "banana"], "uses_pantry": ["oats"]},
                {"name": "Spinach rice bowl", "calories": 700, "ingredients": ["rice", "spinach", "olive oil"], "uses_pantry": ["rice", "spinach"]},
                {"name": "Tofu stir-fry", "calories": 750, "ingredients": ["tofu", "broccoli", "rice"], "uses_pantry": ["rice"]},
            ],
        },
        {
            "day": "Tuesday",
            "meals": [
                {"name": "Yogurt and apple", "calories": 300, "ingredients": ["yogurt", "apple"], "uses_pantry": []},
                {"name": "Lentil soup", "calories": 700, "ingredients": ["lentils", "carrot", "onion"], "uses_pantry": []},
                {"name": "Spinach pasta", "calories": 800, "ingredients": ["pasta", "spinach", "tomato"], "uses_pantry": ["spinach"]},
            ],
        },
    ]


def plan_with_allergen() -> list[dict]:
    """A plan that violates a peanut allergy and ignores expiring spinach."""
    return [
        {
            "day": "Monday",
            "meals": [
                {"name": "Peanut toast", "calories": 400, "ingredients": ["bread", "peanuts"], "uses_pantry": []},
                {"name": "Plain rice", "calories": 700, "ingredients": ["rice"], "uses_pantry": ["rice"]},
                {"name": "Pasta", "calories": 700, "ingredients": ["pasta", "tomato"], "uses_pantry": []},
            ],
        },
    ]
