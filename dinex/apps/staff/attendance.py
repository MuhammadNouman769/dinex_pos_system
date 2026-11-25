"""
Attendance, duty hours and overtime.

How the numbers are worked out (all in minutes, against the employee's WorkSchedule):
  late            arrived after duty start + grace          -> minutes since the duty start (not just the excess)
  early leave     left before duty end - grace              -> minutes before the duty end
  overtime        stayed after duty end, at least `min_overtime` -> minutes after the duty end
  off-day work    came in on the weekly off                 -> the whole time worked is overtime (no late / early)
  no schedule     only the time worked is recorded
Duty that ends before it starts (e.g. 16:00-01:00) finishes after midnight; the work day is the date it started.
"""
import hashlib
import hmac
import re
from datetime import date, datetime, time, timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.staff.models import AttendanceRecord as AR, Employee, WorkSchedule

PRESENT, ABSENT, LEAVE = AR.Status.PRESENT, AR.Status.ABSENT, AR.Status.LEAVE
STALE_HOURS = 20            # an open check-in older than this was forgotten
MAX_PIN_FAILS = 5
LOCK_SECONDS = 300
FUTURE_SLACK = timedelta(minutes=5)
LATE_ENTRY_AFTER = timedelta(minutes=10)


def now():
    """Wrapped so tests can control the clock."""
    return timezone.now()


def local_date(dt):
    return timezone.localtime(dt).date()


