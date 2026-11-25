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