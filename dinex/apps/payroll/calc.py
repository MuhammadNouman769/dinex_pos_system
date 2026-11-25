"""
The salary maths. One pure function: attendance numbers + pay profile in, a full payslip breakdown out.

Rates
  MONTHLY  daily = salary / month basis (30, 26 or the real days of the month); hourly = daily / hours per day
  DAILY    daily = the wage;                 hourly = wage / hours per day
  HOURLY   hourly = the rate;                daily = rate x hours per day
  hours per day = the profile's standard hours, else the duty hours, else 8

Earnings
  MONTHLY  basic = salary (pro-rated by calendar days if the person joined during the month)
  DAILY    basic = wage x (days worked + paid-leave days [if paid] + weekly offs [if paid])
  HOURLY   basic = rate x regular hours (+ paid-leave days x hours per day [if paid])
  overtime = overtime hours x hourly rate x the duty's overtime multiplier (a day off worked is all overtime)
  + allowance + delivery commission (riders) + bonuses
Deductions
  MONTHLY  absent days x penalty days x daily rate; unpaid leave days x daily rate (daily / hourly staff are simply not paid for those days)
  lateness (any type): none, or the late minutes at the hourly rate, or every N late days = D days of pay
  + fixed deduction + one-off deductions + advance installments (never more than what is left, so net pay is never negative)
"""
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from apps.payroll.models import PayProfile

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
P = PayProfile


def q(x):
    return Decimal(x).quantize(CENT, ROUND_HALF_UP)


def month_end(first):
    return date(first.year, first.month, monthrange(first.year, first.month)[1])


def hours_per_day(prof, sched):
    if prof.standard_hours:
        return Decimal(prof.standard_hours)
    if sched is not None:
        s, e = sched.start_time, sched.end_time
        minutes = ((e.hour * 60 + e.minute) - (s.hour * 60 + s.minute)) % (24 * 60)
        if minutes:
            return Decimal(minutes) / 60
    return Decimal(8)


