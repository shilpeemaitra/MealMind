"""Tools the agent / constraint-checker uses.

These are plain Python functions used by the graph nodes. The pantry-first logic
lives here: expiry urgency, allergen detection, calorie estimation, and the
pantry-utilization scoring that drives the 'use it up' optimization.

Starting with a small local nutrition table keeps the app fully offline and free.
Later, swap `nutrition_lookup` for a real API (e.g. USDA FoodData Central) without
changing any callers.
"""
from __future__ import annotations

from datetime import date, timedelta

from app.schemas import PantryItem

# Items expiring within this many days of the reference date are "at risk".
EXPIRING_SOON_DAYS = 3

# Rough calories per typical serving. Lowercased keys; substring match.
_NUTRITION_TABLE: dict[str, int] = {
    "rice": 200,
    "oats": 150,
    "eggs": 78,
    "egg": 78,
    "spinach": 23,
    "chicken": 230,
    "tofu": 180,
    "lentils": 230,
    "beans": 245,
    "bread": 80,
    "olive oil": 120,
    "yogurt": 150,
    "banana": 105,
    "apple": 95,
    "peanut": 190,
    "peanuts": 190,
    "almond": 160,
    "milk": 103,
    "cheese": 113,
    "pasta": 220,
    "tomato": 22,
    "avocado": 240,
    "salmon": 280,
    "broccoli": 55,
    "potato": 160,
    "carrot": 25,
    "onion": 40,
    "mushroom": 22,
}


def nutrition_lookup(ingredient: str) -> int:
    """Return approximate calories for one serving of an ingredient.

    Falls back to a neutral default for unknown ingredients so the agent can
    still produce a plan; the constraint checker will flag big misses.
    """
    key = ingredient.strip().lower()
    for name, cals in _NUTRITION_TABLE.items():
        if name in key:
            return cals
    return 150  # neutral default for unknown foods


def contains_allergen(ingredients: list[str], allergies: list[str]) -> list[str]:
    """Return the list of allergens found in the ingredients (empty if clean)."""
    found: list[str] = []
    lowered = [i.lower() for i in ingredients]
    for allergen in allergies:
        a = allergen.lower().strip()
        if a and any(a in ing for ing in lowered) and allergen not in found:
            found.append(allergen)
    return found


def _matches(pantry_name: str, ingredient: str) -> bool:
    """True if an ingredient string refers to a given pantry item.

    Substring match in either direction so 'eggs' matches '2 eggs' and
    'cherry tomatoes' matches 'tomato'.
    """
    p = pantry_name.lower().strip()
    i = ingredient.lower().strip()
    return bool(p) and (p in i or i in p)


def missing_from_pantry(needed: list[str], pantry: list[PantryItem]) -> list[str]:
    """Ingredients that must be bought = needed minus what's already on hand."""
    missing: list[str] = []
    seen: set[str] = set()
    for item in needed:
        key = item.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        if not any(_matches(p.name, item) for p in pantry):
            missing.append(item)
    return missing


def expiring_soon(pantry: list[PantryItem], today: date) -> list[PantryItem]:
    """Pantry items expiring within EXPIRING_SOON_DAYS of the reference date."""
    cutoff = today + timedelta(days=EXPIRING_SOON_DAYS)
    return [p for p in pantry if p.expires_on is not None and p.expires_on <= cutoff]


def used_pantry_items(all_ingredients: list[str], pantry: list[PantryItem]) -> list[str]:
    """Which pantry item names appear in the plan's ingredients."""
    used: list[str] = []
    for p in pantry:
        if any(_matches(p.name, ing) for ing in all_ingredients):
            used.append(p.name)
    return used


def pantry_utilization(all_ingredients: list[str], pantry: list[PantryItem]) -> float:
    """Fraction (0..1) of pantry items the plan consumes. Empty pantry → 1.0."""
    if not pantry:
        return 1.0
    used = used_pantry_items(all_ingredients, pantry)
    return len(used) / len(pantry)
