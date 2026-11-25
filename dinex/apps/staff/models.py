from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.utils.models import BaseModel


class Role(models.TextChoices):
    MANAGER = "MANAGER", "Manager"
    CASHIER = "CASHIER", "Cashier"
    WAITER = "WAITER", "Waiter"
    RIDER = "RIDER", "Delivery rider"
    CHEF = "CHEF", "Chef"
    HELPER = "HELPER", "Kitchen helper"
    OTHER = "OTHER", "Other"


class Employee(BaseModel):
    """
    A person who works at a branch. Having a record here does NOT mean they can log in:
    waiters and riders usually don't. (Optional `user` link for those who do.)
    """
    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE, related_name="employees")
    location = models.ForeignKey("organizations.Location", on_delete=models.PROTECT, related_name="employees")
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="employee")

    code = models.CharField(max_length=12, help_text="E-001, E-002… unique inside the restaurant")
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.WAITER)
    phone = models.CharField(max_length=20, blank=True)
    cnic = models.CharField(max_length=15, blank=True, help_text="National ID, 13 digits")
    address = models.CharField(max_length=255, blank=True)
    emergency_contact = models.CharField(max_length=120, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # riders
    vehicle = models.CharField(max_length=60, blank=True, help_text="e.g. Honda 70 · LEB-1234")
    delivery_commission = models.DecimalField(max_digits=8, decimal_places=2, default=0,
                                              help_text="Paid to a rider for each delivered order (used by payroll)")

    pin_hash = models.CharField(max_length=128, blank=True, help_text="Hashed PIN for the attendance kiosk")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["organization", "code"], condition=Q(is_deleted=False), name="unique_employee_code_per_org"),
            models.CheckConstraint(condition=Q(delivery_commission__gte=0), name="employee_commission_not_negative"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"


class RiderSettlement(models.Model):
    """A rider hands the cash collected on deliveries to the cashier. Append-only."""
    rider = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="settlements")
    location = models.ForeignKey("organizations.Location", on_delete=models.PROTECT, related_name="+")
    shift = models.ForeignKey("cash.Shift", on_delete=models.PROTECT, related_name="+")
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    expected = models.DecimalField(max_digits=12, decimal_places=2, help_text="Cash due on the selected orders")
    handed = models.DecimalField(max_digits=12, decimal_places=2, help_text="Cash the rider actually handed over")
    shortage = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="expected - handed (0 if complete)")
    order_ids = models.JSONField(default=list)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(condition=Q(handed__gte=0), name="settlement_handed_not_negative")]


class WorkSchedule(models.Model):
    """An employee's usual duty: hours, weekly off and the rules used to work out late / early leave / overtime."""
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="schedule")
    start_time = models.TimeField()
    end_time = models.TimeField(help_text="Earlier than the start = the shift ends after midnight")
    weekly_off = models.JSONField(default=list, blank=True, help_text="Days off: 0 = Monday … 6 = Sunday")
    grace_minutes = models.PositiveSmallIntegerField(default=10, help_text="Arriving up to this late (or leaving this early) is not counted")
    min_overtime_minutes = models.PositiveSmallIntegerField(default=30, help_text="Staying less than this after duty ends is not overtime")
    overtime_multiplier = models.DecimalField(max_digits=4, decimal_places=2, default=1.5, help_text="Overtime pays this multiple of the hourly rate (used by payroll)")

    @property
    def overnight(self):
        return self.end_time <= self.start_time


class AttendanceRecord(models.Model):
    """
    One row per employee per work day. PRESENT rows have check_in (and check_out once they leave);
    ABSENT / LEAVE rows have no times. Late / early / overtime are worked out whenever a row is saved.
    Rows are never deleted: corrections are edits with a reason, written to the audit log.
    """
    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LEAVE = "LEAVE", "On leave"

    class Source(models.TextChoices):
        KIOSK = "KIOSK", "PIN kiosk"
        MANAGER = "MANAGER", "Entered by a manager"

    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="attendance")
    date = models.DateField(help_text="Work day: the local date the shift started")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PRESENT)
    paid_leave = models.BooleanField(default=False)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=8, choices=Source.choices, default=Source.KIOSK)
    note = models.CharField(max_length=255, blank=True)
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    worked_minutes = models.PositiveIntegerField(default=0)
    late_minutes = models.PositiveIntegerField(default=0)
    early_leave_minutes = models.PositiveIntegerField(default=0)
    overtime_minutes = models.PositiveIntegerField(default=0)
    on_off_day = models.BooleanField(default=False, help_text="Worked on the weekly off: all of it counts as overtime")
    auto_closed = models.BooleanField(default=False, help_text="Forgot to check out: closed automatically at the end of duty")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "employee__name"]
        constraints = [
            models.UniqueConstraint(fields=["employee", "date"], name="one_attendance_row_per_employee_per_day"),
            models.CheckConstraint(condition=Q(check_out__isnull=True) | Q(check_in__isnull=False), name="checkout_needs_checkin"),
        ]
        indexes = [models.Index(fields=["date", "status"])]
