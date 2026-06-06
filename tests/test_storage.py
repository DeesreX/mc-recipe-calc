from __future__ import annotations

import json

from recipe_calc.storage import DataStore


def test_data_store_loads_normalised_data(tmp_path) -> None:
    data_file = tmp_path / "recipes.json"
    data_file.write_text(
        json.dumps({"prices": {"iron ingot": "2"}, "recipes": {"gear i": {"iron ingot": "4"}}}),
        encoding="utf-8",
    )

    data = DataStore(data_file).load()

    assert data == {"prices": {"Iron Ingot": 2.0}, "recipes": {"Gear I": {"Iron Ingot": 4.0}}}
    assert json.loads(data_file.read_text(encoding="utf-8")) == data
