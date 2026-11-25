from django.db import models

from apps.organizations.models import Organization
from apps.utils.models import BaseModel


class DietaryTag(BaseModel):

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="dietary_tags",
    )

    name = models.CharField(
        max_length=100,
    )

    slug = models.SlugField(
        max_length=100,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                condition=models.Q(is_deleted=False),
                name="unique_dietary_tag_per_organization",
            ),
        ]

    def __str__(self):
        return self.name