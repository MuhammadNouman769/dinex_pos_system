from django.db import models
from apps.utils.models import BaseModel


""" ======================= Location Model ======================= """
class Location(BaseModel):

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="locations",
    )

    name = models.CharField(
        max_length=255,
    )

    address = models.TextField()

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    is_primary = models.BooleanField(
        default=False,
    )

    class InventoryPolicy(models.TextChoices):
        ALLOW = "ALLOW", "Allow sale even if stock runs out (stock goes negative)"
        WARN = "WARN", "Allow sale but warn"
        BLOCK = "BLOCK", "Block sale when stock is insufficient"

    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=10,
        help_text="Sales tax in percent (e.g. 10 = 10%)",
    )
    service_charge_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Service charge in percent",
    )
    inventory_policy = models.CharField(
        max_length=10, choices=InventoryPolicy.choices, default=InventoryPolicy.ALLOW,
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return (
            f"{self.organization.name} - "
            f"{self.name}"
        )