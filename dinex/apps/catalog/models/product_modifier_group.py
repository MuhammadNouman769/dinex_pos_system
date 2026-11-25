from django.db import models

from apps.utils.models import BaseModel


class ProductModifierGroup(BaseModel):

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="modifier_group_links",
    )

    modifier_group = models.ForeignKey(
        "catalog.ModifierGroup",
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