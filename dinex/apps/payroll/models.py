from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q


class PayProfile(models.Model):
    """How one employee is paid. Salary figures are private: only the owner can see or change them."""

    class PayType(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly salary"
        DAILY = "DAILY", "Daily wage"
        HOURLY = "HOURLY", "Hourly rate"

    class MonthBasis(models.TextChoices):
        D30 = "30", "30 days"
        D26 = "26", "26 working days"
        CALENDAR = "CALENDAR", "Actual days in the month"

    class LateRule(models.TextChoices):
        NONE = "NONE", "No deduction for lateness"
        MINUTES = "MINUTES", "Deduct the late minutes"
        COUNT = "COUNT", "Every N late arrivals, deduct some days"

    employee = models.OneToOneField("staff.Employee", on_delete=models.CASCADE, related_name="pay_profile")
    pay_type = models.CharField(max_length=8, choices=PayType.choices, default=PayType.MONTHLY)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Monthly salary, daily wage or hourly rate, by pay type")
    month_basis = models.CharField(max_length=8, choices=MonthBasis.choices, default=MonthBasis.D30,
                                   help_text="Monthly salary: what one day's pay is (salary ÷ this)")
    standard_hours = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True,
                                         help_text="Paid hours in a normal day. Empty = taken from the duty hours (or 8)")
    fixed_allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Added every month (transport, food…)")
    fixed_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Taken every month (EOBI, uniform…)")
    overtime_enabled = models.BooleanField(default=True)
    absent_penalty_days = models.DecimalField(max_digits=3, decimal_places=1, default=1, help_text="Monthly salary: days of pay lost per absent day")
    pay_paid_leave = models.BooleanField(default=True, help_text="Daily / hourly: are paid-leave days paid?")
    pay_weekly_off = models.BooleanField(default=False, help_text="Daily wage: is the weekly off paid?")
    late_rule = models.CharField(max_length=8, choices=LateRule.choices, default=LateRule.NONE)
    late_every = models.PositiveSmallIntegerField(default=3, help_text="COUNT rule: every this many late days…")
    late_deduct_days = models.DecimalField(max_digits=3, decimal_places=2, default=Decimal("0.5"), help_text="…deduct this many days of pay")
    notes = models.CharField(max_length=255, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(base_amount__gte=0), name="pay_base_not_negative")]


class Advance(models.Model):
    """Money given to an employee in advance; taken back in installments from salary."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Being repaid"
        CLEARED = "CLEARED", "Fully repaid"
        VOID = "VOID", "Cancelled"

    employee = models.ForeignKey("staff.Employee", on_delete=models.PROTECT, related_name="advances")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    installment = models.DecimalField(max_digits=12, decimal_places=2, help_text="Taken from each month's salary")
    given_on = models.DateField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ACTIVE)
    given_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-given_on", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="advance_amount_positive"),
            models.CheckConstraint(condition=Q(installment__gt=0), name="advance_installment_positive"),
        ]

    @property
    def repaid(self):
        return self.repayments.aggregate(t=models.Sum("amount"))["t"] or Decimal("0.00")

    @property
    def balance(self):
        return self.amount - self.repaid


class PayrollRun(models.Model):
    """One branch's payroll for one calendar month. DRAFT can be recalculated; FINALIZED is locked."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        FINALIZED = "FINALIZED", "Finalized"

    location = models.ForeignKey("organizations.Location", on_delete=models.PROTECT, related_name="payroll_runs")
    month = models.DateField(help_text="First day of the month")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    finalized_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    finalized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-month", "location__name"]
        constraints = [models.UniqueConstraint(fields=["location", "month"], name="one_payroll_run_per_branch_per_month")]


class Payslip(models.Model):
    """What one employee earns for the month: a snapshot of the numbers, so later changes never rewrite history."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        UNPAID = "UNPAID", "To pay"
        PAID = "PAID", "Paid"

    run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name="slips")
    employee = models.ForeignKey("staff.Employee", on_delete=models.PROTECT, related_name="payslips")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DRAFT)

    pay_type = models.CharField(max_length=8)
    base_amount = models.DecimalField(max_digits=12, decimal_places=2)
    daily_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    hourly_rate = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    scheduled_days = models.PositiveSmallIntegerField(default=0)
    present_days = models.PositiveSmallIntegerField(default=0)
    absent_days = models.PositiveSmallIntegerField(default=0)
    unmarked_days = models.PositiveSmallIntegerField(default=0)
    leave_paid = models.PositiveSmallIntegerField(default=0)
    leave_unpaid = models.PositiveSmallIntegerField(default=0)
    weekly_off_days = models.PositiveSmallIntegerField(default=0)
    late_days = models.PositiveSmallIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)
    worked_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    deliveries = models.PositiveIntegerField(default=0)

    basic_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    overtime_pay = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gross = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    absent_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    leave_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    late_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fixed_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    other_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    advance_deduction = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    lines = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    advance_plan = models.JSONField(default=list, blank=True, help_text="[{advance, amount}] taken when the run is finalized")

    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    paid_method = models.CharField(max_length=30, blank=True)
    paid_reference = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["employee__name"]
        constraints = [models.UniqueConstraint(fields=["run", "employee"], name="one_payslip_per_employee_per_run")]


class PayslipAdjustment(models.Model):
    """A bonus or a one-off deduction added by hand to a draft payslip."""

    class Kind(models.TextChoices):
        BONUS = "BONUS", "Bonus"
        DEDUCTION = "DEDUCTION", "Deduction"

    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE, related_name="adjustments")
    kind = models.CharField(max_length=10, choices=Kind.choices)
    label = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="adjustment_amount_positive")]


class AdvanceRepayment(models.Model):
    advance = models.ForeignKey(Advance, on_delete=models.CASCADE, related_name="repayments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    payslip = models.ForeignKey(Payslip, null=True, blank=True, on_delete=models.SET_NULL, related_name="repayments")
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        ordering = ["date", "id"]
        constraints = [models.CheckConstraint(condition=Q(amount__gt=0), name="repayment_amount_positive")]
