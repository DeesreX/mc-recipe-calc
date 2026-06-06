import json
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from collections import defaultdict
from typing import Any

DATA_FILE = Path("recipes.json")

ROMAN_NUMERALS = {"I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"}

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


def normalise_name(name: str) -> str:
    words = " ".join(name.strip().split()).split(" ")
    fixed_words: list[str] = []

    for word in words:
        upper = word.upper()
        if upper in ROMAN_NUMERALS:
            fixed_words.append(upper)
        else:
            fixed_words.append(word[:1].upper() + word[1:].lower())

    return " ".join(fixed_words)


def normalise_data(data: dict[str, Any]) -> dict[str, Any]:
    normalised: dict[str, Any] = {"prices": {}, "recipes": {}}

    for item_name, price in data.get("prices", {}).items():
        normalised["prices"][normalise_name(item_name)] = float(price)

    for recipe_name, ingredients in data.get("recipes", {}).items():
        fixed_recipe_name = normalise_name(recipe_name)
        fixed_ingredients: dict[str, float] = {}
        for ingredient_name, qty in ingredients.items():
            fixed_ingredients[normalise_name(ingredient_name)] = float(qty)
            normalised["prices"].setdefault(normalise_name(ingredient_name), 0.0)
        normalised["recipes"][fixed_recipe_name] = fixed_ingredients

    return normalised


def load_data() -> dict[str, Any]:
    if DATA_FILE.exists():
        with DATA_FILE.open("r", encoding="utf-8") as file:
            data = json.load(file)
        data.setdefault("recipes", {})
        data.setdefault("prices", {})
        data = normalise_data(data)
        save_data(data)
        return data

    data = normalise_data(DEFAULT_DATA)
    save_data(data)
    return json.loads(json.dumps(data))


def save_data(data: dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, sort_keys=True)


def fmt(value: float) -> str:
    return f"{value:g}"


def expand_recipe(
    data: dict[str, Any],
    item_name: str,
    quantity: float = 1,
    stack: tuple[str, ...] = (),
) -> dict[str, float]:
    item_name = normalise_name(item_name)

    if item_name in stack:
        chain = " -> ".join((*stack, item_name))
        raise ValueError(f"Circular recipe detected: {chain}")

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


def calculate_item_cost(data: dict[str, Any], item_name: str, quantity: float = 1) -> float:
    raw_items = expand_recipe(data, item_name, quantity)
    return sum(float(data["prices"].get(item, 0.0)) * amount for item, amount in raw_items.items())


class RecipeCostApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Recipe Cost Calculator")
        self.geometry("1150x740")
        self.minsize(980, 620)

        self.data = load_data()
        self.selected_recipe: str | None = None

        self._build_ui()
        self.refresh_all()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.recipes_tab = ttk.Frame(notebook)
        self.prices_tab = ttk.Frame(notebook)
        self.calc_tab = ttk.Frame(notebook)

        notebook.add(self.recipes_tab, text="Recipes")
        notebook.add(self.prices_tab, text="Base Prices")
        notebook.add(self.calc_tab, text="Calculator")

        self._build_recipes_tab()
        self._build_prices_tab()
        self._build_calc_tab()

    def _build_recipes_tab(self) -> None:
        root = self.recipes_tab
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(0, weight=1)

        left = ttk.Frame(root)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=8)
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Recipes").grid(row=0, column=0, sticky="w")
        self.recipe_list = tk.Listbox(left, exportselection=False)
        self.recipe_list.grid(row=1, column=0, sticky="nsew", pady=5)
        self.recipe_list.bind("<<ListboxSelect>>", self.on_recipe_select)

        recipe_buttons = ttk.Frame(left)
        recipe_buttons.grid(row=2, column=0, sticky="ew")
        recipe_buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(recipe_buttons, text="New Recipe", command=self.new_recipe).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(recipe_buttons, text="Delete Recipe", command=self.delete_recipe).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        right = ttk.Frame(root)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=8)
        right.columnconfigure(1, weight=1)
        right.rowconfigure(2, weight=1)

        ttk.Label(right, text="Recipe Name").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.recipe_name_var = tk.StringVar()
        ttk.Entry(right, textvariable=self.recipe_name_var).grid(row=0, column=1, sticky="ew")

        add_row = ttk.Frame(right)
        add_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 6))
        add_row.columnconfigure(1, weight=1)
        add_row.columnconfigure(3, weight=1)

        ttk.Label(add_row, text="Ingredient").grid(row=0, column=0, padx=(0, 6))
        self.ingredient_name_var = tk.StringVar()
        ttk.Entry(add_row, textvariable=self.ingredient_name_var).grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(add_row, text="Qty").grid(row=0, column=2, padx=(0, 6))
        self.ingredient_qty_var = tk.StringVar(value="1")
        ttk.Entry(add_row, textvariable=self.ingredient_qty_var, width=12).grid(row=0, column=3, sticky="ew", padx=(0, 10))

        ttk.Button(add_row, text="Add/Update Ingredient", command=self.add_or_update_ingredient).grid(row=0, column=4)

        self.ingredients_tree = ttk.Treeview(right, columns=("item", "qty"), show="headings", selectmode="browse")
        self.ingredients_tree.heading("item", text="Ingredient")
        self.ingredients_tree.heading("qty", text="Quantity")
        self.ingredients_tree.column("item", width=320)
        self.ingredients_tree.column("qty", width=120, anchor="e")
        self.ingredients_tree.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self.ingredients_tree.bind("<<TreeviewSelect>>", self.on_ingredient_select)

        ingredient_buttons = ttk.Frame(right)
        ingredient_buttons.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ingredient_buttons.columnconfigure((0, 1, 2), weight=1)
        ttk.Button(ingredient_buttons, text="Remove Ingredient", command=self.remove_ingredient).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(ingredient_buttons, text="Save Recipe", command=self.save_recipe_from_editor).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(ingredient_buttons, text="Reload Selected", command=self.load_selected_recipe).grid(row=0, column=2, sticky="ew", padx=(4, 0))

    def _build_prices_tab(self) -> None:
        root = self.prices_tab
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        edit = ttk.Frame(root)
        edit.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 6))
        edit.columnconfigure(1, weight=1)
        edit.columnconfigure(3, weight=1)

        ttk.Label(edit, text="Item").grid(row=0, column=0, padx=(0, 6))
        self.price_item_var = tk.StringVar()
        ttk.Entry(edit, textvariable=self.price_item_var).grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(edit, text="Unit Cost").grid(row=0, column=2, padx=(0, 6))
        self.price_value_var = tk.StringVar(value="0")
        ttk.Entry(edit, textvariable=self.price_value_var, width=14).grid(row=0, column=3, sticky="ew", padx=(0, 10))

        ttk.Button(edit, text="Save Price", command=self.save_price).grid(row=0, column=4)

        self.prices_tree = ttk.Treeview(root, columns=("item", "price", "kind"), show="headings", selectmode="browse")
        self.prices_tree.heading("item", text="Item")
        self.prices_tree.heading("price", text="Unit Cost")
        self.prices_tree.heading("kind", text="Type")
        self.prices_tree.column("item", width=360)
        self.prices_tree.column("price", width=120, anchor="e")
        self.prices_tree.column("kind", width=120)
        self.prices_tree.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.prices_tree.bind("<<TreeviewSelect>>", self.on_price_select)

    def _build_calc_tab(self) -> None:
        root = self.calc_tab
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        controls = ttk.Frame(root)
        controls.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Item / Recipe").grid(row=0, column=0, padx=(0, 6))
        self.calc_item_var = tk.StringVar()
        self.calc_item_combo = ttk.Combobox(controls, textvariable=self.calc_item_var)
        self.calc_item_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(controls, text="Qty").grid(row=0, column=2, padx=(0, 6))
        self.calc_qty_var = tk.StringVar(value="1")
        ttk.Entry(controls, textvariable=self.calc_qty_var, width=12).grid(row=0, column=3, padx=(0, 10))

        ttk.Button(controls, text="Calculate", command=self.calculate).grid(row=0, column=4)

        self.total_var = tk.StringVar(value="Total Cost: 0")
        ttk.Label(root, textvariable=self.total_var, font=("Segoe UI", 12, "bold")).grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))

        calc_notebook = ttk.Notebook(root)
        calc_notebook.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))

        tree_tab = ttk.Frame(calc_notebook)
        raw_tab = ttk.Frame(calc_notebook)
        calc_notebook.add(tree_tab, text="Crafting Tree")
        calc_notebook.add(raw_tab, text="Raw Totals")

        tree_tab.columnconfigure(0, weight=1)
        tree_tab.rowconfigure(0, weight=1)
        raw_tab.columnconfigure(0, weight=1)
        raw_tab.rowconfigure(0, weight=1)

        self.crafting_tree = ttk.Treeview(
            tree_tab,
            columns=("qty", "kind", "unit", "line"),
            show="tree headings",
        )
        self.crafting_tree.heading("#0", text="Item")
        self.crafting_tree.heading("qty", text="Required Qty")
        self.crafting_tree.heading("kind", text="Type")
        self.crafting_tree.heading("unit", text="Unit Cost")
        self.crafting_tree.heading("line", text="Total Cost")
        self.crafting_tree.column("#0", width=430)
        self.crafting_tree.column("qty", width=120, anchor="e")
        self.crafting_tree.column("kind", width=110)
        self.crafting_tree.column("unit", width=120, anchor="e")
        self.crafting_tree.column("line", width=120, anchor="e")
        self.crafting_tree.grid(row=0, column=0, sticky="nsew")

        tree_scroll = ttk.Scrollbar(tree_tab, orient="vertical", command=self.crafting_tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.crafting_tree.configure(yscrollcommand=tree_scroll.set)

        self.raw_totals_tree = ttk.Treeview(raw_tab, columns=("item", "qty", "unit", "line"), show="headings")
        self.raw_totals_tree.heading("item", text="Raw Item")
        self.raw_totals_tree.heading("qty", text="Quantity")
        self.raw_totals_tree.heading("unit", text="Unit Cost")
        self.raw_totals_tree.heading("line", text="Line Cost")
        self.raw_totals_tree.column("item", width=430)
        self.raw_totals_tree.column("qty", width=120, anchor="e")
        self.raw_totals_tree.column("unit", width=120, anchor="e")
        self.raw_totals_tree.column("line", width=120, anchor="e")
        self.raw_totals_tree.grid(row=0, column=0, sticky="nsew")

        raw_scroll = ttk.Scrollbar(raw_tab, orient="vertical", command=self.raw_totals_tree.yview)
        raw_scroll.grid(row=0, column=1, sticky="ns")
        self.raw_totals_tree.configure(yscrollcommand=raw_scroll.set)

    def refresh_all(self) -> None:
        self.refresh_recipe_list()
        self.refresh_prices()
        self.refresh_calc_items()

    def refresh_recipe_list(self) -> None:
        self.recipe_list.delete(0, tk.END)
        for recipe_name in sorted(self.data["recipes"]):
            self.recipe_list.insert(tk.END, recipe_name)

    def refresh_prices(self) -> None:
        for row in self.prices_tree.get_children():
            self.prices_tree.delete(row)

        all_items = set(self.data["prices"]) | set(self.data["recipes"])
        for item_name in sorted(all_items):
            price = float(self.data["prices"].get(item_name, 0.0))
            kind = "Recipe" if item_name in self.data["recipes"] else "Base Item"
            self.prices_tree.insert("", tk.END, values=(item_name, fmt(price), kind))

    def refresh_calc_items(self) -> None:
        all_items = sorted(set(self.data["recipes"]) | set(self.data["prices"]))
        self.calc_item_combo["values"] = all_items
        if not self.calc_item_var.get() and all_items:
            preferred = "Solar Panel III" if "Solar Panel III" in all_items else all_items[0]
            self.calc_item_var.set(preferred)

    def on_recipe_select(self, _event: tk.Event | None = None) -> None:
        selection = self.recipe_list.curselection()
        if not selection:
            return
        self.selected_recipe = self.recipe_list.get(selection[0])
        self.load_selected_recipe()

    def load_selected_recipe(self) -> None:
        if not self.selected_recipe or self.selected_recipe not in self.data["recipes"]:
            return

        self.recipe_name_var.set(self.selected_recipe)
        self.clear_ingredient_inputs()
        self.load_ingredients_into_editor(self.data["recipes"][self.selected_recipe])

    def load_ingredients_into_editor(self, ingredients: dict[str, float]) -> None:
        for row in self.ingredients_tree.get_children():
            self.ingredients_tree.delete(row)
        for item_name, qty in sorted(ingredients.items()):
            self.ingredients_tree.insert("", tk.END, values=(item_name, fmt(float(qty))))

    def new_recipe(self) -> None:
        self.selected_recipe = None
        self.recipe_name_var.set("")
        self.clear_ingredient_inputs()
        self.load_ingredients_into_editor({})

    def delete_recipe(self) -> None:
        recipe_name = self.recipe_name_var.get().strip() or self.selected_recipe
        if not recipe_name:
            messagebox.showwarning("No recipe selected", "Select a recipe first.")
            return

        recipe_name = normalise_name(recipe_name)
        if recipe_name not in self.data["recipes"]:
            messagebox.showwarning("Not found", "That recipe does not exist.")
            return

        if not messagebox.askyesno("Delete recipe", f"Delete '{recipe_name}'?"):
            return

        del self.data["recipes"][recipe_name]
        save_data(self.data)
        self.selected_recipe = None
        self.new_recipe()
        self.refresh_all()

    def on_ingredient_select(self, _event: tk.Event | None = None) -> None:
        selected = self.ingredients_tree.selection()
        if not selected:
            return
        item_name, qty = self.ingredients_tree.item(selected[0], "values")
        self.ingredient_name_var.set(item_name)
        self.ingredient_qty_var.set(qty)

    def add_or_update_ingredient(self) -> None:
        item_name = normalise_name(self.ingredient_name_var.get())
        if not item_name:
            messagebox.showwarning("Missing ingredient", "Enter an ingredient name.")
            return

        try:
            qty = float(self.ingredient_qty_var.get())
        except ValueError:
            messagebox.showerror("Invalid quantity", "Quantity must be a number.")
            return

        if qty <= 0:
            messagebox.showerror("Invalid quantity", "Quantity must be greater than 0.")
            return

        existing_row = None
        for row in self.ingredients_tree.get_children():
            values = self.ingredients_tree.item(row, "values")
            if values and values[0] == item_name:
                existing_row = row
                break

        if existing_row:
            self.ingredients_tree.item(existing_row, values=(item_name, fmt(qty)))
        else:
            self.ingredients_tree.insert("", tk.END, values=(item_name, fmt(qty)))

        self.clear_ingredient_inputs()

    def remove_ingredient(self) -> None:
        selected = self.ingredients_tree.selection()
        if not selected:
            messagebox.showwarning("No ingredient selected", "Select an ingredient first.")
            return
        self.ingredients_tree.delete(selected[0])
        self.clear_ingredient_inputs()

    def clear_ingredient_inputs(self) -> None:
        self.ingredient_name_var.set("")
        self.ingredient_qty_var.set("1")

    def get_editor_ingredients(self) -> dict[str, float]:
        ingredients: dict[str, float] = {}
        for row in self.ingredients_tree.get_children():
            item_name, qty = self.ingredients_tree.item(row, "values")
            ingredients[item_name] = float(qty)
        return ingredients

    def save_recipe_from_editor(self) -> None:
        recipe_name = normalise_name(self.recipe_name_var.get())
        if not recipe_name:
            messagebox.showwarning("Missing name", "Enter a recipe name.")
            return

        ingredients = self.get_editor_ingredients()
        if not ingredients:
            messagebox.showwarning("Missing ingredients", "Add at least one ingredient.")
            return

        if recipe_name in ingredients:
            messagebox.showerror("Invalid recipe", "A recipe cannot directly contain itself.")
            return

        old_name = self.selected_recipe
        old_recipe = self.data["recipes"].get(old_name, {}).copy() if old_name else None

        if old_name and old_name != recipe_name and old_name in self.data["recipes"]:
            del self.data["recipes"][old_name]

        self.data["recipes"][recipe_name] = ingredients
        for item_name in ingredients:
            self.data["prices"].setdefault(item_name, 0.0)

        try:
            expand_recipe(self.data, recipe_name)
        except ValueError as error:
            self.data["recipes"].pop(recipe_name, None)
            if old_name and old_recipe:
                self.data["recipes"][old_name] = old_recipe
            messagebox.showerror("Circular recipe", str(error))
            return

        save_data(self.data)
        self.selected_recipe = recipe_name
        self.refresh_all()
        self.select_recipe_in_list(recipe_name)
        messagebox.showinfo("Saved", f"Saved recipe: {recipe_name}")

    def select_recipe_in_list(self, recipe_name: str) -> None:
        self.recipe_list.selection_clear(0, tk.END)
        for i in range(self.recipe_list.size()):
            if self.recipe_list.get(i) == recipe_name:
                self.recipe_list.selection_set(i)
                self.recipe_list.see(i)
                break

    def on_price_select(self, _event: tk.Event | None = None) -> None:
        selected = self.prices_tree.selection()
        if not selected:
            return
        item_name, price, _kind = self.prices_tree.item(selected[0], "values")
        self.price_item_var.set(item_name)
        self.price_value_var.set(price)

    def save_price(self) -> None:
        item_name = normalise_name(self.price_item_var.get())
        if not item_name:
            messagebox.showwarning("Missing item", "Enter an item name.")
            return

        try:
            price = float(self.price_value_var.get())
        except ValueError:
            messagebox.showerror("Invalid price", "Price must be a number.")
            return

        if price < 0:
            messagebox.showerror("Invalid price", "Price cannot be negative.")
            return

        self.data["prices"][item_name] = price
        save_data(self.data)
        self.refresh_all()

    def clear_calculator_results(self) -> None:
        for row in self.crafting_tree.get_children():
            self.crafting_tree.delete(row)
        for row in self.raw_totals_tree.get_children():
            self.raw_totals_tree.delete(row)

    def insert_crafting_node(
        self,
        parent_id: str,
        item_name: str,
        quantity: float,
        stack: tuple[str, ...] = (),
    ) -> float:
        item_name = normalise_name(item_name)

        if item_name in stack:
            chain = " -> ".join((*stack, item_name))
            raise ValueError(f"Circular recipe detected: {chain}")

        is_recipe = item_name in self.data["recipes"]
        kind = "Recipe" if is_recipe else "Base"

        if is_recipe:
            line_cost = calculate_item_cost(self.data, item_name, quantity)
            node_id = self.crafting_tree.insert(
                parent_id,
                tk.END,
                text=item_name,
                values=(fmt(quantity), kind, "-", fmt(line_cost)),
                open=True,
            )
            for ingredient_name, ingredient_qty in sorted(self.data["recipes"][item_name].items()):
                self.insert_crafting_node(
                    node_id,
                    ingredient_name,
                    quantity * float(ingredient_qty),
                    (*stack, item_name),
                )
            return line_cost

        unit_cost = float(self.data["prices"].get(item_name, 0.0))
        line_cost = quantity * unit_cost
        self.crafting_tree.insert(
            parent_id,
            tk.END,
            text=item_name,
            values=(fmt(quantity), kind, fmt(unit_cost), fmt(line_cost)),
            open=True,
        )
        return line_cost

    def calculate(self) -> None:
        item_name = normalise_name(self.calc_item_var.get())
        if not item_name:
            messagebox.showwarning("Missing item", "Choose or enter an item.")
            return

        try:
            qty = float(self.calc_qty_var.get() or "1")
        except ValueError:
            messagebox.showerror("Invalid quantity", "Quantity must be a number.")
            return

        if qty <= 0:
            messagebox.showerror("Invalid quantity", "Quantity must be greater than 0.")
            return

        try:
            raw_items = expand_recipe(self.data, item_name, qty)
        except ValueError as error:
            messagebox.showerror("Cannot calculate", str(error))
            return

        self.clear_calculator_results()

        try:
            total = self.insert_crafting_node("", item_name, qty)
        except ValueError as error:
            messagebox.showerror("Cannot calculate", str(error))
            return

        raw_total = 0.0
        for raw_item, amount in sorted(raw_items.items()):
            unit_cost = float(self.data["prices"].get(raw_item, 0.0))
            line_cost = amount * unit_cost
            raw_total += line_cost
            self.raw_totals_tree.insert(
                "",
                tk.END,
                values=(raw_item, fmt(amount), fmt(unit_cost), fmt(line_cost)),
            )

        # total and raw_total should match. raw_total is the hard cost source.
        self.total_var.set(f"Total Cost: {fmt(raw_total)}")


if __name__ == "__main__":
    app = RecipeCostApp()
    app.mainloop()
