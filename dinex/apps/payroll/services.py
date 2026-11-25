"""Payroll runs: generate -> (adjust) -> finalize -> pay. Plus advances."""
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.cash import services as cash
from apps.cash.services import audit
from apps.orders.models import Order
from apps.payroll import calc
from apps.payroll.models import Advance, AdvanceRepayment, PayProfile, PayrollRun, Payslip, PayslipAdjustment
from apps.staff import attendance as att
from apps.staff.models import AttendanceRecord, Employee

ZERO = Decimal("0.00")
METHODS = {"CASH": "Cash", "BANK": "Bank transfer", "JAZZCASH": "JazzCash", "EASYPAISA": "Easypaisa", "CHEQUE": "Cheque", "OTHER": "Other"}
SLIP_FIELDS = ["daily_rate", "hourly_rate", "scheduled_days", "present_days", "absent_days", "unmarked_days", "leave_paid", "leave_unpaid",
               "weekly_off_days", "late_days", "late_minutes", "worked_minutes", "overtime_minutes", "deliveries", "basic_pay", "overtime_pay",
               "allowance", "commission", "bonus", "gross", "absent_deduction", "leave_deduction", "late_deduction", "fixed_deduction",
               "other_deduction", "advance_deduction", "deductions", "net", "lines", "warnings", "advance_plan"]


class PayrollError(APIException):
    status_code = 400
    default_code = "payroll_error"


def today():
    return att.local_date(att.now())


# ───────────────────────── advances ─────────────────────────
def give_advance(emp, amount, installment, given_on, reason, user):
    amount = cash.q2(amount)
    if amount <= 0:
        raise PayrollError("The advance must be more than zero.")
    installment = cash.q2(installment) if installment not in (None, "") else amount
    if installment <= 0 or installment > amount:
        raise PayrollError("The monthly installment must be more than zero and not more than the advance.")
    if given_on > today():
        raise PayrollError("An advance cannot be dated in the future.")
    adv = Advance.objects.create(employee=emp, amount=amount, installment=installment, given_on=given_on, reason=(reason or "")[:255], given_by=user)
    audit(user, emp.location, "advance_given", adv, employee=emp.name, amount=amount, installment=installment, reason=reason or "")
    return adv


@transaction.atomic
def repay_advance(adv, amount, note, user):
    adv = Advance.objects.select_for_update().get(pk=adv.pk)
    if adv.status != Advance.Status.ACTIVE:
        raise PayrollError("This advance is not being repaid.")
    amount = cash.q2(amount)
    if amount <= 0:
        raise PayrollError("The amount must be more than zero.")
    if amount > adv.balance:
        raise PayrollError(f"Only {adv.balance} is still owed.")
    AdvanceRepayment.objects.create(advance=adv, amount=amount, date=today(), note=(note or "")[:255], created_by=user)
    if adv.balance <= 0:
        adv.status = Advance.Status.CLEARED
        adv.save(update_fields=["status"])
    audit(user, adv.employee.location, "advance_repaid", adv, employee=adv.employee.name, amount=amount, note=note or "")
    return adv


def void_advance(adv, user):
    if adv.status != Advance.Status.ACTIVE or adv.repayments.exists():
        raise PayrollError("Only an advance with no repayments yet can be cancelled.")
    adv.status = Advance.Status.VOID
    adv.save(update_fields=["status"])
    audit(user, adv.employee.location, "advance_voided", adv, employee=adv.employee.name, amount=adv.amount)
    return adv


def _open_advances(emp, upto):
    out = []
    for a in Advance.objects.filter(employee=emp, status=Advance.Status.ACTIVE, given_on__lte=upto).order_by("given_on", "id"):
        if a.balance > 0:
            out.append((a.id, a.reason, a.installment, a.balance))
    return out


# ───────────────────────── runs ─────────────────────────
def parse_month(value):
    try:
        y, m = str(value).split("-")
        d = date(int(y), int(m), 1)
    except (ValueError, TypeError):
        raise PayrollError("Use the month as YYYY-MM.")
    if d > today().replace(day=1):
        raise PayrollError("You cannot run payroll for a future month.")
    return d


def _eligible(location, start, end):
    qs = Employee.objects.filter(location=location, pay_profile__isnull=False).select_related("pay_profile", "schedule")
    for emp in qs.order_by("name"):
        if emp.is_active or AttendanceRecord.objects.filter(employee=emp, date__range=(start, end)).exists():
            if emp.joining_date and emp.joining_date > end:
                continue
            yield emp


