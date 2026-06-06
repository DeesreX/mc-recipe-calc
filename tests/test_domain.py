from __future__ import annotations

import pytest

from recipe_calc.domain import (
    RecipeError,
    calculate,
    expand_recipe,
    normalise_data,
    normalise_name,
    parse_non_negative_float,
    parse_positive_float,
)


def sample_data() -> dict[str, object]:
    return normalise_data(
        {
            "prices": {"wood": 2, "iron ingot": 5, "redstone dust": 3},
            "recipes": {
                "piston": {"wood": 3, "iron ingot": 1, "redstone dust": 1},
                "machine i": {"piston": 2, "wood": 4},
            },
        }
    )


def test_normalise_name_preserves_roman_numerals() -> None:
    assert normalise_name("  solar   PANEL iii ") == "Solar Panel III"


def test_expand_recipe_rolls_up_raw_totals() -> None:
    assert expand_recipe(sample_data(), "Machine I", 2) == {
        "Iron Ingot": 4.0,
        "Redstone Dust": 4.0,
        "Wood": 20.0,
    }


def test_calculate_returns_tree_and_total() -> None:
    result = calculate(sample_data(), "machine i", 1)

    assert result.item_name == "Machine I"
    assert result.total_cost == 36.0
    assert result.tree.kind == "Recipe"
    assert [child.item_name for child in result.tree.children] == ["Piston", "Wood"]


def test_circular_recipe_is_rejected() -> None:
    data = normalise_data({"prices": {}, "recipes": {"A": {"B": 1}, "B": {"A": 1}}})

    with pytest.raises(RecipeError, match="Circular recipe detected: A -> B -> A"):
        expand_recipe(data, "A")


def test_numeric_parsers_report_user_friendly_errors() -> None:
    assert parse_positive_float("2.5", "Quantity") == 2.5
    assert parse_non_negative_float("0", "Price") == 0

    with pytest.raises(RecipeError, match="Quantity must be greater than 0"):
        parse_positive_float("0", "Quantity")

    with pytest.raises(RecipeError, match="Price cannot be negative"):
        parse_non_negative_float("-1", "Price")


def test_filter_items_matches_case_insensitive_substrings() -> None:
    from recipe_calc.app import RecipeCostApp

    assert RecipeCostApp.filter_items(["Iron Ingot", "Redstone Dust", "Wood"], "ing") == ["Iron Ingot"]
    assert RecipeCostApp.filter_items(["Iron Ingot", "Redstone Dust"], "") == ["Iron Ingot", "Redstone Dust"]
