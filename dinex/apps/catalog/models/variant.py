from django.db import models

from apps.utils.models import BaseModel


class ProductVariant(BaseModel):

    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="variants",
    )

    name = models.CharField(
        max_length=255,
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
    )

    barcode = models.CharField(
        max_length=100,
        blank=True,
    )

    base_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
    )

    position = models.PositiveIntegerField(
        default=0,
    )

    is_default = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["position", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=["product", "sku"],
                condition=~models.Q(sku="") & models.Q(is_deleted=False),
                name="unique_variant_sku_per_product",
            ),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.name}"