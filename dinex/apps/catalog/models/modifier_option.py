from django.db import models

from apps.utils.models import BaseModel


class ModifierOption(BaseModel):

    modifier_group = models.ForeignKey(
        "catalog.ModifierGroup",
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