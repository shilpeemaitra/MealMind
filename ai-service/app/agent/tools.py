"""Tools the agent / constraint-checker uses.

Right now these are plain Python functions used by the graph's `check_limits` node.
In Week 2 you can also expose them to the LLM as LangChain tools (so the model can
*call* them mid-reasoning) — the function bodies stay the same.

Starting with a small local nutrition table keeps the app fully offline and free.
Later, swap `nutrition_lookup` for a real API (e.g. USDA FoodData Central) without
changing any callers.
"""
from __future__ import annotations

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
        if a and any(a in ing for ing in lowered):
            found.append(allergen)
    return found


def missing_from_pantry(needed: list[str], pantry: list[str]) -> list[str]:
    """Ingredients that must be bought = needed minus what's already on hand."""
    have = {p.lower().strip() for p in pantry}
    missing: list[str] = []
    seen: set[str] = set()
    for item in needed:
        key = item.lower().strip()
        if key in seen:
            continue
        seen.add(key)
        # "in pantry" if any pantry item is a substring (e.g. "eggs" covers "2 eggs")
        if not any(h in key or key in h for h in have):
            missing.append(item)
    return missing
