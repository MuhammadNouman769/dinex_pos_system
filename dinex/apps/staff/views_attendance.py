from datetime import date, datetime, timedelta

from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework import status as http
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.cash.services import audit
from apps.organizations.models import Location
from apps.staff import attendance as att
from apps.staff.models import AttendanceRecord as AR, Employee, Role, WorkSchedule
from apps.staff.views import _employee, _org
from apps.utils.helpers import is_manager_or_owner, location_model_scope, location_scope
from apps.utils.permissions import CanOperatePOS


# ───────────────────────── helpers ─────────────────────────
def _location(request, value):
    try:
        pk = int(value)
    except (TypeError, ValueError):
        raise ValidationError({"location": "Choose a branch."})
    return get_object_or_404(Location, pk=pk, **location_model_scope(request, _org(request)))


def _managed(request, location):
    if not is_manager_or_owner(request, location):
        raise PermissionDenied("Only the owner or a branch manager can do this.")


def _day(value, default=None):
    if value in (None, ""):
        return default
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({"date": "Use the format YYYY-MM-DD."})


def _when(value, default=None):
    """ISO date-time. A value without a time zone is local (Pakistan) time."""
    if value in (None, ""):
        return default
    dt = parse_datetime(str(value))
    if dt is None:
        raise ValidationError({"time": "Use the format YYYY-MM-DDTHH:MM."})
    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt


def _t(value, field):
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(str(value), fmt).time()
        except ValueError:
            continue
    raise ValidationError({field: "Use the format HH:MM."})


def schedule_dict(s):
    if s is None:
        return None
    return {"start_time": s.start_time.strftime("%H:%M"), "end_time": s.end_time.strftime("%H:%M"), "weekly_off": list(s.weekly_off or []),
            "grace_minutes": s.grace_minutes, "min_overtime_minutes": s.min_overtime_minutes,
            "overtime_multiplier": float(s.overtime_multiplier), "overnight": s.overnight}


def record_dict(r):
    if r is None:
        return None
    return {"id": r.id, "date": r.date, "status": r.status, "paid_leave": r.paid_leave, "check_in": r.check_in, "check_out": r.check_out,
            "source": r.source, "worked_minutes": r.worked_minutes, "late_minutes": r.late_minutes, "early_leave_minutes": r.early_leave_minutes,
            "overtime_minutes": r.overtime_minutes, "on_off_day": r.on_off_day, "auto_closed": r.auto_closed, "note": r.note}


def brief(e):
    return {"id": e.id, "code": e.code, "name": e.name, "role": e.role, "role_display": e.get_role_display(), "has_pin": bool(e.pin_hash), "is_active": e.is_active}


def parse_schedule(data):
    start, end = _t(data.get("start_time"), "start_time"), _t(data.get("end_time"), "end_time")
    if start == end:
        raise ValidationError({"end_time": "Duty cannot start and end at the same time."})
    off = data.get("weekly_off", [])
    if not isinstance(off, list) or any(not isinstance(d, int) or isinstance(d, bool) or not 0 <= d <= 6 for d in off):
        raise ValidationError({"weekly_off": "A list of days from 0 (Monday) to 6 (Sunday)."})
    out = {"start_time": start, "end_time": end, "weekly_off": sorted(set(off))}
    for key, lo, hi, cast in (("grace_minutes", 0, 120, int), ("min_overtime_minutes", 0, 240, int), ("overtime_multiplier", 1, 5, float)):
        if key in data and data[key] not in (None, ""):
            try:
                v = cast(data[key])
            except (TypeError, ValueError):
                raise ValidationError({key: "Enter a number."})
            if not lo <= v <= hi:
                raise ValidationError({key: f"Between {lo} and {hi}."})
            out[key] = v
    return out


# ───────────────────────── duty hours and PIN ─────────────────────────
class ScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        return Response({"schedule": schedule_dict(att.schedule_of(_employee(request, pk)))})

    def put(self, request, pk):
        emp = _employee(request, pk)
        _managed(request, emp.location)
        WorkSchedule.objects.update_or_create(employee=emp, defaults=parse_schedule(request.data))
        return Response({"schedule": schedule_dict(att.schedule_of(Employee.objects.select_related("schedule").get(pk=emp.pk)))})

    def delete(self, request, pk):
        emp = _employee(request, pk)
        _managed(request, emp.location)
        WorkSchedule.objects.filter(employee=emp).delete()
        return Response(status=http.HTTP_204_NO_CONTENT)


