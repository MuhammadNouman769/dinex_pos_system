from django.db import models
from apps.utils.models import BaseModel


class Customer(BaseModel):
    """
    Customer model - Linked to Location (not Organization directly)
    """
    
    class CustomerType(models.TextChoices):
        WALK_IN = "WALK_IN", "Walk-in"
        REGULAR = "REGULAR", "Regular"
        CORPORATE = "CORPORATE", "Corporate"

    location = models.ForeignKey(
        "organizations.Location",
        on_delete=models.CASCADE,
        related_name="customers",
        help_text="Location where customer usually visits"
    )

    first_name = models.CharField(
        max_length=100,
        help_text="Customer first name"
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Customer last name"
    )

    phone = models.CharField(
        max_length=20,
        help_text="Customer phone number (unique per location)"
    )

    email = models.EmailField(
        blank=True,
        null=True,
        help_text="Customer email (optional)"
    )

    address = models.TextField(
        blank=True,
        help_text="Customer address (for delivery)"
    )

    customer_type = models.CharField(
        max_length=20,
        choices=CustomerType.choices,
        default=CustomerType.WALK_IN,
        help_text="Customer type"
    )

    total_orders = models.PositiveIntegerField(
        default=0,
        help_text="Total orders placed"
    )

    total_spent = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Total amount spent"
    )

    last_order_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last order timestamp"
    )

    notes = models.TextField(
        blank=True,
        help_text="Additional notes about customer"
    )

    points_balance = models.PositiveIntegerField(default=0, help_text="Loyalty points")
    last_reminder_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    class Meta:
        ordering = ["-total_orders", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "phone"],
                condition=models.Q(is_deleted=False),
                name="unique_customer_phone_per_location",
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.phone}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def add_order(self, amount):
        """Update customer stats after order"""
        self.total_orders += 1
        self.total_spent += amount
        from django.utils import timezone
        self.last_order_at = timezone.now()
        self.save()