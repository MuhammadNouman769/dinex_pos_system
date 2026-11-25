from django.db import models

from apps.organizations.models import Organization
from apps.utils.models import OrderedModel


class ProductCategory(OrderedModel):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="product_categories",
    )

    name = models.CharField(max_length=255)

    slug = models.SlugField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )

    image = models.ImageField(
        upload_to="catalog/categories/",
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["position", "name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                condition=models.Q(is_deleted=False),
                name="unique_category_slug_per_organization",
            ),
        ]

    def __str__(self):
        return self.name