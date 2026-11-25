from datetime import date
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from rest_framework import status as http
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cash.services import audit
from apps.catalog.utils import get_user_organization_id
from apps.organizations.models import Location
from apps.payroll import calc, services
from apps.payroll.models import Advance, PayProfile, PayrollRun, Payslip, PayslipAdjustment
from apps.staff.models import Employee
from apps.utils.helpers import get_accessible_location_ids, location_model_scope

P = PayProfile


def _owner(request):
    """Salaries are private: only the restaurant owner."""
    org = get_user_organization_id(request)
    if not org:
        raise PermissionDenied("User has no organization assigned.")
    if get_accessible_location_ids(request, org) is not None:
        raise PermissionDenied("Only the owner can see or change payroll.")
    return org


def _employee(org, pk):
    return get_object_or_404(Employee.objects.select_related("location", "schedule"), pk=pk, organization_id=org)


def _location(request, org, value):
    try:
        pk = int(value)
    except (TypeError, ValueError):
        raise ValidationError({"location": "Choose a branch."})
    return get_object_or_404(Location, pk=pk, **location_model_scope(request, org))


def _dec(data, key, default=None, lo=Decimal("0"), hi=None):
    if key not in data or data[key] in (None, ""):
        if default is None:
            raise ValidationError({key: "This field is required."})
        return default
    try:
        v = Decimal(str(data[key]))
    except InvalidOperation:
        raise ValidationError({key: "Enter a number."})
    if v < lo or (hi is not None and v > hi):
        raise ValidationError({key: f"Between {lo} and {hi if hi is not None else 'a large number'}."})
    return v


# ───────────────────────── serializers ─────────────────────────
def brief(e):
    return {"id": e.id, "code": e.code, "name": e.name, "role": e.role, "role_display": e.get_role_display(), "location": e.location_id,
            "location_name": e.location.name, "is_active": e.is_active}


def profile_dict(p):
    if p is None:
        return None
    return {"pay_type": p.pay_type, "base_amount": p.base_amount, "month_basis": p.month_basis, "standard_hours": p.standard_hours,
            "fixed_allowance": p.fixed_allowance, "fixed_deduction": p.fixed_deduction, "overtime_enabled": p.overtime_enabled,
            "absent_penalty_days": p.absent_penalty_days, "pay_paid_leave": p.pay_paid_leave, "pay_weekly_off": p.pay_weekly_off,
            "late_rule": p.late_rule, "late_every": p.late_every, "late_deduct_days": p.late_deduct_days, "notes": p.notes}


def advance_dict(a, with_repayments=False):
    d = {"id": a.id, "employee": brief(a.employee), "amount": a.amount, "installment": a.installment, "given_on": a.given_on, "reason": a.reason,
         "status": a.status, "repaid": a.repaid, "balance": a.balance if a.status == Advance.Status.ACTIVE else Decimal("0.00")}
    if with_repayments:
        d["repayments"] = [{"id": r.id, "amount": r.amount, "date": r.date, "note": r.note, "source": "PAYROLL" if r.payslip_id else "MANUAL"} for r in a.repayments.all()]
    return d


def slip_summary(s):
    return {"id": s.id, "employee": brief(s.employee), "pay_type": s.pay_type, "status": s.status, "gross": s.gross, "deductions": s.deductions, "net": s.net,
            "overtime_minutes": s.overtime_minutes, "unmarked_days": s.unmarked_days, "warnings": s.warnings, "paid_at": s.paid_at, "paid_method": s.paid_method}


def slip_full(s):
    d = slip_summary(s)
    d.update({f: getattr(s, f) for f in services.SLIP_FIELDS if f not in ("lines", "warnings")})
    d.update({"base_amount": s.base_amount, "lines": s.lines, "advance_plan": s.advance_plan, "paid_reference": s.paid_reference,
              "paid_by": s.paid_by.username if s.paid_by else None, "month": s.run.month, "run": s.run_id, "run_status": s.run.status,
              "location_name": s.run.location.name,
              "adjustments": [{"id": a.id, "kind": a.kind, "label": a.label, "amount": a.amount} for a in s.adjustments.all()]})
    return d


