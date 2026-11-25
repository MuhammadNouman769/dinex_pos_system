from decimal import Decimal
from django.db import models
from apps.utils.models import BaseModel


class OrderItem(BaseModel):
    """
    Order Item Model
    """
    
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Order"
    )

    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="order_items",
        help_text="Product variant"
    )

    product_name = models.CharField(
        max_length=255,
        help_text="Product name (snapshot)"
    )

    variant_name = models.CharField(
        max_length=255,
        help_text="Variant name (snapshot)"
    )

    quantity = models.PositiveIntegerField(
        default=1,
        help_text="Quantity"
    )

    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Unit price at order time"
    )

    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Total price (quantity * unit_price)"
    )

    tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Tax for this item"
    )

    discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Discount for this item"
    )

    notes = models.TextField(
        blank=True,
        help_text="Special instructions"
    )

    modifiers = models.JSONField(default=list, blank=True, help_text="Chosen options [{id, group, name, price}] (snapshot)")

    deal = models.ForeignKey(
        "catalog.Deal", null=True, blank=True, on_delete=models.SET_NULL, related_name="order_items",
        help_text="Set when this line came from a deal",
    )
    deal_name = models.CharField(max_length=255, blank=True, help_text="Deal name (snapshot)")

    class Meta:
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="valid_quantity",
            ),
        ]

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def save(self, *args, **kwargs):
        """Calculate total price before saving"""
        #  Use Decimal for multiplication
        self.total_price = Decimal(str(self.quantity)) * self.unit_price
        super().save(*args, **kwargs)
    
    def calculate_total(self):
        """Calculate total price"""
        from decimal import Decimal
        return Decimal(str(self.quantity)) * self.unit_price

        