class BulkScheduleView(APIView):
    """Same duty hours for a whole group, e.g. every waiter at the branch."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        location = _location(request, request.data.get("location"))
        _managed(request, location)
        values = parse_schedule(request.data)
        qs = Employee.objects.filter(location=location, is_active=True)
        if request.data.get("role"):
            if request.data["role"] not in Role.values:
                raise ValidationError({"role": "Unknown role."})
            qs = qs.filter(role=request.data["role"])
        n = 0
        for emp in qs:
            WorkSchedule.objects.update_or_create(employee=emp, defaults=values)
            n += 1
        return Response({"updated": n})


class SetPinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        emp = _employee(request, pk)
        _managed(request, emp.location)
        if "pin" not in request.data or request.data["pin"] == "":
            # an empty box must never silently delete a PIN: removing needs an explicit null
            raise ValidationError({"pin": "Enter a PIN of 4 to 6 digits (or send null to remove it)."})
        att.set_pin(emp, request.data["pin"])
        return Response({"has_pin": bool(emp.pin_hash)})


# ───────────────────────── punching ─────────────────────────
class PunchView(APIView):
    """A manager checks someone in or out (optionally at an earlier time)."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        emp = _employee(request, request.data.get("employee"))
        _managed(request, emp.location)
        at = att.now()
        when = _when(request.data.get("time"), at)
        note = (request.data.get("note") or "").strip()
        late_entry = at - when > att.LATE_ENTRY_AFTER
        if late_entry and len(note) < 3:
            raise ValidationError({"note": "Say why this is entered later."})
        done, rec = att.punch(emp, request.data.get("action"), when, request.user, source=AR.Source.MANAGER, note=note)
        if late_entry:
            audit(request.user, emp.location, "attendance_backdated", rec, employee=emp.name, punch=done, time=when, note=note)
        return Response({"action": done, "record": record_dict(rec)}, status=http.HTTP_201_CREATED)


class KioskView(APIView):
    """The entrance tablet (logged in as a cashier / manager): the employee types only their PIN."""
    permission_classes = [IsAuthenticated, CanOperatePOS]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "kiosk"

    def post(self, request):
        location = _location(request, request.data.get("location"))
        done, rec = att.kiosk_punch(location.id, request.data.get("pin", ""), request.user)
        e = rec.employee
        return Response({"action": done, "employee": {"id": e.id, "name": e.name, "role": e.get_role_display()},
                         "time": rec.check_in if done == "IN" else rec.check_out, "late_minutes": rec.late_minutes,
                         "worked_minutes": rec.worked_minutes, "overtime_minutes": rec.overtime_minutes,
                         "early_leave_minutes": rec.early_leave_minutes})


class MarkView(APIView):
    """Absent or on leave (paid / unpaid) for a day."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        emp = _employee(request, request.data.get("employee"))
        _managed(request, emp.location)
        day = _day(request.data.get("date"))
        if day is None:
            raise ValidationError({"date": "Choose the day."})
        rec = att.mark(emp, day, request.data.get("status"), request.data.get("paid"), request.data.get("note"), request.user)
        audit(request.user, emp.location, "attendance_marked", rec, employee=emp.name, date=day, status=rec.status, paid=rec.paid_leave)
        return Response(record_dict(rec), status=http.HTTP_201_CREATED)


class RecordView(APIView):
    """Correct a record. Always needs a reason and is written to the audit log."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        rec = get_object_or_404(AR.objects.select_related("employee__location"), pk=pk, **location_scope(request, _org(request), "employee__location"))
        _managed(request, rec.employee.location)
        data = {}
        for key in ("check_in", "check_out"):
            if key in request.data:
                data[key] = _when(request.data[key])
        for key in ("status", "paid_leave", "note"):
            if key in request.data:
                data[key] = request.data[key]
        before = att.snapshot(rec)
        att.edit(rec, data, request.data.get("reason"), request.user)
        audit(request.user, rec.employee.location, "attendance_edited", rec, employee=rec.employee.name, date=rec.date,
              reason=request.data.get("reason"), old=before, new=att.snapshot(rec))
        return Response(record_dict(rec))


# ───────────────────────── board and report ─────────────────────────
class BoardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        location = _location(request, request.query_params.get("location"))
        _managed(request, location)
        at = att.now()
        day = _day(request.query_params.get("date"), att.local_date(at))
        b = att.board(location, day, at)
        return Response({"date": day, "location": location.id, "counts": b["counts"], "rows": [
            {"employee": brief(r["employee"]), "schedule": schedule_dict(r["schedule"]), "state": r["state"], "record": record_dict(r["record"])} for r in b["rows"]]})


class ReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        location = _location(request, request.query_params.get("location"))
        _managed(request, location)
        at = att.now()
        today = att.local_date(at)
        end = _day(request.query_params.get("to"), today)
        start = _day(request.query_params.get("from"), end.replace(day=1))
        if end < start:
            raise ValidationError({"to": "Must not be before the start date."})
        if (end - start).days > 366:
            raise ValidationError({"to": "Choose a range of at most one year."})
        employee = None
        if request.query_params.get("employee"):
            employee = _employee(request, request.query_params["employee"])
            if employee.location_id != location.id:
                raise ValidationError({"employee": "This employee works at another branch."})
        rows = att.report(location, start, end, employee, at)
        out = []
        for r in rows:
            item = {k: v for k, v in r.items() if k not in ("employee", "schedule", "records")}
            item.update(employee=brief(r["employee"]), schedule=schedule_dict(r["schedule"]),
                        records=[record_dict(x) for x in r["records"]] if r["records"] is not None else None)
            out.append(item)
        return Response({"from": start, "to": end, "location": location.id, "rows": out})
