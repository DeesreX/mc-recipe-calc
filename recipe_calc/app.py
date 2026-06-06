"""Tkinter user interface for the recipe cost calculator."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from .domain import (
    CraftNode,
    RecipeError,
    calculate,
    fmt,
    normalise_name,
    parse_non_negative_float,
    parse_positive_float,
    validate_recipe,
)
from .storage import DataStore


class RecipeCostApp(tk.Tk):
    """Desktop app for editing recipes, prices, and cost calculations."""

    def __init__(self, store: DataStore | None = None) -> None:
        super().__init__()
        self.title("Minecraft Recipe Cost Calculator")
        self.geometry("1180x760")
        self.minsize(980, 640)

        self.store = store or DataStore()
        self.data = self.store.load()
        self.selected_recipe: str | None = None

        self._configure_style()
        self._build_ui()
        self.refresh_all()
        self.set_status(f"Loaded {self.store.path.resolve()}")

    def _configure_style(self) -> None:
        self.style = ttk.Style(self)
        self.style.configure("Title.TLabel", font=("Segoe UI", 14, "bold"))
        self.style.configure("Total.TLabel", font=("Segoe UI", 12, "bold"))
        self.style.configure("Hint.TLabel", foreground="#555")

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self, padding=(12, 10, 12, 0))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Minecraft Recipe Cost Calculator", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Edit recipes and base item prices, then inspect full crafting costs.",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        ttk.Button(header, text="Reload Data", command=self.reload_data).grid(row=0, column=1, rowspan=2, sticky="e")

        notebook = ttk.Notebook(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        self.recipes_tab = ttk.Frame(notebook, padding=8)
        self.prices_tab = ttk.Frame(notebook, padding=8)
        self.calc_tab = ttk.Frame(notebook, padding=8)

        notebook.add(self.recipes_tab, text="Recipes")
        notebook.add(self.prices_tab, text="Base Prices")
        notebook.add(self.calc_tab, text="Calculator")

        self._build_recipes_tab()
        self._build_prices_tab()
        self._build_calc_tab()

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, relief="sunken", anchor="w", padding=(8, 3)).grid(
            row=2, column=0, sticky="ew"
        )

    def _build_recipes_tab(self) -> None:
        root = self.recipes_tab
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=2)
        root.rowconfigure(0, weight=1)

        left = ttk.Labelframe(root, text="Recipe Library", padding=8)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        self.recipe_filter_var = tk.StringVar()
        self.recipe_filter_var.trace_add("write", lambda *_args: self.refresh_recipe_list())
        ttk.Entry(left, textvariable=self.recipe_filter_var).grid(row=0, column=0, sticky="ew", pady=(0, 6))

        self.recipe_list = tk.Listbox(left, exportselection=False, activestyle="dotbox")
        self.recipe_list.grid(row=1, column=0, sticky="nsew")
        self.recipe_list.bind("<<ListboxSelect>>", self.on_recipe_select)

        recipe_buttons = ttk.Frame(left)
        recipe_buttons.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        recipe_buttons.columnconfigure((0, 1), weight=1)
        ttk.Button(recipe_buttons, text="New Recipe", command=self.new_recipe).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ttk.Button(recipe_buttons, text="Delete Recipe", command=self.delete_recipe).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        right = ttk.Labelframe(root, text="Recipe Editor", padding=8)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
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
        self.ingredient_combo = ttk.Combobox(add_row, textvariable=self.ingredient_name_var)
        self.ingredient_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(add_row, text="Qty").grid(row=0, column=2, padx=(0, 6))
        self.ingredient_qty_var = tk.StringVar(value="1")
        ttk.Entry(add_row, textvariable=self.ingredient_qty_var, width=12).grid(row=0, column=3, sticky="ew", padx=(0, 10))

        ttk.Button(add_row, text="Add / Update", command=self.add_or_update_ingredient).grid(row=0, column=4)

        self.ingredients_tree = ttk.Treeview(right, columns=("item", "qty"), show="headings", selectmode="browse")
        self.ingredients_tree.heading("item", text="Ingredient")
        self.ingredients_tree.heading("qty", text="Quantity")
        self.ingredients_tree.column("item", width=360)
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

        edit = ttk.Labelframe(root, text="Price Editor", padding=8)
        edit.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        edit.columnconfigure(1, weight=1)
        edit.columnconfigure(3, weight=1)

        ttk.Label(edit, text="Item").grid(row=0, column=0, padx=(0, 6))
        self.price_item_var = tk.StringVar()
        self.price_item_combo = ttk.Combobox(edit, textvariable=self.price_item_var)
        self.price_item_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(edit, text="Unit Cost").grid(row=0, column=2, padx=(0, 6))
        self.price_value_var = tk.StringVar(value="0")
        ttk.Entry(edit, textvariable=self.price_value_var, width=14).grid(row=0, column=3, sticky="ew", padx=(0, 10))

        ttk.Button(edit, text="Save Price", command=self.save_price).grid(row=0, column=4)

        self.prices_tree = ttk.Treeview(root, columns=("item", "price", "kind"), show="headings", selectmode="browse")
        self.prices_tree.heading("item", text="Item")
        self.prices_tree.heading("price", text="Unit Cost")
        self.prices_tree.heading("kind", text="Type")
        self.prices_tree.column("item", width=420)
        self.prices_tree.column("price", width=120, anchor="e")
        self.prices_tree.column("kind", width=120)
        self.prices_tree.grid(row=1, column=0, sticky="nsew")
        self.prices_tree.bind("<<TreeviewSelect>>", self.on_price_select)

    def _build_calc_tab(self) -> None:
        root = self.calc_tab
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        controls = ttk.Labelframe(root, text="Calculate Cost", padding=8)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Item / Recipe").grid(row=0, column=0, padx=(0, 6))
        self.calc_item_var = tk.StringVar()
        self.calc_item_combo = ttk.Combobox(controls, textvariable=self.calc_item_var)
        self.calc_item_combo.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        ttk.Label(controls, text="Qty").grid(row=0, column=2, padx=(0, 6))
        self.calc_qty_var = tk.StringVar(value="1")
        ttk.Entry(controls, textvariable=self.calc_qty_var, width=12).grid(row=0, column=3, padx=(0, 10))

        ttk.Button(controls, text="Calculate", command=self.calculate_current_item).grid(row=0, column=4)

        self.total_var = tk.StringVar(value="Total Cost: 0")
        ttk.Label(root, textvariable=self.total_var, style="Total.TLabel").grid(row=1, column=0, sticky="w", pady=(0, 6))

        calc_notebook = ttk.Notebook(root)
        calc_notebook.grid(row=2, column=0, sticky="nsew")

        tree_tab = ttk.Frame(calc_notebook, padding=4)
        raw_tab = ttk.Frame(calc_notebook, padding=4)
        calc_notebook.add(tree_tab, text="Crafting Tree")
        calc_notebook.add(raw_tab, text="Raw Totals")

        tree_tab.columnconfigure(0, weight=1)
        tree_tab.rowconfigure(0, weight=1)
        raw_tab.columnconfigure(0, weight=1)
        raw_tab.rowconfigure(0, weight=1)

        self.crafting_tree = ttk.Treeview(tree_tab, columns=("qty", "kind", "unit", "line"), show="tree headings")
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

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def save_data(self) -> None:
        self.store.save(self.data)
        self.set_status(f"Saved {Path(self.store.path).resolve()}")

    def reload_data(self) -> None:
        self.data = self.store.load()
        self.selected_recipe = None
        self.new_recipe()
        self.refresh_all()
        self.set_status("Reloaded data from disk.")

    def refresh_all(self) -> None:
        self.refresh_recipe_list()
        self.refresh_prices()
        self.refresh_item_combos()

    def refresh_recipe_list(self) -> None:
        current = self.selected_recipe
        self.recipe_list.delete(0, tk.END)
        filter_text = self.recipe_filter_var.get().casefold() if hasattr(self, "recipe_filter_var") else ""
        for recipe_name in sorted(self.data["recipes"]):
            if filter_text and filter_text not in recipe_name.casefold():
                continue
            self.recipe_list.insert(tk.END, recipe_name)
        if current:
            self.select_recipe_in_list(current)

    def refresh_prices(self) -> None:
        for row in self.prices_tree.get_children():
            self.prices_tree.delete(row)

        for item_name in self.all_items():
            price = float(self.data["prices"].get(item_name, 0.0))
            kind = "Recipe" if item_name in self.data["recipes"] else "Base Item"
            self.prices_tree.insert("", tk.END, values=(item_name, fmt(price), kind))

    def refresh_item_combos(self) -> None:
        all_items = self.all_items()
        self.calc_item_combo["values"] = all_items
        self.ingredient_combo["values"] = all_items
        self.price_item_combo["values"] = all_items
        if not self.calc_item_var.get() and all_items:
            preferred = "Solar Panel III" if "Solar Panel III" in all_items else all_items[0]
            self.calc_item_var.set(preferred)

    def all_items(self) -> list[str]:
        return sorted(set(self.data["recipes"]) | set(self.data["prices"]))

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
        self.set_status(f"Editing recipe: {self.selected_recipe}")

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
        self.set_status("Ready for a new recipe.")

    def delete_recipe(self) -> None:
        recipe_name = normalise_name(self.recipe_name_var.get().strip() or self.selected_recipe or "")
        if not recipe_name:
            messagebox.showwarning("No recipe selected", "Select a recipe first.")
            return
        if recipe_name not in self.data["recipes"]:
            messagebox.showwarning("Not found", "That recipe does not exist.")
            return
        if not messagebox.askyesno("Delete recipe", f"Delete '{recipe_name}'?"):
            return
        del self.data["recipes"][recipe_name]
        self.save_data()
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
            qty = parse_positive_float(self.ingredient_qty_var.get(), "Quantity")
        except RecipeError as error:
            messagebox.showerror("Invalid quantity", str(error))
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
        self.set_status(f"Staged ingredient: {item_name}")

    def remove_ingredient(self) -> None:
        selected = self.ingredients_tree.selection()
        if not selected:
            messagebox.showwarning("No ingredient selected", "Select an ingredient first.")
            return
        self.ingredients_tree.delete(selected[0])
        self.clear_ingredient_inputs()
        self.set_status("Removed ingredient from editor.")

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
        ingredients = self.get_editor_ingredients()
        old_name = self.selected_recipe
        old_recipe = self.data["recipes"].get(old_name, {}).copy() if old_name else None

        if old_name and old_name != recipe_name and old_name in self.data["recipes"]:
            del self.data["recipes"][old_name]
        self.data["recipes"][recipe_name] = ingredients
        for item_name in ingredients:
            self.data["prices"].setdefault(item_name, 0.0)

        try:
            validate_recipe(self.data, recipe_name, ingredients)
        except RecipeError as error:
            self.data["recipes"].pop(recipe_name, None)
            if old_name and old_recipe:
                self.data["recipes"][old_name] = old_recipe
            messagebox.showerror("Invalid recipe", str(error))
            return

        self.save_data()
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
            price = parse_non_negative_float(self.price_value_var.get(), "Price")
        except RecipeError as error:
            messagebox.showerror("Invalid price", str(error))
            return

        self.data["prices"][item_name] = price
        self.save_data()
        self.refresh_all()
        self.set_status(f"Saved price for {item_name}.")

    def clear_calculator_results(self) -> None:
        for row in self.crafting_tree.get_children():
            self.crafting_tree.delete(row)
        for row in self.raw_totals_tree.get_children():
            self.raw_totals_tree.delete(row)

    def insert_crafting_node(self, parent_id: str, node: CraftNode) -> None:
        node_id = self.crafting_tree.insert(
            parent_id,
            tk.END,
            text=node.item_name,
            values=(
                fmt(node.quantity),
                node.kind,
                "-" if node.unit_cost is None else fmt(node.unit_cost),
                fmt(node.line_cost),
            ),
            open=True,
        )
        for child in node.children:
            self.insert_crafting_node(node_id, child)

    def calculate_current_item(self) -> None:
        item_name = normalise_name(self.calc_item_var.get())
        if not item_name:
            messagebox.showwarning("Missing item", "Choose or enter an item.")
            return
        try:
            qty = parse_positive_float(self.calc_qty_var.get() or "1", "Quantity")
            result = calculate(self.data, item_name, qty)
        except RecipeError as error:
            messagebox.showerror("Cannot calculate", str(error))
            return

        self.clear_calculator_results()
        self.insert_crafting_node("", result.tree)

        for raw_item, amount in sorted(result.raw_totals.items()):
            unit_cost = float(self.data["prices"].get(raw_item, 0.0))
            line_cost = amount * unit_cost
            self.raw_totals_tree.insert("", tk.END, values=(raw_item, fmt(amount), fmt(unit_cost), fmt(line_cost)))

        self.total_var.set(f"Total Cost: {fmt(result.total_cost)}")
        self.set_status(f"Calculated {fmt(qty)} × {result.item_name}.")


def main() -> None:
    app = RecipeCostApp()
    app.mainloop()
