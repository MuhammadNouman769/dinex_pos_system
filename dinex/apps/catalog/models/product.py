from django.db import models

from apps.organizations.models import Organization
from apps.utils.models import BaseModel


class Product(BaseModel):

    class ProductType(models.TextChoices):
        SELLABLE = "SELLABLE", "Sellable"
        INVENTORY = "INVENTORY", "Inventory"
        PREPARED = "PREPARED", "Prepared"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="products",
    )

    category = models.ForeignKey(
        "catalog.ProductCategory",
        on_delete=models.PROTECT,
        related_name="products",
    )

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        default=ProductType.SELLABLE,
        db_index=True,
    )

    image = models.ImageField(
        upload_to="catalog/products/",
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    dietary_tags = models.ManyToManyField(
        "catalog.DietaryTag",
        blank=True,
        related_name="products",
    )

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                condition=models.Q(is_deleted=False),
                name="unique_product_slug_per_organization",
            ),
            models.UniqueConstraint(
                fields=["organization", "sku"],
                condition=~models.Q(sku="") & models.Q(is_deleted=False),
                name="unique_product_sku_per_organization",
            ),
        ]

    def __str__(self):
        return self.name