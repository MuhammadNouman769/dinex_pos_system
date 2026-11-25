from django.db import models

from apps.organizations.models import Organization
from apps.utils.models import BaseModel


class ModifierGroup(BaseModel):

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="modifier_groups",
    )

    name = models.CharField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    min_selections = models.PositiveIntegerField(
        default=0,
    )

    max_selections = models.PositiveIntegerField(
        default=1,
    )

    is_required = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ModifierOption(BaseModel):

    modifier_group = models.ForeignKey(
        ModifierGroup,
        on_delete=models.CASCADE,
        related_name="options",
    )

    name = models.CharField(
        max_length=255,
    )

    price_adjustment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    position = models.PositiveIntegerField(
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["position", "name"]

    def __str__(self):
        return self.name


class ProductModifierGroup(BaseModel):

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="modifier_group_links",
    )

    modifier_group = models.ForeignKey(
        ModifierGroup,
        on_delete=models.CASCADE,
        related_name="product_links",
    )

    display_order = models.PositiveIntegerField(
        default=0,
    )

    is_required_override = models.BooleanField(
        null=True,
        blank=True,
    )

    min_selections_override = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    max_selections_override = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["display_order"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "product",
                    "modifier_group",
                ],
                name="unique_product_modifier_group",
            ),
        ]

    def __str__(self):
        return f"{self.product} - {self.modifier_group}"