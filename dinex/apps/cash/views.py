from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.utils import get_user_organization_id
from apps.cash import services
from apps.cash.models import AuditLog, Payment, Shift
from apps.orders.models import Order
from apps.organizations.models import Location
from apps.utils.helpers import is_manager_or_owner, location_model_scope, location_scope, get_accessible_location_ids
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.permissions import CanOperatePOS


def _org(request):
    org = get_user_organization_id(request)
    if not org:
        raise PermissionDenied("User has no organization assigned.")
    return org


def _money(data, key, required=True):
    value = data.get(key)
    if value in (None, ""):
        if required:
            raise ValidationError({key: "This field is required."})
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        raise ValidationError({key: "Enter a valid amount."})


def _shift(request, pk):
    org = _org(request)
    shift = get_object_or_404(Shift.objects.select_related("location", "opened_by"), pk=pk, **location_scope(request, org, "location"))
    if shift.opened_by_id != request.user.id and not is_manager_or_owner(request, shift.location):
        get_object_or_404(Shift, pk=-1)          # cashiers only see their own shifts -> 404
    return shift


def _order(request, pk):
    org = _org(request)
    return get_object_or_404(Order.objects.select_related("location"), pk=pk, **location_scope(request, org))


def _payment_dict(p):
    return {"id": p.id, "kind": p.kind, "method": p.method, "amount": p.amount, "tendered": p.tendered,
            "change": (p.tendered - p.amount) if p.tendered is not None else None,
            "reference": p.reference, "reason": p.reason, "by": p.created_by.username, "created_at": p.created_at}


def _order_money(order):
    paid, refunded = services.paid_and_refunded(order)
    return {"total": order.total_amount, "paid": paid, "refunded": refunded,
            "due": max(services.amount_due(order), Decimal("0.00")), "payment_status": order.payment_status}


# ───────────────────────── shifts ─────────────────────────
class CurrentShiftView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def get(self, request):
        org = _org(request)
        try:
            location_id = int(request.query_params.get("location", ""))
        except ValueError:
            raise ValidationError({"location": "Required."})
        get_object_or_404(Location, pk=location_id, **location_model_scope(request, org))
        shift = services.current_shift(request.user, location_id)
        return Response({"shift": services.shift_summary(shift) if shift else None})


class OpenShiftView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def post(self, request):
        org = _org(request)
        location = get_object_or_404(Location, pk=request.data.get("location"), **location_model_scope(request, org))
        shift = services.open_shift(request.user, location, _money(request.data, "opening_cash"))
        return Response(services.shift_summary(shift), status=status.HTTP_201_CREATED)


class ShiftListView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def get(self, request):
        org = _org(request)
        qs = Shift.objects.filter(**location_scope(request, org)).select_related("location", "opened_by")
        location = request.query_params.get("location")
        if location:
            try:
                qs = qs.filter(location_id=int(location))
            except ValueError:
                raise ValidationError({"location": "Invalid location id."})
        ids = get_accessible_location_ids(request, org)
        if ids is not None:      # staff: own shifts only, unless they manage the location
            managed = [l.id for l in Location.objects.filter(pk__in=ids) if is_manager_or_owner(request, l)]
            qs = qs.filter(opened_by=request.user) | qs.filter(location_id__in=managed)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs.distinct(), request)
        return paginator.get_paginated_response([{
            "id": s.id, "status": s.status, "location": s.location_id, "location_name": s.location.name,
            "cashier": s.opened_by.username, "opened_at": s.opened_at, "closed_at": s.closed_at,
            "opening_cash": s.opening_cash, "expected_cash": s.expected_cash, "counted_cash": s.counted_cash,
            "difference": s.difference,
        } for s in page])


class ShiftDetailView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def get(self, request, pk):
        return Response(services.shift_summary(_shift(request, pk)))


