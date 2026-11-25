from django.db import models

from apps.organizations.models import Location
from apps.utils.models import BaseModel


class ProductLocation(BaseModel):
    """
    Model to assign products/variants to specific locations
    """
    
    product = models.ForeignKey(
        "catalog.Product",
        on_delete=models.CASCADE,
        related_name="location_assignments",
    )
    
    product_variant = models.ForeignKey(
        "catalog.ProductVariant",
        on_delete=models.CASCADE,
        related_name="location_assignments",
        null=True,
        blank=True,
    )
    
    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name="product_assignments",
    )
    
    is_available = models.BooleanField(
        default=True,
        db_index=True,
    )
    
    available_quantity = models.PositiveIntegerField(
        default=0,
    )
    
    class Meta:
        ordering = ["location", "product"]
        
        constraints = [
            models.UniqueConstraint(
                fields=["product", "location"],
                condition=models.Q(product_variant__isnull=True, is_deleted=False),
                name="unique_product_location",
            ),
            models.UniqueConstraint(
                fields=["product_variant", "location"],
                condition=~models.Q(product_variant=None) & models.Q(is_deleted=False),
                name="unique_variant_location",
            ),
        ]
    
    def __str__(self):
        variant_info = f" - {self.product_variant.name}" if self.product_variant else ""
        return f"{self.product.name}{variant_info} @ {self.location.name}"