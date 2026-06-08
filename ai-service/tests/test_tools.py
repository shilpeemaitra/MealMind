"""Unit tests for the agent's deterministic tools."""
from __future__ import annotations

from datetime import date

from app.agent.tools import (
    contains_allergen,
    expiring_soon,
    missing_from_pantry,
    nutrition_lookup,
    pantry_utilization,
    used_pantry_items,
)
from app.schemas import PantryItem


def test_nutrition_lookup_known_and_unknown():
    assert nutrition_lookup("rice") == 200
    assert nutrition_lookup("2 cups rice") == 200  # substring match
    assert nutrition_lookup("dragonfruit") == 150  # neutral default


def test_contains_allergen_detects_and_dedupes():
    ingredients = ["peanut butter", "bread", "peanuts"]
    found = contains_allergen(ingredients, ["peanut"])
    assert found == ["peanut"]  # matched once, not duplicated
    assert contains_allergen(["rice", "tofu"], ["shellfish"]) == []


def test_missing_from_pantry():
    pantry = [PantryItem(name="rice"), PantryItem(name="eggs")]
    needed = ["rice", "spinach", "2 eggs", "tomato"]
    missing = missing_from_pantry(needed, pantry)
    assert "rice" not in missing
    assert "2 eggs" not in missing  # 'eggs' matches '2 eggs'
    assert set(missing) == {"spinach", "tomato"}


def test_expiring_soon_uses_reference_date():
    today = date(2026, 6, 9)
    pantry = [
        PantryItem(name="spinach", expires_on=date(2026, 6, 10)),  # 1 day → soon
        PantryItem(name="rice", expires_on=date(2026, 12, 1)),     # far off
        PantryItem(name="milk"),                                    # no expiry
    ]
    soon = expiring_soon(pantry, today)
    assert [p.name for p in soon] == ["spinach"]


def test_pantry_utilization_and_used_items():
    pantry = [PantryItem(name="rice"), PantryItem(name="spinach"), PantryItem(name="tofu")]
    ingredients = ["rice", "spinach", "olive oil"]
    used = used_pantry_items(ingredients, pantry)
    assert set(used) == {"rice", "spinach"}
    assert pantry_utilization(ingredients, pantry) == 2 / 3


def test_pantry_utilization_empty_pantry_is_full():
    assert pantry_utilization(["rice"], []) == 1.0
