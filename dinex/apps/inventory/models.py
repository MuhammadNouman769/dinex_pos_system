from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.utils.models import BaseModel


class BaseUnit(models.TextChoices):
    GRAM = "G", "Gram"
    MILLILITRE = "ML", "Millilitre"
    PIECE = "PCS", "Piece"


class Ingredient(BaseModel):
    """
    Anything the kitchen uses: chicken, bun, cheese slice, oil, sauce...

    All quantities are stored in the ingredient's BASE unit (g / ml / pcs).
    People can enter kg, l, dozen... – those are converted on the way in
    (see services.to_base_quantity).

    `is_prepared=True` marks an in-house preparation (e.g. "Chicken patty")
    that has its own recipe. Selling a burger then deducts the patty's raw
    ingredients, not a "patty" stock row.
    """
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="ingredients"
    )
    name = models.CharField(max_length=150)
    sku = models.CharField(max_length=50, blank=True)
    base_unit = models.CharField(max_length=3, choices=BaseUnit.choices, default=BaseUnit.PIECE)
    cost_per_unit = models.DecimalField(
        max_digits=12, decimal_places=4, default=0,
        help_text="Cost per ONE base unit (per g / ml / piece). Updated by purchases (weighted average).",
    )
    reorder_level = models.DecimalField(
        max_digits=14, decimal_places=3, default=0,
        help_text="Warn when stock at a location falls to or below this (base units).",
    )
    is_prepared = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"],
                condition=Q(is_deleted=False),
                name="unique_ingredient_name_per_organization",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.base_unit})"


class IngredientStock(models.Model):
    """Current stock of one ingredient at one location (base units)."""
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="stocks")
    location = models.ForeignKey(
        "organizations.Location", on_delete=models.CASCADE, related_name="ingredient_stocks"
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["ingredient", "location"], name="unique_stock_per_ingredient_location"),
        ]


class MovementType(models.TextChoices):
    OPENING = "OPENING", "Opening stock"
    PURCHASE = "PURCHASE", "Purchase"
    SALE = "SALE", "Used by sale"
    SALE_REVERSAL = "SALE_REVERSAL", "Sale cancelled"
    WASTAGE = "WASTAGE", "Wastage"
    ADJUSTMENT = "ADJUSTMENT", "Stock count adjustment"


class StockMovement(models.Model):
    """
    Immutable stock ledger. Every change to stock is one row here, so
    "where did the stock go?" can always be answered. Never edit or delete.
    """
    location = models.ForeignKey("organizations.Location", on_delete=models.PROTECT, related_name="stock_movements")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name="movements")
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity_change = models.DecimalField(max_digits=14, decimal_places=3, help_text="Signed, base units")
    balance_after = models.DecimalField(max_digits=14, decimal_places=3)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    reference_type = models.CharField(max_length=30, blank=True)
    reference_id = models.PositiveIntegerField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["location", "ingredient", "-created_at"])]


class Recipe(BaseModel):
    """
    Bill of materials. Belongs to EITHER a menu item variant (one serving)
    OR a prepared ingredient (output_quantity base units per batch).
    """
    product_variant = models.OneToOneField(
        "catalog.ProductVariant", null=True, blank=True, on_delete=models.CASCADE, related_name="recipe"
    )
    ingredient = models.OneToOneField(
        Ingredient, null=True, blank=True, on_delete=models.CASCADE, related_name="recipe"
    )
    output_quantity = models.DecimalField(
        max_digits=14, decimal_places=3, default=1,
        help_text="Variant: servings made (1). Prepared ingredient: base units one batch yields.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(Q(product_variant__isnull=False, ingredient__isnull=True)
                           | Q(product_variant__isnull=True, ingredient__isnull=False)),
                name="recipe_belongs_to_exactly_one",
            ),
            models.CheckConstraint(condition=Q(output_quantity__gt=0), name="recipe_output_positive"),
        ]


class RecipeLine(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="lines")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.PROTECT, related_name="used_in")
    quantity = models.DecimalField(max_digits=14, decimal_places=3, help_text="Base units per output")

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["recipe", "ingredient"], name="unique_ingredient_per_recipe"),
            models.CheckConstraint(condition=Q(quantity__gt=0), name="recipe_line_quantity_positive"),
        ]