class CloseShiftView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def post(self, request, pk):
        shift = _shift(request, pk)
        shift = services.close_shift(shift, request.user, _money(request.data, "counted_cash"), request.data.get("note", ""))
        return Response(services.shift_summary(shift))


class ReopenShiftView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def post(self, request, pk):
        shift = _shift(request, pk)
        ids = get_accessible_location_ids(request, shift.location.organization_id)
        if ids is not None:
            raise PermissionDenied("Only the owner can reopen a closed shift.")
        shift = services.reopen_shift(shift, request.user, request.data.get("reason", ""))
        return Response(services.shift_summary(shift))


class MovementView(APIView):
    """Cash in / cash out / expense / safe drop on an open shift."""
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def post(self, request, pk):
        shift = _shift(request, pk)
        if shift.opened_by_id != request.user.id:
            raise PermissionDenied("You can only record cash movements on your own shift.")
        m = services.add_movement(shift, request.user, request.data.get("kind"), _money(request.data, "amount"),
                                  request.data.get("reason", ""), request.data.get("category", ""))
        return Response({"id": m.id, "shift": services.shift_summary(shift)}, status=status.HTTP_201_CREATED)


# ───────────────────────── payments ─────────────────────────
class OrderPaymentsView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def get(self, request, pk):
        order = _order(request, pk)
        rows = order.payments.select_related("created_by")
        return Response({"order": _order_money(order), "payments": [_payment_dict(p) for p in rows]})

    def post(self, request, pk):
        order = _order(request, pk)
        amount = _money(request.data, "amount", required=False)
        if amount is None:                                  # default: pay what is due
            amount = max(services.amount_due(order), Decimal("0.00"))
        payment, order = services.take_payment(
            order, request.user, request.data.get("method"), amount,
            tendered=request.data.get("tendered"), reference=request.data.get("reference", ""))
        return Response({"payment": _payment_dict(payment), "order": _order_money(order)}, status=status.HTTP_201_CREATED)


class OrderRefundView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def post(self, request, pk):
        order = _order(request, pk)
        if not is_manager_or_owner(request, order.location):
            raise PermissionDenied("Only a manager or the owner can give a refund.")
        payment, order = services.refund_payment(order, request.user, request.data.get("method"),
                                                 _money(request.data, "amount"), request.data.get("reason", ""))
        return Response({"payment": _payment_dict(payment), "order": _order_money(order)}, status=status.HTTP_201_CREATED)


# ───────────────────────── reports & audit ─────────────────────────
def _parse_day(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({"date": "Use YYYY-MM-DD."})


class SalesReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _org(request)
        today = timezone.localdate()
        start = _parse_day(request.query_params.get("from"), today)
        end = _parse_day(request.query_params.get("to"), today)
        if end < start:
            raise ValidationError({"to": "Must not be before 'from'."})
        if (end - start).days > 366:
            raise ValidationError({"to": "Choose a range of at most one year."})

        locations = Location.objects.filter(**location_model_scope(request, org))
        if request.query_params.get("location"):
            try:
                locations = locations.filter(pk=int(request.query_params["location"]))
            except ValueError:
                raise ValidationError({"location": "Invalid location id."})
        allowed = [l for l in locations if is_manager_or_owner(request, l)]
        if not allowed:
            raise PermissionDenied("Reports are for owners and managers.")
        return Response(services.sales_report(allowed, start, end))


class AuditLogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _org(request)
        if get_accessible_location_ids(request, org) is not None:
            raise PermissionDenied("Only the owner can see the audit log.")
        qs = AuditLog.objects.filter(organization_id=org).select_related("user", "location")
        if request.query_params.get("action"):
            qs = qs.filter(action=request.query_params["action"])
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([{
            "id": a.id, "action": a.action, "user": a.user.username if a.user else None,
            "location": a.location.name if a.location else None, "object_type": a.object_type,
            "object_id": a.object_id, "details": a.details, "created_at": a.created_at} for a in page])