def run_summary(run):
    t = run.slips.aggregate(n=Count("id"), gross=Sum("gross"), ded=Sum("deductions"), net=Sum("net"))
    return {"id": run.id, "month": run.month, "location": run.location_id, "location_name": run.location.name, "status": run.status,
            "employees": t["n"] or 0, "gross": t["gross"] or Decimal("0"), "deductions": t["ded"] or Decimal("0"), "net": t["net"] or Decimal("0"),
            "paid": run.slips.filter(status=Payslip.Status.PAID).count(), "unpaid": run.slips.filter(status=Payslip.Status.UNPAID).count(),
            "unmarked": run.slips.filter(unmarked_days__gt=0).count(), "finalized_at": run.finalized_at}


def run_detail(run):
    out = run_summary(run)
    problems = services.blockers(run) if run.status == PayrollRun.Status.DRAFT else []
    out.update({"blockers": problems, "can_finalize": run.status == PayrollRun.Status.DRAFT and not problems,
                "slips": [slip_summary(s) for s in run.slips.select_related("employee__location")]})
    return out


# ───────────────────────── pay profiles ─────────────────────────
class ProfilesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _owner(request)
        qs = Employee.objects.filter(organization_id=org, is_active=True).select_related("location", "pay_profile", "schedule").order_by("location__name", "name")
        if request.query_params.get("location"):
            qs = qs.filter(location=_location(request, org, request.query_params["location"]))
        rows = []
        for e in qs:
            prof = getattr(e, "pay_profile", None)
            open_adv = sum((a.balance for a in e.advances.filter(status=Advance.Status.ACTIVE)), Decimal("0.00"))
            rows.append({"employee": brief(e), "profile": profile_dict(prof), "hours_per_day": calc.hours_per_day(prof, e.schedule if hasattr(e, "schedule") else None) if prof else None,
                         "advance_balance": open_adv})
        return Response(rows)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        e = _employee(_owner(request), pk)
        return Response({"employee": brief(e), "profile": profile_dict(getattr(e, "pay_profile", None))})

    def put(self, request, pk):
        org = _owner(request)
        e = _employee(org, pk)
        d = request.data
        pay_type, basis, rule = d.get("pay_type", P.PayType.MONTHLY), d.get("month_basis", P.MonthBasis.D30), d.get("late_rule", P.LateRule.NONE)
        if pay_type not in P.PayType.values:
            raise ValidationError({"pay_type": "Choose MONTHLY, DAILY or HOURLY."})
        if basis not in P.MonthBasis.values:
            raise ValidationError({"month_basis": "Choose 30, 26 or CALENDAR."})
        if rule not in P.LateRule.values:
            raise ValidationError({"late_rule": "Choose NONE, MINUTES or COUNT."})
        hours = _dec(d, "standard_hours", default=Decimal("0"), hi=Decimal("24"))
        values = {
            "pay_type": pay_type, "base_amount": _dec(d, "base_amount", hi=Decimal("100000000")), "month_basis": basis,
            "standard_hours": hours if hours > 0 else None,
            "fixed_allowance": _dec(d, "fixed_allowance", Decimal("0")), "fixed_deduction": _dec(d, "fixed_deduction", Decimal("0")),
            "overtime_enabled": bool(d.get("overtime_enabled", True)), "absent_penalty_days": _dec(d, "absent_penalty_days", Decimal("1"), hi=Decimal("5")),
            "pay_paid_leave": bool(d.get("pay_paid_leave", True)), "pay_weekly_off": bool(d.get("pay_weekly_off", False)),
            "late_rule": rule, "late_every": int(_dec(d, "late_every", Decimal("3"), lo=Decimal("1"), hi=Decimal("31"))),
            "late_deduct_days": _dec(d, "late_deduct_days", Decimal("0.5"), hi=Decimal("5")), "notes": str(d.get("notes", ""))[:255],
        }
        old = getattr(e, "pay_profile", None)
        before = services.profile_snapshot(old) if old else None
        prof, _ = P.objects.update_or_create(employee=e, defaults=values)
        prof.refresh_from_db()                      # numbers exactly as stored (35000.00, not 35000), so old and new compare cleanly
        audit(request.user, e.location, "pay_profile_changed", prof, employee=e.name, old=before, new=services.profile_snapshot(prof))
        return Response({"employee": brief(e), "profile": profile_dict(prof)})

    def delete(self, request, pk):
        e = _employee(_owner(request), pk)
        if Payslip.objects.filter(employee=e).exclude(run__status=PayrollRun.Status.DRAFT).exists():
            raise ValidationError({"detail": "This person already has finalized payslips, so the pay profile is kept."})
        P.objects.filter(employee=e).delete()
        return Response(status=http.HTTP_204_NO_CONTENT)


