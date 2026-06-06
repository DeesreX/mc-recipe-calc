# Minecraft Recipe Cost Calculator

A small Tkinter desktop app for calculating the raw material cost of Minecraft-style crafting chains.

## Features

- Edit recipes and nested ingredients in a dedicated recipe library.
- Track base item prices separately from craftable recipes.
- Calculate any item quantity and inspect both:
  - a nested crafting tree, and
  - raw material totals with line costs.
- Detect circular recipes before saving or calculating.
- Store data in a readable `recipes.json` file.

## Run the app

```bash
python -m recipe_calc
```

The original launcher still works too:

```bash
python recipe_cost_gui_tree.py
```

## Development

Install test dependencies if needed:

```bash
python -m pip install -e '.[dev]'
```

Run tests:

```bash
python -m pytest
```

## Data format

`recipes.json` contains two top-level objects:

- `prices`: item name to unit cost.
- `recipes`: recipe name to ingredient quantities.

Item names are normalised on load and save so entries such as `solar panel iii` become `Solar Panel III`.
