from django.db import models
from django.db.models import Q


class LoyaltySettings(models.Model):
    """Each restaurant decides its own points rules from the dashboard."""
    organization = models.OneToOneField("organizations.Organization", on_delete=models.CASCADE, related_name="loyalty")
    enabled = models.BooleanField(default=False)
    spend_per_point = models.DecimalField(max_digits=10, decimal_places=2, default=100, help_text="Customer earns 1 point for every this much spent")
    point_value = models.DecimalField(max_digits=10, decimal_places=2, default=1, help_text="Discount given by 1 point")
    min_redeem = models.PositiveIntegerField(default=100, help_text="Points can be used only when the balance is at least this")
    email_customers = models.BooleanField(default=True, help_text="Email customers when they earn points")
    reminders = models.BooleanField(default=True, help_text="Send points reminders by email")


class LoyaltyEntry(models.Model):
    class Kind(models.TextChoices):
        EARN = "EARN", "Earned"
        REDEEM = "REDEEM", "Used"
        EARN_REVERSED = "EARN_REVERSED", "Earned points taken back"
        REDEEM_RETURNED = "REDEEM_RETURNED", "Used points returned"
        ADJUST = "ADJUST", "Adjusted by staff"

    customer = models.ForeignKey("customers.Customer", on_delete=models.CASCADE, related_name="loyalty_entries")
    order = models.ForeignKey("orders.Order", null=True, blank=True, on_delete=models.SET_NULL, related_name="loyalty_entries")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    points = models.IntegerField(help_text="+ earned, - used")
    balance_after = models.PositiveIntegerField()
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Discount value for REDEEM entries")
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]
        constraints = [models.UniqueConstraint(fields=["order", "kind"], condition=Q(order__isnull=False), name="one_loyalty_entry_per_kind_per_order")]
