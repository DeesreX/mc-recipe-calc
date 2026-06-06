"""JSON persistence for recipe-cost data."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .domain import DEFAULT_DATA, normalise_data

DATA_FILE = Path("recipes.json")


class DataStore:
    """Small JSON-backed data store with normalisation on load and save."""

    def __init__(self, path: Path | str = DATA_FILE) -> None:
        self.path = Path(path)

    def load(self) -> dict[str, Any]:
        if self.path.exists():
            with self.path.open("r", encoding="utf-8") as file:
                loaded = json.load(file)
        else:
            loaded = deepcopy(DEFAULT_DATA)

        data = normalise_data(loaded)
        self.save(data)
        return data

    def save(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as file:
            json.dump(normalise_data(data), file, indent=4, sort_keys=True)
            file.write("\n")
