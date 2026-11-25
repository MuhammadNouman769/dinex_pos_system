from django.db import models

from apps.organizations.models import Organization, Location
from apps.utils.models import BaseModel


class Deal(BaseModel):
    """Deal model for discounts and promotions"""

    class DiscountType(models.TextChoices):
        FIXED = "FIXED", "Fixed Amount"
        PERCENTAGE = "PERCENTAGE", "Percentage"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="deals",
    )

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
    )

    description = models.TextField(
        blank=True,
    )

    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
    )

    discount_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    image = models.ImageField(upload_to="catalog/deals/", null=True, blank=True)

    start_at = models.DateTimeField()

    end_at = models.DateTimeField()

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "slug"],
                condition=models.Q(is_deleted=False),
                name="unique_deal_slug_per_organization",
            ),
        ]

    def __str__(self):
        return self.name


class DealItem(BaseModel):
    """Deal item linking a product variant to a deal"""

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.PROTECT,
        related_name="deal_items",
    )

    quantity = models.PositiveIntegerField(
        default=1,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deal", "product_variant"],
                name="unique_deal_product_variant",
            ),
        ]

    def __str__(self):
        return f"{self.deal.name} - {self.product_variant.name}"


class DealLocation(BaseModel):
    """Deal location assignment"""

    deal = models.ForeignKey(
        Deal,
        on_delete=models.CASCADE,
        related_name="locations",
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="deals",
    )

    is_enabled = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["deal", "location"],
                name="unique_deal_location",
            ),
        ]

    def __str__(self):
        return f"{self.deal.name} @ {self.location.name}"