from decimal import Decimal

from django.db import models
from django.db.models import Q


class Plan(models.Model):
    """A subscription plan XverLabs sells (monthly, in PKR)."""
    code = models.SlugField(max_length=30, unique=True)
    name = models.CharField(max_length=60)
    description = models.CharField(max_length=255, blank=True)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    max_locations = models.PositiveIntegerField(default=1)
    max_users = models.PositiveIntegerField(default=5, help_text="Active staff accounts incl. the owner")
    features = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "price_monthly"]
        constraints = [models.CheckConstraint(condition=Q(price_monthly__gte=0), name="plan_price_not_negative")]

    def __str__(self):
        return self.name


class Subscription(models.Model):
    class Status(models.TextChoices):
        TRIAL = "TRIAL", "Free trial"
        ACTIVE = "ACTIVE", "Active"
        PAST_DUE = "PAST_DUE", "Payment overdue"
        SUSPENDED = "SUSPENDED", "Suspended"
        CANCELLED = "CANCELLED", "Cancelled"

    organization = models.OneToOneField("organizations.Organization", on_delete=models.CASCADE, related_name="subscription")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TRIAL)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateField(null=True, blank=True)
    current_period_end = models.DateField(null=True, blank=True)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                         help_text="Special price for this restaurant (instead of the plan price)")
    suspended_reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    terms_version = models.CharField(max_length=20, blank=True, help_text="Terms of Use version the owner agreed to")
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    signup_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def price(self) -> Decimal:
        return self.price_override if self.price_override is not None else self.plan.price_monthly


class Invoice(models.Model):
    class Status(models.TextChoices):
        DUE = "DUE", "Due"
        PAID = "PAID", "Paid"
        VOID = "VOID", "Void"

    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="invoices")
    subscription = models.ForeignKey(Subscription, null=True, blank=True, on_delete=models.SET_NULL, related_name="invoices")
    number = models.CharField(max_length=20, unique=True)
    period_start = models.DateField()
    period_end = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=6, choices=Status.choices, default=Status.DUE)
    issued_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField()
    paid_at = models.DateTimeField(null=True, blank=True)
    method = models.CharField(max_length=30, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-issued_at", "-id"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="invoice_amount_positive")]
        indexes = [models.Index(fields=["status", "due_date"])]


class PaymentAccount(models.Model):
    """Where restaurants send their subscription money (JazzCash, Easypaisa, bank...). Edited by XverLabs."""

    class Method(models.TextChoices):
        JAZZCASH = "JAZZCASH", "JazzCash"
        EASYPAISA = "EASYPAISA", "Easypaisa"
        BANK = "BANK", "Bank transfer"
        OTHER = "OTHER", "Other"

    method = models.CharField(max_length=10, choices=Method.choices)
    account_title = models.CharField(max_length=120, help_text="Name on the account")
    account_number = models.CharField(max_length=60, help_text="Mobile number / IBAN / account number")
    bank_name = models.CharField(max_length=80, blank=True)
    instructions = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]


class PaymentSubmission(models.Model):
    """A restaurant says 'I sent the money': XverLabs checks it and approves (system starts) or rejects."""

    class Status(models.TextChoices):
        PENDING = "PENDING", "Waiting for confirmation"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="payment_submissions")
    invoice = models.ForeignKey(Invoice, null=True, blank=True, on_delete=models.SET_NULL, related_name="submissions")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=30)
    reference = models.CharField(max_length=100, help_text="Transaction / TID number")
    sender_name = models.CharField(max_length=120, blank=True)
    sender_number = models.CharField(max_length=40, blank=True)
    note = models.CharField(max_length=255, blank=True)
    proof = models.ImageField(upload_to="billing/proofs/", null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reject_reason = models.CharField(max_length=255, blank=True)
    submitted_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="submission_amount_positive")]
        indexes = [models.Index(fields=["status", "-created_at"])]