def compute(emp, prof, start, end, row, deliveries, adjustments, advances):
    """
    row: the employee's attendance report row for [start, end].
    adjustments: [(kind, label, amount)] ; advances: [(id, reason, installment, balance)] oldest first.
    Returns a dict of numbers, display `lines`, `warnings` and the `advance_plan`.
    """
    cal_days = (end - start).days + 1
    divisor = Decimal({P.MonthBasis.D30: 30, P.MonthBasis.D26: 26, P.MonthBasis.CALENDAR: cal_days}[prof.month_basis])
    sched = row["schedule"]
    hpd = hours_per_day(prof, sched)
    base = Decimal(prof.base_amount)

    if prof.pay_type == P.PayType.MONTHLY:
        daily = base / divisor
        hourly = daily / hpd
    elif prof.pay_type == P.PayType.DAILY:
        daily, hourly = base, base / hpd
    else:
        hourly, daily = base, base * hpd

    joined = emp.joining_date if emp.joining_date and emp.joining_date > start else start
    eligible_days = max(0, (end - joined).days + 1)
    prorate = min(Decimal(eligible_days) / Decimal(cal_days), Decimal(1))

    r = row
    absent_days = r["absent_days"]
    lines, warnings = [], []
    earn = lambda label, amount, note="": lines.append({"kind": "earning", "label": label, "amount": float(amount), "note": note}) if amount else None
    ded = lambda label, amount, note="": lines.append({"kind": "deduction", "label": label, "amount": float(amount), "note": note}) if amount else None

    # ---- earnings
    if prof.pay_type == P.PayType.MONTHLY:
        basic = q(base * prorate)
        note = f"Rs {base:,.0f} a month" + (f", pro-rated for {eligible_days} of {cal_days} days (joined {joined})" if prorate < 1 else "")
        earn("Basic salary", basic, note)
    elif prof.pay_type == P.PayType.DAILY:
        worked_days = r["present_days"] - r["off_days_worked"]
        paid_days = worked_days + (r["leave_paid"] if prof.pay_paid_leave else 0) + (r["weekly_off_days"] if prof.pay_weekly_off else 0)
        basic = q(daily * paid_days)
        earn("Daily wages", basic, f"{paid_days} paid days × Rs {daily:,.0f}")
    else:
        regular_minutes = max(0, r["worked_minutes"] - r["overtime_minutes"])
        basic = q(hourly * Decimal(regular_minutes) / 60 + (hourly * hpd * r["leave_paid"] if prof.pay_paid_leave else 0))
        earn("Hourly pay", basic, f"{regular_minutes / 60:.1f} h × Rs {hourly:,.0f}" + (f" + {r['leave_paid']} paid leave day(s)" if r["leave_paid"] and prof.pay_paid_leave else ""))

    mult = Decimal(sched.overtime_multiplier) if sched is not None else Decimal("1.5")
    overtime_pay = q(hourly * Decimal(r["overtime_minutes"]) / 60 * mult) if prof.overtime_enabled else ZERO
    earn("Overtime", overtime_pay, f"{r['overtime_minutes'] / 60:.1f} h × Rs {hourly:,.0f} × {mult}")
    if r["overtime_minutes"] and sched is None:
        warnings.append("No duty hours are set, so overtime is paid at 1.5× the hourly rate.")
    allowance = q(Decimal(prof.fixed_allowance) * prorate)
    earn("Allowance", allowance)
    commission = q(Decimal(deliveries) * Decimal(emp.delivery_commission))
    earn("Delivery commission", commission, f"{deliveries} deliveries × Rs {emp.delivery_commission:,.0f}")
    bonus = ZERO
    for kind, label, amount in adjustments:
        if kind == "BONUS":
            bonus += Decimal(amount); earn(f"Bonus: {label}", Decimal(amount))
    gross = basic + overtime_pay + allowance + commission + bonus

    # ---- deductions
    absent_ded = leave_ded = ZERO
    if prof.pay_type == P.PayType.MONTHLY:
        absent_ded = q(daily * Decimal(absent_days) * Decimal(prof.absent_penalty_days))
        leave_ded = q(daily * r["leave_unpaid"])
    ded("Absent", absent_ded, f"{absent_days} day(s) × {prof.absent_penalty_days} × Rs {daily:,.0f}")
    ded("Unpaid leave", leave_ded, f"{r['leave_unpaid']} day(s) × Rs {daily:,.0f}")
    late_ded = ZERO
    if prof.late_rule == P.LateRule.MINUTES:
        late_ded = q(hourly * Decimal(r["late_minutes"]) / 60)
        ded("Late arrivals", late_ded, f"{r['late_minutes']} min at Rs {hourly:,.0f}/h")
    elif prof.late_rule == P.LateRule.COUNT and prof.late_every:
        steps = r["late_days"] // prof.late_every
        late_ded = q(daily * Decimal(steps) * Decimal(prof.late_deduct_days))
        ded("Late arrivals", late_ded, f"{r['late_days']} late days: {steps} × {prof.late_deduct_days} day(s)")
    fixed = q(Decimal(prof.fixed_deduction) * prorate)
    ded("Fixed deduction", fixed)
    other = ZERO
    for kind, label, amount in adjustments:
        if kind == "DEDUCTION":
            other += Decimal(amount); ded(label, Decimal(amount))
    before_advances = absent_ded + leave_ded + late_ded + fixed + other

    room = max(ZERO, gross - before_advances)
    plan, advance_ded = [], ZERO
    for adv_id, reason, installment, balance in advances:
        take = min(Decimal(installment), Decimal(balance), room - advance_ded)
        if take > 0:
            take = q(take); plan.append({"advance": adv_id, "amount": float(take)}); advance_ded += take
            ded("Advance repayment", take, reason or "")
    deductions = before_advances + advance_ded
    net = q(max(ZERO, gross - deductions))
    if before_advances > gross:
        warnings.append("Deductions are more than the earnings this month, so net pay is 0.")
    if advances and advance_ded < sum(min(Decimal(i), Decimal(b)) for _, _, i, b in advances):
        warnings.append("Not enough pay to take the full advance installment this month. The rest stays owed.")

    if r["unmarked_days"]:
        warnings.append(f"{r['unmarked_days']} day(s) have no attendance recorded (counted as absent until you mark them).")
    if r["open_records"]:
        warnings.append(f"{r['open_records']} day(s) have a check-in but no check-out (hours unknown).")
    return {
        "daily_rate": q(daily), "hourly_rate": q(hourly),
        "scheduled_days": r["scheduled_days"], "present_days": r["present_days"], "absent_days": absent_days, "unmarked_days": r["unmarked_days"],
        "leave_paid": r["leave_paid"], "leave_unpaid": r["leave_unpaid"], "weekly_off_days": r["weekly_off_days"], "late_days": r["late_days"],
        "late_minutes": r["late_minutes"], "worked_minutes": r["worked_minutes"], "overtime_minutes": r["overtime_minutes"], "deliveries": deliveries,
        "basic_pay": basic, "overtime_pay": overtime_pay, "allowance": allowance, "commission": commission, "bonus": q(bonus), "gross": q(gross),
        "absent_deduction": absent_ded, "leave_deduction": leave_ded, "late_deduction": late_ded, "fixed_deduction": fixed,
        "other_deduction": q(other), "advance_deduction": q(advance_ded), "deductions": q(deductions), "net": net,
        "lines": lines, "warnings": warnings, "advance_plan": plan,
        "_open_records": r["open_records"],
    }
