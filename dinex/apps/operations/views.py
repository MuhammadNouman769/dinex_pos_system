from decimal import Decimal
from datetime import datetime, timedelta

from django.db import transaction
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cash import services as cash
from apps.catalog.utils import get_user_organization_id
from apps.inventory.models import Ingredient
from apps.operations import services
from apps.operations.models import Expense, Purchase, Reservation, Supplier
from apps.orders.models import Table
from apps.organizations.models import Location
from apps.utils.helpers import is_manager_or_owner, location_model_scope, location_scope
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.permissions import CanManageInventory


class OwnerOrManager(CanManageInventory):
    """Money screens: owner or branch manager only, even for reading."""
    message = "Only the owner or a branch manager can use this."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        from apps.organizations.models import LocationMembership, OrganizationMembership
        if OrganizationMembership.objects.filter(user=user, role=OrganizationMembership.Role.OWNER, is_active=True).exists():
            return True
        return LocationMembership.objects.filter(organization_membership__user=user, organization_membership__is_active=True,
                                                 is_active=True, role=LocationMembership.Role.MANAGER).exists()


def _org(request):
    org = get_user_organization_id(request)
    if not org:
        raise PermissionDenied("User has no organization assigned.")
    return org


def _location(request, value, money=False):
    org = _org(request)
    try:
        loc = Location.objects.get(pk=int(value), **location_model_scope(request, org))
    except (TypeError, ValueError, Location.DoesNotExist):
        raise ValidationError({"location": "Choose one of your branches."})
    if money and not is_manager_or_owner(request, loc):
        raise PermissionDenied("Only the owner or this branch's manager can do that.")
    return loc


def _day(value, default):
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({"date": "Use YYYY-MM-DD."})


def _page(request, qs, ser):
    p = StandardResultsSetPagination()
    return p.get_paginated_response(ser(p.paginate_queryset(qs, request), many=True).data)


