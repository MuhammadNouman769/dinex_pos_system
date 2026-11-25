"""
Inventory business logic.

Key ideas
- Quantities are stored in base units (g / ml / pcs).
- A menu item (variant) has a Recipe; a recipe line may point at a *prepared*
  ingredient that has its own recipe (e.g. patty). Selling explodes the whole
  tree down to raw ingredients.
- Stock for an order is kept in sync by *delta*: we compare what the order needs
  now with what the ledger says was already deducted, and move only the
  difference. This one rule handles confirm, adding/removing items later and
  cancelling.
"""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from rest_framework.exceptions import APIException

from apps.inventory.models import (
    Ingredient, IngredientStock, StockMovement, MovementType, BaseUnit,
)

MAX_RECIPE_DEPTH = 6

# entered unit -> (base unit, factor to base)
UNIT_TABLE = {
    "g": (BaseUnit.GRAM, Decimal("1")),
    "kg": (BaseUnit.GRAM, Decimal("1000")),
    "mg": (BaseUnit.GRAM, Decimal("0.001")),
    "ml": (BaseUnit.MILLILITRE, Decimal("1")),
    "l": (BaseUnit.MILLILITRE, Decimal("1000")),
    "pcs": (BaseUnit.PIECE, Decimal("1")),
    "dozen": (BaseUnit.PIECE, Decimal("12")),
}


class InsufficientStock(APIException, ValueError):
    """Raised when a location's policy is BLOCK and stock is not enough.
    Is an API error (HTTP 400) and also a ValueError, so existing
    `except ValueError` handlers report it as a normal 400 too."""
    status_code = 400
    default_code = "insufficient_stock"


def unit_factor(unit, ingredient):
    """Factor converting `unit` into the ingredient's base unit."""
    unit = (unit or "").strip().lower() or ingredient.base_unit.lower()
    if unit not in UNIT_TABLE:
        raise ValueError(f"Unknown unit '{unit}'. Use one of: {', '.join(UNIT_TABLE)}.")
    base, factor = UNIT_TABLE[unit]
    if base != ingredient.base_unit:
        raise ValueError(
            f"'{unit}' cannot be used for {ingredient.name} (it is measured in {ingredient.base_unit})."
        )
    return factor


def to_base_quantity(quantity, unit, ingredient):
    return Decimal(str(quantity)) * unit_factor(unit, ingredient)


# ───────────────────────── recipes ─────────────────────────
def _recipe_of(obj):
    try:
        recipe = obj.recipe
    except Exception:  # RelatedObjectDoesNotExist
        return None
    return None if recipe.is_deleted else recipe


def explode_recipe(recipe, multiplier, totals=None, depth=0):
    """
    Add the RAW ingredients needed for `multiplier` x one recipe-output into
    `totals` ({ingredient_id: base quantity}). Prepared ingredients are expanded
    through their own recipe.
    """
    if totals is None:
        totals = defaultdict(Decimal)
    if depth > MAX_RECIPE_DEPTH:
        raise ValueError("Recipe is nested too deeply or refers to itself.")
    for line in recipe.lines.select_related("ingredient"):
        need = line.quantity * multiplier
        ingredient = line.ingredient
        sub = _recipe_of(ingredient) if ingredient.is_prepared else None
        if sub is not None:
            explode_recipe(sub, need / sub.output_quantity, totals, depth + 1)
        else:
            totals[ingredient.id] += need
    return totals


def recipe_cost_per_output(recipe):
    """Cost of one serving (variant) or one base unit (prepared ingredient)."""
    totals = explode_recipe(recipe, Decimal("1") / recipe.output_quantity)
    costs = Ingredient.objects.in_bulk(list(totals))
    return sum((qty * costs[i].cost_per_unit for i, qty in totals.items()), Decimal("0"))


def would_create_cycle(prepared_ingredient, new_line_ingredient_ids):
    """True if adding these lines to prepared_ingredient's recipe makes it depend on itself."""
    seen = set()
    stack = list(new_line_ingredient_ids)
    while stack:
        ing_id = stack.pop()
        if ing_id == prepared_ingredient.id:
            return True
        if ing_id in seen:
            continue
        seen.add(ing_id)
        ing = Ingredient.objects.filter(pk=ing_id).first()
        sub = _recipe_of(ing) if ing and ing.is_prepared else None
        if sub:
            stack.extend(sub.lines.values_list("ingredient_id", flat=True))
    return False


