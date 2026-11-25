from django.conf import settings
from django.db import models
from django.db.models import Q


class Shift(models.Model):
    """One cashier's turn at the till. All payments and cash movements belong to a shift."""

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"

    location = models.ForeignKey("organizations.Location", on_delete=models.PROTECT, related_name="shifts")
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    opened_at = models.DateTimeField(auto_now_add=True)
    opening_cash = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN)

    closed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    closed_at = models.DateTimeField(null=True, blank=True)
    expected_cash = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    counted_cash = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    difference = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                     help_text="counted - expected. Negative = cash is short.")
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-opened_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["location", "opened_by"], condition=Q(status="OPEN"),
                name="one_open_shift_per_cashier_per_location",
            ),
            models.CheckConstraint(condition=Q(opening_cash__gte=0), name="shift_opening_cash_not_negative"),
        ]


class PaymentMethod(models.TextChoices):
    CASH = "CASH", "Cash"
    CARD = "CARD", "Card"
    WALLET = "WALLET", "JazzCash / Easypaisa"
    BANK = "BANK", "Bank transfer"


class Payment(models.Model):
    """Money in (PAYMENT) or out (REFUND) for one order. Immutable."""

    class Kind(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment"
        REFUND = "REFUND", "Refund"

    order = models.ForeignKey("orders.Order", on_delete=models.PROTECT, related_name="payments")
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="payments")
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.PAYMENT)
    method = models.CharField(max_length=10, choices=PaymentMethod.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    tendered = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                   help_text="Cash handed over by the customer (change = tendered - amount)")
    reference = models.CharField(max_length=100, blank=True, help_text="Card slip / transaction id")
    reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive")]
        indexes = [models.Index(fields=["shift", "kind", "method"])]


class CashMovement(models.Model):
    """Cash put into / taken out of the drawer outside of sales."""

    class Kind(models.TextChoices):
        CASH_IN = "CASH_IN", "Cash in"
        CASH_OUT = "CASH_OUT", "Cash out"
        EXPENSE = "EXPENSE", "Expense paid from drawer"
        SAFE_DROP = "SAFE_DROP", "Moved to safe"

    shift = models.ForeignKey(Shift, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=50, blank=True, help_text="e.g. vegetables, gas, electricity")
    reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="cash_movement_amount_positive")]


class AuditLog(models.Model):
    """Who did what, when. For voids, refunds, discounts, shifts: never edited or deleted."""
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="+")
    location = models.ForeignKey("organizations.Location", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    action = models.CharField(max_length=50)
    object_type = models.CharField(max_length=50, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["organization", "-created_at"]), models.Index(fields=["action"])]