# ───────────── reservations ─────────────
class ReservationSerializer(serializers.ModelSerializer):
    table_number = serializers.CharField(source="table.table_number", read_only=True, default=None)
    ends_at = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = ["id", "location", "table", "table_number", "guest_name", "phone", "party_size", "starts_at", "ends_at",
                  "duration_minutes", "status", "notes", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def get_ends_at(self, r):
        return r.starts_at + timedelta(minutes=r.duration_minutes)

    def validate_duration_minutes(self, v):
        if not 15 <= v <= 480:
            raise serializers.ValidationError("Between 15 minutes and 8 hours.")
        return v

    def validate_guest_name(self, v):
        if not v.strip():
            raise serializers.ValidationError("Guest name is required.")
        return v.strip()


class ReservationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _org(request)
        qs = Reservation.objects.filter(**location_scope(request, org)).select_related("table")
        if request.query_params.get("location"):
            qs = qs.filter(location_id=request.query_params["location"])
        if request.query_params.get("date"):
            qs = qs.filter(starts_at__date=_day(request.query_params["date"], None))
        elif request.query_params.get("upcoming"):
            qs = qs.filter(starts_at__gte=timezone.now() - timedelta(hours=3), status__in=services.ACTIVE)
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return _page(request, qs, ReservationSerializer)

    @transaction.atomic
    def post(self, request):
        s = ReservationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        loc = _location(request, request.data.get("location"))
        if d["starts_at"] < timezone.now() - timedelta(minutes=30):
            raise ValidationError({"starts_at": "That time has already passed."})
        table = d.get("table")
        services.check_reservation(loc, table, d["party_size"], d["starts_at"], d.get("duration_minutes", 90))
        r = s.save(location=loc, created_by=request.user)
        cash.audit(request.user, loc, "reservation_created", r, guest=r.guest_name, party=r.party_size)
        return Response(ReservationSerializer(r).data, status=status.HTTP_201_CREATED)


class ReservationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request, pk):
        return get_object_or_404(Reservation, pk=pk, **location_scope(request, _org(request)))

    def get(self, request, pk):
        return Response(ReservationSerializer(self._get(request, pk)).data)

    @transaction.atomic
    def patch(self, request, pk):
        r = self._get(request, pk)
        if r.status not in services.ACTIVE:
            raise ValidationError({"detail": "Only active bookings can be changed."})
        s = ReservationSerializer(r, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        d = {**{f: getattr(r, f) for f in ("table", "party_size", "starts_at", "duration_minutes")}, **s.validated_data}
        services.check_reservation(r.location, d["table"], d["party_size"], d["starts_at"], d["duration_minutes"], exclude_id=r.id)
        s.save()
        return Response(ReservationSerializer(r).data)


class ReservationActionView(APIView):
    """seat / cancel / no-show / complete"""
    permission_classes = [IsAuthenticated]
    ACTIONS = {"seat": ("BOOKED", "SEATED"), "cancel": ("BOOKED", "CANCELLED"), "no-show": ("BOOKED", "NO_SHOW"),
               "complete": ("SEATED", "COMPLETED")}

    @transaction.atomic
    def post(self, request, pk, action):
        if action not in self.ACTIONS:
            raise ValidationError({"detail": "Unknown action."})
        r = get_object_or_404(Reservation, pk=pk, **location_scope(request, _org(request)))
        need, new = self.ACTIONS[action]
        if r.status != need:
            raise ValidationError({"detail": f"A {r.get_status_display().lower()} booking cannot be set to {new.lower()}."})
        if action == "seat" and r.table_id:
            t = Table.objects.select_for_update().get(pk=r.table_id)
            if t.status not in ("AVAILABLE", "RESERVED"):
                raise ValidationError({"detail": f"Table {t.table_number} is {t.get_status_display().lower()} right now."})
            t.status = "OCCUPIED"
            t.save(update_fields=["status", "updated_at"])
        r.status = new
        r.save(update_fields=["status"])
        cash.audit(request.user, r.location, f"reservation_{new.lower()}", r, guest=r.guest_name)
        return Response(ReservationSerializer(r).data)


# ───────────── suppliers ─────────────
class SupplierSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = ["id", "name", "phone", "address", "notes", "is_active", "balance"]

    def get_balance(self, s):
        t = s.purchases.aggregate(t=Sum("total"), p=Sum("paid"))
        return (t["t"] or 0) - (t["p"] or 0)


class SupplierListView(APIView):
    permission_classes = [IsAuthenticated, OwnerOrManager]

    def get(self, request):
        qs = Supplier.objects.filter(organization_id=_org(request))
        if request.query_params.get("active", "true") == "true":
            qs = qs.filter(is_active=True)
        return _page(request, qs, SupplierSerializer)

    def post(self, request):
        s = SupplierSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if Supplier.objects.filter(organization_id=_org(request), name__iexact=s.validated_data["name"]).exists():
            raise ValidationError({"name": "You already have a supplier with this name."})
        s.save(organization_id=_org(request))
        return Response(s.data, status=status.HTTP_201_CREATED)


class SupplierDetailView(APIView):
    permission_classes = [IsAuthenticated, OwnerOrManager]

    def patch(self, request, pk):
        sup = get_object_or_404(Supplier, pk=pk, organization_id=_org(request))
        s = SupplierSerializer(sup, data=request.data, partial=True)
        s.is_valid(raise_exception=True)
        s.save()
        return Response(s.data)


# ───────────── purchases ─────────────
class PurchaseLineIn(serializers.Serializer):
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.CharField(required=False, allow_blank=True, max_length=10)
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=4, min_value=Decimal("0"))


class PurchaseIn(serializers.Serializer):
    location = serializers.IntegerField()
    supplier = serializers.IntegerField(required=False, allow_null=True)
    date = serializers.DateField(required=False)
    invoice_no = serializers.CharField(required=False, allow_blank=True, max_length=50)
    note = serializers.CharField(required=False, allow_blank=True, max_length=255)
    paid = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, min_value=Decimal("0"))
    lines = PurchaseLineIn(many=True)


def purchase_dict(p):
    return {"id": p.id, "location": p.location_id, "location_name": p.location.name, "date": p.date, "invoice_no": p.invoice_no,
            "supplier": p.supplier_id, "supplier_name": p.supplier.name if p.supplier else "", "total": p.total, "paid": p.paid,
            "due": p.total - p.paid, "note": p.note,
            "lines": [{"ingredient": l.ingredient_id, "name": l.ingredient.name, "quantity": l.quantity, "unit": l.unit or l.ingredient.base_unit,
                       "unit_cost": l.unit_cost, "line_total": l.line_total} for l in p.lines.select_related("ingredient")]}