def minutes(a, b):
    return max(0, int((b - a).total_seconds() // 60))


# ───────────────────────── duty window and metrics ─────────────────────────
def window(sched, day):
    """(duty start, duty end) as aware datetimes for the work day `day`."""
    tz = timezone.get_current_timezone()
    start = timezone.make_aware(datetime.combine(day, sched.start_time), tz)
    end = timezone.make_aware(datetime.combine(day, sched.end_time), tz)
    if sched.end_time <= sched.start_time:
        end += timedelta(days=1)
    return start, end


def recalc(rec, sched):
    """Work out worked / late / early / overtime for a record from its times and the schedule."""
    rec.worked_minutes = rec.late_minutes = rec.early_leave_minutes = rec.overtime_minutes = 0
    rec.on_off_day = False
    if rec.status != PRESENT or rec.check_in is None:
        return rec
    rec.on_off_day = bool(sched and rec.date.weekday() in (sched.weekly_off or []))
    if rec.check_out is not None:
        rec.worked_minutes = minutes(rec.check_in, rec.check_out)
    if sched is None:
        return rec
    start, end = window(sched, rec.date)
    if rec.on_off_day:
        rec.overtime_minutes = rec.worked_minutes
        return rec
    if rec.check_in > start + timedelta(minutes=sched.grace_minutes):
        rec.late_minutes = minutes(start, rec.check_in)
    if rec.check_out is not None:
        if rec.check_out < end - timedelta(minutes=sched.grace_minutes):
            rec.early_leave_minutes = minutes(rec.check_out, end)
        elif rec.check_out - end >= timedelta(minutes=sched.min_overtime_minutes):
            rec.overtime_minutes = minutes(end, rec.check_out)
    return rec


def schedule_of(emp):
    try:
        return emp.schedule
    except WorkSchedule.DoesNotExist:
        return None


def day_state(emp, sched, rec, day, at):
    """What to show for one person on one day."""
    if rec is not None:
        if rec.status == ABSENT:
            return "ABSENT"
        if rec.status == LEAVE:
            return "LEAVE"
        return "ON_DUTY" if rec.check_out is None else "DONE"
    if emp.joining_date and day < emp.joining_date:
        return "NOT_JOINED"
    if sched is None:
        return "NO_SCHEDULE"
    if day.weekday() in (sched.weekly_off or []):
        return "OFF"
    today = local_date(at)
    if day > today:
        return "UPCOMING"
    start, end = window(sched, day)
    if day == today:
        if at < start:
            return "UPCOMING"
        return "ABSENT_DERIVED" if at >= end else "NOT_IN"
    return "ABSENT_DERIVED"


# ───────────────────────── PINs ─────────────────────────
def pin_digest(employee_id, pin):
    """
    PINs are 4-6 digits, so a slow password hash adds little (anyone can try all 10^6) and would make the kiosk
    crawl: identifying a PIN means testing it against everyone at the branch. We store a fast keyed hash instead
    (HMAC-SHA256 over the employee id with the server's SECRET_KEY). The real protection is the lockout below.
    """
    mac = hmac.new(settings.SECRET_KEY.encode(), f"pin:{employee_id}:{pin}".encode(), hashlib.sha256)
    return "hmac$" + mac.hexdigest()


def pin_matches(emp, pin):
    return bool(emp.pin_hash) and hmac.compare_digest(emp.pin_hash, pin_digest(emp.id, pin))


def set_pin(emp, pin):
    """pin=None removes it. The PIN must be unique among the branch's active employees (the PIN alone identifies a person)."""
    if pin is None:
        emp.pin_hash = ""
    else:
        pin = str(pin).strip()
        if not re.fullmatch(r"\d{4,6}", pin):
            raise ValidationError({"pin": "A PIN is 4 to 6 digits."})
        for other in Employee.objects.filter(location_id=emp.location_id, is_active=True).exclude(pk=emp.pk).exclude(pin_hash=""):
            if pin_matches(other, pin):
                raise ValidationError({"pin": "Another person at this branch already uses this PIN. Choose a different one."})
        emp.pin_hash = pin_digest(emp.id, pin)
    emp.save(update_fields=["pin_hash", "updated_at"])


def identify(location_id, pin):
    for emp in Employee.objects.filter(location_id=location_id, is_active=True).exclude(pin_hash="").select_related("location"):
        if pin_matches(emp, pin):
            return emp
    return None


def _lock_key(location_id):
    return f"kiosk-fails:{location_id}"


def kiosk_punch(location_id, pin, by):
    key = _lock_key(location_id)
    if cache.get(key, 0) >= MAX_PIN_FAILS:
        raise ValidationError({"detail": "Too many wrong PINs. The kiosk is locked for a few minutes."})
    emp = identify(location_id, str(pin).strip()) if re.fullmatch(r"\d{4,6}", str(pin).strip()) else None
    if emp is None:
        fails = cache.get(key, 0) + 1
        cache.set(key, fails, LOCK_SECONDS)
        left = MAX_PIN_FAILS - fails
        raise ValidationError({"detail": "Wrong PIN." + (f" {left} tries left." if 0 < left <= 2 else "")})
    cache.delete(key)
    return punch(emp, "AUTO", now(), by, source=AR.Source.KIOSK)


# ───────────────────────── punching ─────────────────────────
def _open_record(emp):
    return AR.objects.filter(employee=emp, status=PRESENT, check_out__isnull=True, check_in__isnull=False).order_by("-check_in").first()


def _auto_close(rec, sched):
    """A forgotten check-out is closed at the end of duty (or 8 hours after check-in without a schedule)."""
    rec.check_out = window(sched, rec.date)[1] if sched else rec.check_in + timedelta(hours=8)
    if rec.check_out < rec.check_in:
        rec.check_out = rec.check_in
    rec.auto_closed = True
    recalc(rec, sched)
    rec.save()


def punch(emp, action, when, by, source=AR.Source.MANAGER, note=""):
    """action: IN, OUT or AUTO (toggle). Returns (action_done, record)."""
    if not emp.is_active:
        raise ValidationError({"detail": f"{emp.name} is not an active employee."})
    at = now()
    if when > at + FUTURE_SLACK:
        raise ValidationError({"detail": "That time is in the future."})
    sched = schedule_of(emp)
    user = by if getattr(by, "is_authenticated", False) else None
    open_rec = _open_record(emp)
    if open_rec is not None and when - open_rec.check_in > timedelta(hours=STALE_HOURS):   # measured to the time being punched, so late entries work
        _auto_close(open_rec, sched)
        open_rec = None
    if action not in ("IN", "OUT", "AUTO"):
        raise ValidationError({"action": "Use IN or OUT."})

    if open_rec is not None and action in ("OUT", "AUTO"):
        if when <= open_rec.check_in:
            raise ValidationError({"detail": "Check-out must be after the check-in."})
        open_rec.check_out = when
        recalc(open_rec, sched)
        open_rec.marked_by = user
        open_rec.save()
        return "OUT", open_rec
    if action == "OUT":
        raise ValidationError({"detail": f"{emp.name} has not checked in."})
    if open_rec is not None:
        raise ValidationError({"detail": f"{emp.name} is already checked in."})

    day = local_date(when)
    existing = AR.objects.filter(employee=emp, date=day).first()
    if existing is not None:
        if existing.status == PRESENT:
            raise ValidationError({"detail": f"{emp.name} already checked in and out on {day}. A manager can correct it."})
        raise ValidationError({"detail": f"{emp.name} is marked {existing.get_status_display().lower()} for {day}. A manager must change that first."})
    rec = AR(employee=emp, date=day, status=PRESENT, check_in=when, source=source, note=note[:255], marked_by=user)
    recalc(rec, sched)
    rec.save()
    return "IN", rec


# ───────────────────────── absent / leave / corrections ─────────────────────────
def mark(emp, day, status, paid, note, by):
    if status not in (ABSENT, LEAVE):
        raise ValidationError({"status": "Use ABSENT or LEAVE. To record a check-in use the punch."})
    if status == ABSENT and day > local_date(now()):
        raise ValidationError({"date": "You cannot mark someone absent in the future."})
    rec = AR.objects.filter(employee=emp, date=day).first()
    if rec is not None and rec.status == PRESENT:
        raise ValidationError({"detail": "This day already has check-in times. Edit the record instead."})
    if rec is None:
        rec = AR(employee=emp, date=day)
    rec.status, rec.paid_leave = status, bool(paid) and status == LEAVE
    rec.check_in = rec.check_out = None
    rec.source, rec.note, rec.marked_by = AR.Source.MANAGER, (note or "")[:255], by
    recalc(rec, None)
    rec.save()
    return rec


def snapshot(rec):
    local = lambda dt: timezone.localtime(dt).isoformat() if dt else None          # the audit log reads in local (Pakistan) time
    return {"status": rec.status, "paid_leave": rec.paid_leave, "check_in": local(rec.check_in), "check_out": local(rec.check_out)}


def edit(rec, data, reason, by):
    reason = (reason or "").strip()
    if len(reason) < 3:
        raise ValidationError({"reason": "Say why you are changing this record."})
    status = data.get("status", rec.status)
    if status not in (PRESENT, ABSENT, LEAVE):
        raise ValidationError({"status": "Unknown status."})
    check_in = data["check_in"] if "check_in" in data else rec.check_in
    check_out = data["check_out"] if "check_out" in data else rec.check_out
    if status == PRESENT:
        if check_in is None:
            raise ValidationError({"check_in": "A present day needs a check-in time."})
        if check_out is not None and check_out <= check_in:
            raise ValidationError({"check_out": "Check-out must be after the check-in."})
        if check_in > now() + FUTURE_SLACK or (check_out and check_out > now() + FUTURE_SLACK):
            raise ValidationError({"detail": "That time is in the future."})
    else:
        check_in = check_out = None
    rec.status = status
    rec.paid_leave = bool(data.get("paid_leave", rec.paid_leave)) and status == LEAVE
    rec.check_in, rec.check_out = check_in, check_out
    rec.auto_closed = False if check_out else rec.auto_closed
    if "note" in data:
        rec.note = (data["note"] or "")[:255]
    rec.marked_by = by
    recalc(rec, schedule_of(rec.employee))
    rec.save()
    return rec


# ───────────────────────── board and report ─────────────────────────
def board(location, day, at=None):
    at = at or now()
    emps = list(Employee.objects.filter(location=location, is_active=True).select_related("schedule").order_by("name"))
    recs = {r.employee_id: r for r in AR.objects.filter(employee__in=emps, date=day)}
    rows, counts = [], {}
    for e in emps:
        sched, rec = schedule_of(e), recs.get(e.id)
        state = day_state(e, sched, rec, day, at)
        counts[state] = counts.get(state, 0) + 1
        rows.append({"employee": e, "schedule": sched, "state": state, "record": rec})
    return {"date": day, "rows": rows, "counts": counts}


SCHEDULED_STATES = {"DONE", "ON_DUTY", "ABSENT", "ABSENT_DERIVED", "LEAVE", "NOT_IN"}


def report(location, start, end, employee=None, at=None):
    at = at or now()
    qs = Employee.objects.filter(location=location).select_related("schedule")
    emps = [employee] if employee is not None else [e for e in qs.order_by("name") if e.is_active or AR.objects.filter(employee=e, date__range=(start, end)).exists()]
    recs = {}
    for r in AR.objects.filter(employee__in=emps, date__range=(start, end)).order_by("date"):
        recs.setdefault(r.employee_id, {})[r.date] = r
    rows = []
    for e in emps:
        sched, mine = schedule_of(e), recs.get(e.id, {})
        row = {"employee": e, "schedule": sched, "scheduled_days": 0, "present_days": 0, "late_days": 0, "late_minutes": 0,
               "early_leave_days": 0, "absent_days": 0, "leave_paid": 0, "leave_unpaid": 0, "worked_minutes": 0,
               "overtime_minutes": 0, "off_days_worked": 0, "missing_checkouts": 0,
               "unmarked_days": 0, "weekly_off_days": 0, "open_records": 0}
        day = start
        while day <= end:
            rec = mine.get(day)
            state = day_state(e, sched, rec, day, at)
            if state in SCHEDULED_STATES and not (rec is not None and rec.on_off_day):      # working on the day off is extra, not scheduled
                row["scheduled_days"] += 1
            if state in ("ABSENT", "ABSENT_DERIVED"):
                row["absent_days"] += 1
            if state == "ABSENT_DERIVED":
                row["unmarked_days"] += 1                      # nobody recorded this day at all
            if state == "OFF":
                row["weekly_off_days"] += 1
            if state == "LEAVE":
                row["leave_paid" if rec.paid_leave else "leave_unpaid"] += 1
            if rec is not None and rec.status == PRESENT:
                row["present_days"] += 1
                row["worked_minutes"] += rec.worked_minutes
                row["overtime_minutes"] += rec.overtime_minutes
                if rec.late_minutes:
                    row["late_days"] += 1; row["late_minutes"] += rec.late_minutes
                if rec.early_leave_minutes:
                    row["early_leave_days"] += 1
                if rec.on_off_day:
                    row["off_days_worked"] += 1
                if rec.auto_closed or (rec.check_out is None and day < local_date(at)):
                    row["missing_checkouts"] += 1
                if rec.check_out is None and day < local_date(at):
                    row["open_records"] += 1                   # a finished day that never got a check-out: hours are unknown
            day += timedelta(days=1)
        row["records"] = [mine[d] for d in sorted(mine)] if employee is not None else None
        rows.append(row)
    return rows