# ───────────────────────── ledger ─────────────────────────
@transaction.atomic
def record_movement(location, ingredient, change, movement_type, user=None, note="",
                    reference=None, unit_cost=None):
    """Change stock and write the ledger row in one step. Returns the movement."""
    stock, _ = IngredientStock.objects.get_or_create(ingredient=ingredient, location=location)
    stock = IngredientStock.objects.select_for_update().get(pk=stock.pk)
    stock.quantity = stock.quantity + Decimal(change)
    stock.save(update_fields=["quantity", "updated_at"])
    return StockMovement.objects.create(
        location=location,
        ingredient=ingredient,
        movement_type=movement_type,
        quantity_change=Decimal(change),
        balance_after=stock.quantity,
        unit_cost=unit_cost,
        reference_type=reference[0] if reference else "",
        reference_id=reference[1] if reference else None,
        note=note[:255],
        created_by=user if getattr(user, "is_authenticated", False) else None,
    )


@transaction.atomic
def purchase(location, ingredient, base_quantity, cost_per_base_unit=None, user=None, note=""):
    """Receive stock; keeps ingredient.cost_per_unit as a weighted average."""
    if cost_per_base_unit is not None:
        on_hand = sum(
            (max(q, Decimal("0")) for q in
             IngredientStock.objects.filter(ingredient=ingredient).values_list("quantity", flat=True)),
            Decimal("0"),
        )
        total = on_hand + base_quantity
        ingredient.cost_per_unit = (
            (on_hand * ingredient.cost_per_unit + base_quantity * cost_per_base_unit) / total
            if on_hand > 0 else cost_per_base_unit
        )
        ingredient.save(update_fields=["cost_per_unit", "updated_at"])
    return record_movement(location, ingredient, base_quantity, MovementType.PURCHASE,
                           user=user, note=note, unit_cost=cost_per_base_unit)


# ───────────────────── orders ↔ stock ─────────────────────
def _needed_for_order(order):
    totals = defaultdict(Decimal)
    for item in order.items.filter(is_deleted=False).select_related("product_variant"):
        variant = item.product_variant
        recipe = _recipe_of(variant) if variant else None
        if recipe is not None:
            explode_recipe(recipe, Decimal(item.quantity) / recipe.output_quantity, totals)
    return totals


def _already_deducted(order):
    done = defaultdict(Decimal)
    rows = StockMovement.objects.filter(
        reference_type="order", reference_id=order.pk,
        movement_type__in=[MovementType.SALE, MovementType.SALE_REVERSAL],
    ).values_list("ingredient_id", "quantity_change")
    for ingredient_id, change in rows:
        done[ingredient_id] -= change  # sales are negative changes -> positive "deducted"
    return done


@transaction.atomic
def sync_stock_for_order(order, release_all=False, user=None):
    """
    Make the ledger match what the order needs (or release everything).
    Returns a list of warning strings (policy WARN).
    """
    needed = {} if release_all else _needed_for_order(order)
    deducted = _already_deducted(order)
    location = order.location

    deltas = {i: needed.get(i, Decimal("0")) - deducted.get(i, Decimal("0"))
              for i in set(needed) | set(deducted)}
    deltas = {i: d for i, d in deltas.items() if d != 0}
    ingredients = Ingredient.objects.in_bulk(list(deltas))
    ref = ("order", order.pk)

    shortages = []
    for ing_id, delta in deltas.items():
        if delta > 0:
            row = IngredientStock.objects.filter(ingredient_id=ing_id, location=location).first()
            have = row.quantity if row else Decimal("0")
            if have < delta:
                shortages.append(
                    f"{ingredients[ing_id].name}: need {delta:g} "
                    f"{ingredients[ing_id].base_unit}, have {have:g}"
                )

    policy = location.inventory_policy
    if shortages and policy == "BLOCK":
        raise InsufficientStock("Not enough stock - " + "; ".join(shortages))

    for ing_id, delta in deltas.items():
        record_movement(
            location, ingredients[ing_id], -delta,
            MovementType.SALE if delta > 0 else MovementType.SALE_REVERSAL,
            user=user, note=f"Order {order.order_number}", reference=ref,
        )

    order.stock_deducted = not release_all
    type(order).objects.filter(pk=order.pk).update(stock_deducted=order.stock_deducted)
    return shortages if policy == "WARN" else []