def _compute_for(emp, run, adjustments):
    start, end = run.month, calc.month_end(run.month)
    at = att.now()
    row = att.report(run.location, start, end, emp, at)[0]
    deliveries = Order.objects.filter(rider=emp, order_type="DELIVERY", status="COMPLETED", delivered_at__date__range=(start, end)).count()
    return calc.compute(emp, emp.pay_profile, start, end, row, deliveries, adjustments, _open_advances(emp, end))


def _apply(slip, data):
    slip.pay_type, slip.base_amount = slip.employee.pay_profile.pay_type, slip.employee.pay_profile.base_amount
    for f in SLIP_FIELDS:
        setattr(slip, f, data[f])
    slip.save()


def _adjustments(slip):
    return [(a.kind, a.label, a.amount) for a in slip.adjustments.all()]


@transaction.atomic
def generate_run(location, month, user):
    run, created = PayrollRun.objects.get_or_create(location=location, month=month, defaults={"created_by": user})
    if run.status == PayrollRun.Status.FINALIZED:
        raise PayrollError("This month is already finalized. Reopen it first if something must change.")
    end = calc.month_end(month)
    keep = set()
    for emp in _eligible(location, month, end):
        slip = Payslip.objects.filter(run=run, employee=emp).first() or Payslip(run=run, employee=emp, base_amount=0, pay_type=emp.pay_profile.pay_type)
        if slip.pk is None:
            slip.save()
        data = _compute_for(emp, run, _adjustments(slip))
        _apply(slip, data)
        keep.add(slip.pk)
    run.slips.exclude(pk__in=keep).delete()
    if created:
        audit(user, location, "payroll_generated", run, month=month.isoformat())
    return run


def blockers(run):
    """Why this run cannot be finalized yet (empty list = it can)."""
    out = []
    end = calc.month_end(run.month)
    if today() <= end:
        out.append(f"The month is not over yet (it ends on {end}).")
    slips = list(run.slips.select_related("employee"))
    if not slips:
        out.append("There is nobody to pay. Give your employees a pay profile first.")
    for s in slips:
        if s.unmarked_days:
            out.append(f"{s.employee.name}: {s.unmarked_days} day(s) have no attendance recorded. Mark them present, absent or on leave.")
        open_n = AttendanceRecord.objects.filter(employee=s.employee, date__range=(run.month, end), status="PRESENT",
                                                 check_out__isnull=True, date__lt=today()).count()
        if open_n:
            out.append(f"{s.employee.name}: {open_n} day(s) have a check-in but no check-out.")
    return out


@transaction.atomic
def finalize_run(run, user):
    run = PayrollRun.objects.select_for_update().get(pk=run.pk)
    if run.status == PayrollRun.Status.FINALIZED:
        raise PayrollError("This month is already finalized.")
    generate_run(run.location, run.month, user)               # fresh numbers from the latest attendance
    problems = blockers(run)
    if problems:
        raise PayrollError({"blockers": problems, "detail": "Fix these first: " + " ".join(problems[:3]) + (" …" if len(problems) > 3 else "")})
    on = today()
    for slip in run.slips.select_related("employee"):
        for item in slip.advance_plan:
            adv = Advance.objects.select_for_update().get(pk=item["advance"])
            AdvanceRepayment.objects.create(advance=adv, amount=Decimal(str(item["amount"])), date=on, payslip=slip, note=f"Salary {run.month:%b %Y}", created_by=user)
            if adv.balance <= 0:
                adv.status = Advance.Status.CLEARED
                adv.save(update_fields=["status"])
        slip.status = Payslip.Status.UNPAID
        slip.save(update_fields=["status"])
    run.status, run.finalized_by, run.finalized_at = PayrollRun.Status.FINALIZED, user, timezone.now()
    run.save()
    totals = run.slips.aggregate(n=Count("id"), g=Sum("gross"), t=Sum("net"))
    audit(user, run.location, "payroll_finalized", run, month=run.month.isoformat(), employees=totals["n"], gross=totals["g"], net=totals["t"])
    return run