# ───────────────────────── runs ─────────────────────────
class RunsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _owner(request)
        qs = PayrollRun.objects.filter(location__organization_id=org).select_related("location")
        if request.query_params.get("location"):
            qs = qs.filter(location=_location(request, org, request.query_params["location"]))
        return Response([run_summary(r) for r in qs[:36]])

    def post(self, request):
        org = _owner(request)
        location = _location(request, org, request.data.get("location"))
        run = services.generate_run(location, services.parse_month(request.data.get("month")), request.user)
        return Response(run_detail(run), status=http.HTTP_201_CREATED)


def _run(org, pk):
    return get_object_or_404(PayrollRun.objects.select_related("location"), pk=pk, location__organization_id=org)


class RunView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        return Response(run_detail(_run(_owner(request), pk)))


class RunActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action):
        run = _run(_owner(request), pk)
        if action == "regenerate":
            services.generate_run(run.location, run.month, request.user)
        elif action == "finalize":
            services.finalize_run(run, request.user)
        elif action == "reopen":
            services.reopen_run(run, request.user, request.data.get("reason"))
        elif action == "pay-all":
            services.pay_all(run, request.user, request.data.get("method"), request.data.get("reference", ""))
        else:
            raise ValidationError({"detail": "Unknown action."})
        run.refresh_from_db()
        return Response(run_detail(run))


# ───────────────────────── payslips ─────────────────────────
def _slip(org, pk):
    return get_object_or_404(Payslip.objects.select_related("run__location", "employee__location", "employee__pay_profile", "paid_by"), pk=pk, run__location__organization_id=org)


class SlipView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        return Response(slip_full(_slip(_owner(request), pk)))


class SlipAdjustmentsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        slip = _slip(_owner(request), pk)
        services.add_adjustment(slip, request.data.get("kind"), request.data.get("label"), request.data.get("amount"), request.user)
        slip.refresh_from_db()
        return Response(slip_full(slip), status=http.HTTP_201_CREATED)


class AdjustmentView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        org = _owner(request)
        adj = get_object_or_404(PayslipAdjustment.objects.select_related("payslip__run__location", "payslip__employee"), pk=pk, payslip__run__location__organization_id=org)
        services.remove_adjustment(adj, request.user)
        return Response(status=http.HTTP_204_NO_CONTENT)


class SlipPayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        slip = _slip(_owner(request), pk)
        services.pay_slip(slip, request.user, request.data.get("method"), request.data.get("reference", ""), bool(request.data.get("from_drawer")))
        return Response(slip_full(_slip(slip.run.location.organization_id, pk)))


# ───────────────────────── advances ─────────────────────────
class AdvancesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _owner(request)
        qs = Advance.objects.filter(employee__organization_id=org).select_related("employee__location")
        if request.query_params.get("employee"):
            qs = qs.filter(employee_id=request.query_params["employee"])
        if request.query_params.get("location"):
            qs = qs.filter(employee__location=_location(request, org, request.query_params["location"]))
        if request.query_params.get("status") in Advance.Status.values:
            qs = qs.filter(status=request.query_params["status"])
        return Response([advance_dict(a) for a in qs[:200]])

    def post(self, request):
        org = _owner(request)
        e = _employee(org, request.data.get("employee"))
        try:
            given = date.fromisoformat(request.data["given_on"]) if request.data.get("given_on") else services.today()
        except ValueError:
            raise ValidationError({"given_on": "Use the format YYYY-MM-DD."})
        adv = services.give_advance(e, request.data.get("amount"), request.data.get("installment"), given, request.data.get("reason"), request.user)
        return Response(advance_dict(adv, True), status=http.HTTP_201_CREATED)


def _advance(org, pk):
    return get_object_or_404(Advance.objects.select_related("employee__location"), pk=pk, employee__organization_id=org)


class AdvanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        return Response(advance_dict(_advance(_owner(request), pk), True))


class AdvanceRepayView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        adv = services.repay_advance(_advance(_owner(request), pk), request.data.get("amount"), request.data.get("note"), request.user)
        return Response(advance_dict(adv, True), status=http.HTTP_201_CREATED)


class AdvanceVoidView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        adv = services.void_advance(_advance(_owner(request), pk), request.user)
        return Response(advance_dict(adv, True))
