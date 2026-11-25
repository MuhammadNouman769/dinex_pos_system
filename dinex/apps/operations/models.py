from django.conf import settings
from django.db import models
from django.db.models import Q


class Reservation(models.Model):
    class Status(models.TextChoices):
        BOOKED = "BOOKED", "Booked"
        SEATED = "SEATED", "Seated"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"
        NO_SHOW = "NO_SHOW", "No-show"

    location = models.ForeignKey("organizations.Location", on_delete=models.CASCADE, related_name="reservations")
    table = models.ForeignKey("orders.Table", null=True, blank=True, on_delete=models.SET_NULL, related_name="reservations")
    guest_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30, blank=True)
    party_size = models.PositiveIntegerField()
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=90)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.BOOKED)
    notes = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["starts_at", "id"]
        constraints = [models.CheckConstraint(condition=Q(party_size__gt=0), name="reservation_party_positive")]
        indexes = [models.Index(fields=["location", "starts_at"])]


class Supplier(models.Model):
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="suppliers")
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["organization", "name"], name="unique_supplier_name_per_org")]


class Purchase(models.Model):
    """A delivery from a supplier. Receiving it stocks the ingredients in."""
    location = models.ForeignKey("organizations.Location", on_delete=models.PROTECT, related_name="purchases")
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.PROTECT, related_name="purchases")
    invoice_no = models.CharField(max_length=50, blank=True)
    date = models.DateField()
    total = models.DecimalField(max_digits=12, decimal_places=2)
    paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]


class PurchaseLine(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="lines")
    ingredient = models.ForeignKey("inventory.Ingredient", on_delete=models.PROTECT, related_name="+")
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.CharField(max_length=10, blank=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=4, help_text="Price per entered unit")
    line_total = models.DecimalField(max_digits=12, decimal_places=2)


class Expense(models.Model):
    class Source(models.TextChoices):
        DRAWER = "DRAWER", "Cash drawer"
        OTHER = "OTHER", "Paid outside the till"

    location = models.ForeignKey("organizations.Location", on_delete=models.PROTECT, related_name="expenses")
    date = models.DateField()
    category = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.OTHER)
    movement = models.OneToOneField("cash.CashMovement", null=True, blank=True, on_delete=models.SET_NULL, related_name="expense")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="expense_amount_positive")]