@transaction.atomic
def reopen_run(run, user, reason):
    run = PayrollRun.objects.select_for_update().get(pk=run.pk)
    reason = (reason or "").strip()
    if len(reason) < 3:
        raise PayrollError("Say why you are reopening this month.")
    if run.status != PayrollRun.Status.FINALIZED:
        raise PayrollError("This month is not finalized.")
    if run.slips.filter(status=Payslip.Status.PAID).exists():
        raise PayrollError("Some salaries are already paid, so this month cannot be reopened.")
    for rep in AdvanceRepayment.objects.filter(payslip__run=run).select_related("advance"):
        adv = rep.advance
        rep.delete()
        if adv.status == Advance.Status.CLEARED and adv.balance > 0:
            adv.status = Advance.Status.ACTIVE
            adv.save(update_fields=["status"])
    run.slips.update(status=Payslip.Status.DRAFT)
    run.status, run.finalized_by, run.finalized_at = PayrollRun.Status.DRAFT, None, None
    run.save()
    audit(user, run.location, "payroll_reopened", run, month=run.month.isoformat(), reason=reason)
    return run


# ───────────────────────── adjustments ─────────────────────────
@transaction.atomic
def add_adjustment(slip, kind, label, amount, user):
    if slip.run.status != PayrollRun.Status.DRAFT:
        raise PayrollError("This month is finalized. Reopen it to change a payslip.")
    if kind not in PayslipAdjustment.Kind.values:
        raise PayrollError("Choose BONUS or DEDUCTION.")
    label = (label or "").strip()
    if len(label) < 2:
        raise PayrollError("Give it a name, e.g. Eid bonus.")
    amount = cash.q2(amount)
    if amount <= 0:
        raise PayrollError("The amount must be more than zero.")
    adj = PayslipAdjustment.objects.create(payslip=slip, kind=kind, label=label[:100], amount=amount, created_by=user)
    _apply(slip, _compute_for(slip.employee, slip.run, _adjustments(slip)))
    audit(user, slip.run.location, "payroll_adjustment", slip, employee=slip.employee.name, kind=kind, label=label, amount=amount)
    return adj


@transaction.atomic
def remove_adjustment(adj, user):
    slip = adj.payslip
    if slip.run.status != PayrollRun.Status.DRAFT:
        raise PayrollError("This month is finalized. Reopen it to change a payslip.")
    audit(user, slip.run.location, "payroll_adjustment_removed", slip, employee=slip.employee.name, label=adj.label, amount=adj.amount)
    adj.delete()
    _apply(slip, _compute_for(slip.employee, slip.run, _adjustments(slip)))


# ───────────────────────── paying ─────────────────────────
@transaction.atomic
def pay_slip(slip, user, method, reference="", from_drawer=False):
    slip = Payslip.objects.select_for_update().select_related("run", "employee").get(pk=slip.pk)
    method = str(method or "").upper()
    if method not in METHODS:
        raise PayrollError(f"Pay by one of: {', '.join(METHODS)}.")
    if slip.run.status != PayrollRun.Status.FINALIZED:
        raise PayrollError("Finalize the month before paying salaries.")
    if slip.status != Payslip.Status.UNPAID:
        raise PayrollError("This salary is already paid." if slip.status == Payslip.Status.PAID else "This payslip is not ready to pay.")
    if from_drawer:
        if method != "CASH":
            raise PayrollError("Only cash can come out of the cash drawer.")
        shift = cash.current_shift(user, slip.run.location_id)
        if shift is None:
            raise PayrollError("Open your shift first to pay salary from the cash drawer.")
        if slip.net > 0:
            cash.add_movement(shift, user, "EXPENSE", slip.net, f"Salary {slip.employee.name} {slip.run.month:%b %Y}", "salary")
    slip.status, slip.paid_at, slip.paid_by = Payslip.Status.PAID, timezone.now(), user
    slip.paid_method, slip.paid_reference = METHODS[method], (reference or "")[:100]
    slip.save()
    audit(user, slip.run.location, "salary_paid", slip, employee=slip.employee.name, month=slip.run.month.isoformat(), net=slip.net, method=slip.paid_method, from_drawer=from_drawer)
    return slip


@transaction.atomic
def pay_all(run, user, method, reference=""):
    paid = [pay_slip(s, user, method, reference) for s in run.slips.filter(status=Payslip.Status.UNPAID)]
    if not paid:
        raise PayrollError("There is nothing left to pay.")
    return paid


# ───────────────────────── pay profile ─────────────────────────
def profile_snapshot(p):
    return {"pay_type": p.pay_type, "base_amount": str(p.base_amount), "month_basis": p.month_basis, "fixed_allowance": str(p.fixed_allowance),
            "fixed_deduction": str(p.fixed_deduction), "late_rule": p.late_rule}