class PurchaseListView(APIView):
    permission_classes = [IsAuthenticated, OwnerOrManager]

    def get(self, request):
        qs = Purchase.objects.filter(**location_scope(request, _org(request))).select_related("location", "supplier")
        if request.query_params.get("supplier"):
            qs = qs.filter(supplier_id=request.query_params["supplier"])
        if request.query_params.get("unpaid") == "true":
            from django.db.models import F
            qs = qs.filter(paid__lt=F("total"))
        p = StandardResultsSetPagination()
        return p.get_paginated_response([purchase_dict(x) for x in p.paginate_queryset(qs, request)])

    def post(self, request):
        s = PurchaseIn(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        loc = _location(request, d["location"], money=True)
        supplier = None
        if d.get("supplier"):
            supplier = get_object_or_404(Supplier, pk=d["supplier"], organization_id=loc.organization_id)
        org = loc.organization_id
        for ln in d["lines"]:
            if ln["ingredient"].organization_id != org:
                raise ValidationError({"lines": "Unknown ingredient."})
            if not ln["ingredient"].is_active or ln["ingredient"].is_prepared:
                raise ValidationError({"lines": f"{ln['ingredient'].name} cannot be purchased."})
        p = services.receive_purchase(loc, supplier, d.get("date") or timezone.localdate(), d["lines"], d.get("paid", 0),
                                      d.get("invoice_no", ""), d.get("note", ""), request.user)
        return Response(purchase_dict(p), status=status.HTTP_201_CREATED)


class PurchasePayView(APIView):
    """Pay (part of) what is still owed on a bill."""
    permission_classes = [IsAuthenticated, OwnerOrManager]

    @transaction.atomic
    def post(self, request, pk):
        p = get_object_or_404(Purchase.objects.select_for_update(), pk=pk, **location_scope(request, _org(request)))
        _location(request, p.location_id, money=True)
        try:
            amt = services.q2(request.data.get("amount"))
        except Exception:
            raise ValidationError({"amount": "Enter a valid amount."})
        if amt <= 0 or amt > p.total - p.paid:
            raise ValidationError({"amount": f"Between 0.01 and the amount due ({p.total - p.paid})."})
        p.paid += amt
        p.save(update_fields=["paid"])
        cash.audit(request.user, p.location, "purchase_paid", p, amount=amt)
        return Response(purchase_dict(p))


# ───────────── expenses ─────────────
class ExpenseSerializer(serializers.ModelSerializer):
    location_name = serializers.CharField(source="location.name", read_only=True)

    class Meta:
        model = Expense
        fields = ["id", "location", "location_name", "date", "category", "description", "amount", "source", "created_at"]
        read_only_fields = ["id", "created_at"]
        extra_kwargs = {"date": {"required": False}, "source": {"required": False}}


class ExpenseListView(APIView):
    permission_classes = [IsAuthenticated, OwnerOrManager]

    def get(self, request):
        qs = Expense.objects.filter(**location_scope(request, _org(request))).select_related("location")
        today = timezone.localdate()
        start = _day(request.query_params.get("from"), None)
        end = _day(request.query_params.get("to"), None)
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        if not start and not end:
            qs = qs.filter(date__gte=today - timedelta(days=30))
        if request.query_params.get("location"):
            qs = qs.filter(location_id=request.query_params["location"])
        total = qs.aggregate(t=Sum("amount"))["t"] or 0
        by_cat = list(qs.values("category").annotate(total=Sum("amount")).order_by("-total"))
        resp = _page(request, qs, ExpenseSerializer)
        resp.data["total"] = total
        resp.data["by_category"] = by_cat
        return resp

    def post(self, request):
        s = ExpenseSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        loc = _location(request, request.data.get("location"), money=True)
        if d.get("date") and d["date"] > timezone.localdate():
            raise ValidationError({"date": "An expense cannot be in the future."})
        e = services.add_expense(loc, request.user, d.get("date") or timezone.localdate(), d["category"], d["amount"],
                                 d.get("description", ""), d.get("source", "OTHER"))
        return Response(ExpenseSerializer(e).data, status=status.HTTP_201_CREATED)


class ExpenseDetailView(APIView):
    permission_classes = [IsAuthenticated, OwnerOrManager]

    def delete(self, request, pk):
        e = get_object_or_404(Expense, pk=pk, **location_scope(request, _org(request)))
        _location(request, e.location_id, money=True)
        if e.movement_id:
            raise ValidationError({"detail": "This was paid from the cash drawer, so it is part of a shift's cash count and cannot be deleted."})
        cash.audit(request.user, e.location, "expense_deleted", e, amount=e.amount, category=e.category)
        e.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ───────────── end-of-day report ─────────────
class DayReportView(APIView):
    permission_classes = [IsAuthenticated, OwnerOrManager]

    def get(self, request):
        org = _org(request)
        day = _day(request.query_params.get("date"), timezone.localdate())
        locs = Location.objects.filter(**location_model_scope(request, org))
        if request.query_params.get("location"):
            locs = locs.filter(pk=request.query_params["location"])
        allowed = [l for l in locs if is_manager_or_owner(request, l)]
        if not allowed:
            raise PermissionDenied("Reports are for owners and managers.")
        return Response(services.day_report(allowed, day))
