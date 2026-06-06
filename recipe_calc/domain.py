"""Core recipe-cost calculation logic."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Mapping

ROMAN_NUMERALS = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}

RecipeMap = dict[str, dict[str, float]]
PriceMap = dict[str, float]


DEFAULT_DATA: dict[str, Any] = {
    "prices": {
        "Wooden Plank": 0.0,
        "Cobblestone": 0.0,
        "Iron Ingot": 0.0,
        "Redstone Dust": 0.0,
        "Glass": 0.0,
        "Iron Block": 0.0,
        "Redstone Repeater": 0.0,
        "Photovoltaic Cell I": 0.0,
    },
    "recipes": {
        "Piston": {
            "Wooden Plank": 3,
            "Cobblestone": 4,
            "Iron Ingot": 1,
            "Redstone Dust": 1,
        },
        "Mirror": {
            "Glass": 3,
            "Iron Ingot": 1,
        },
        "Solar Panel I": {
            "Mirror": 3,
            "Wooden Plank": 5,
            "Redstone Dust": 1,
        },
        "Solar Panel II": {
            "Solar Panel I": 8,
            "Piston": 1,
        },
        "Solar Panel III": {
            "Solar Panel II": 4,
            "Iron Block": 1,
            "Redstone Repeater": 1,
            "Photovoltaic Cell I": 3,
        },
    },
}


class RecipeError(ValueError):
    """Raised when recipe data cannot be calculated or saved safely."""


@dataclass(slots=True)
class CraftNode:
    """A display-friendly node in an expanded crafting tree."""

    item_name: str
    quantity: float
    kind: str
    unit_cost: float | None
    line_cost: float
    children: list["CraftNode"] = field(default_factory=list)


@dataclass(slots=True)
class CalculationResult:
    """The raw and tree totals for a requested item quantity."""

    item_name: str
    quantity: float
    total_cost: float
    raw_totals: dict[str, float]
    tree: CraftNode


def normalise_name(name: str) -> str:
    """Normalise user-entered item names while preserving common Roman numerals."""
    words = " ".join(name.strip().split()).split(" ")
    fixed_words: list[str] = []

    for word in words:
        upper = word.upper()
        if upper in ROMAN_NUMERALS:
            fixed_words.append(upper)
        else:
            fixed_words.append(word[:1].upper() + word[1:].lower())

    return " ".join(fixed_words)


def parse_positive_float(value: str, field_name: str) -> float:
    """Parse a positive numeric input for UI and tests."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise RecipeError(f"{field_name} must be a number.") from exc

    if parsed <= 0:
        raise RecipeError(f"{field_name} must be greater than 0.")
    return parsed


def parse_non_negative_float(value: str, field_name: str) -> float:
    """Parse a non-negative numeric input for prices."""
    try:
        parsed = float(value)
    except ValueError as exc:
        raise RecipeError(f"{field_name} must be a number.") from exc

    if parsed < 0:
        raise RecipeError(f"{field_name} cannot be negative.")
    return parsed


def fmt(value: float) -> str:
    """Format numbers compactly for the UI."""
    return f"{value:g}"


def normalise_data(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return normalised recipe data with numeric quantities and known price keys."""
    normalised: dict[str, Any] = {"prices": {}, "recipes": {}}

    for item_name, price in data.get("prices", {}).items():
        normalised["prices"][normalise_name(item_name)] = float(price)

    for recipe_name, ingredients in data.get("recipes", {}).items():
        fixed_recipe_name = normalise_name(recipe_name)
        fixed_ingredients: dict[str, float] = {}
        for ingredient_name, qty in ingredients.items():
            fixed_ingredient_name = normalise_name(ingredient_name)
            fixed_ingredients[fixed_ingredient_name] = float(qty)
            normalised["prices"].setdefault(fixed_ingredient_name, 0.0)
        normalised["recipes"][fixed_recipe_name] = fixed_ingredients

    return normalised


def expand_recipe(
    data: Mapping[str, Any],
    item_name: str,
    quantity: float = 1,
    stack: tuple[str, ...] = (),
) -> dict[str, float]:
    """Expand an item into raw base ingredients and quantities."""
    item_name = normalise_name(item_name)

    if item_name in stack:
        chain = " -> ".join((*stack, item_name))
        raise RecipeError(f"Circular recipe detected: {chain}")

    if item_name not in data["recipes"]:
        return {item_name: quantity}

    totals: defaultdict[str, float] = defaultdict(float)
    for ingredient_name, ingredient_amount in data["recipes"][item_name].items():
        expanded = expand_recipe(
            data,
            ingredient_name,
            quantity * float(ingredient_amount),
            (*stack, item_name),
        )
        for base_item, base_amount in expanded.items():
            totals[base_item] += base_amount

    return dict(totals)


def calculate_item_cost(data: Mapping[str, Any], item_name: str, quantity: float = 1) -> float:
    """Calculate an item using only raw base item prices."""
    raw_items = expand_recipe(data, item_name, quantity)
    return sum(float(data["prices"].get(item, 0.0)) * amount for item, amount in raw_items.items())


def build_crafting_tree(
    data: Mapping[str, Any],
    item_name: str,
    quantity: float = 1,
    stack: tuple[str, ...] = (),
) -> CraftNode:
    """Build a nested tree suitable for presenting the expanded recipe."""
    item_name = normalise_name(item_name)

    if item_name in stack:
        chain = " -> ".join((*stack, item_name))
        raise RecipeError(f"Circular recipe detected: {chain}")

    if item_name in data["recipes"]:
        children = [
            build_crafting_tree(
                data,
                ingredient_name,
                quantity * float(ingredient_qty),
                (*stack, item_name),
            )
            for ingredient_name, ingredient_qty in sorted(data["recipes"][item_name].items())
        ]
        return CraftNode(
            item_name=item_name,
            quantity=quantity,
            kind="Recipe",
            unit_cost=None,
            line_cost=sum(child.line_cost for child in children),
            children=children,
        )

    unit_cost = float(data["prices"].get(item_name, 0.0))
    return CraftNode(
        item_name=item_name,
        quantity=quantity,
        kind="Base",
        unit_cost=unit_cost,
        line_cost=quantity * unit_cost,
    )


def calculate(data: Mapping[str, Any], item_name: str, quantity: float = 1) -> CalculationResult:
    """Calculate all views for an item in one call."""
    item_name = normalise_name(item_name)
    raw_totals = expand_recipe(data, item_name, quantity)
    total_cost = sum(float(data["prices"].get(item, 0.0)) * amount for item, amount in raw_totals.items())
    tree = build_crafting_tree(data, item_name, quantity)
    return CalculationResult(item_name, quantity, total_cost, raw_totals, tree)


def validate_recipe(data: Mapping[str, Any], recipe_name: str, ingredients: Mapping[str, float]) -> None:
    """Validate a recipe before saving it into the data store."""
    recipe_name = normalise_name(recipe_name)
    if not recipe_name:
        raise RecipeError("Enter a recipe name.")
    if not ingredients:
        raise RecipeError("Add at least one ingredient.")
    if recipe_name in ingredients:
        raise RecipeError("A recipe cannot directly contain itself.")

    probe = normalise_data(data)
    probe["recipes"][recipe_name] = {normalise_name(name): float(qty) for name, qty in ingredients.items()}
    expand_recipe(probe, recipe_name)
