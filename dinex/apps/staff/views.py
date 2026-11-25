from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cash import services as cash
from apps.catalog.utils import get_user_organization_id
from apps.orders.models import Order
from apps.organizations.models import Location, OrganizationMembership
from apps.staff import services
from apps.staff.models import Employee, RiderSettlement, Role
from apps.staff.serializers import EmployeeSerializer
from apps.utils.helpers import is_manager_or_owner, location_model_scope, location_scope, get_accessible_location_ids
from apps.utils.pagination import StandardResultsSetPagination
from apps.utils.permissions import CanOperatePOS


def _org(request):
    org = get_user_organization_id(request)
    if not org:
        raise PermissionDenied("User has no organization assigned.")
    return org


def _employee(request, pk):
    return get_object_or_404(Employee.objects.select_related("location", "user"), pk=pk, **location_scope(request, _org(request)))


def _serialize(emp, request):
    return EmployeeSerializer(emp, context={"request": request}).data


class EmployeeListCreateView(APIView):
    """Everyone at a branch can look the team up (the POS needs the waiter list); owner / branch manager hire."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _org(request)
        qs = Employee.objects.filter(**location_scope(request, org)).select_related("location", "user")
        p = request.query_params
        if p.get("location"):
            try:
                qs = qs.filter(location_id=int(p["location"]))
            except ValueError:
                raise ValidationError({"location": "Invalid location id."})
        if p.get("role"):
            if p["role"] not in Role.values:
                raise ValidationError({"role": "Unknown role."})
            qs = qs.filter(role=p["role"])
        if p.get("active", "true").lower() == "true":
            qs = qs.filter(is_active=True)
        if p.get("search"):
            qs = qs.filter(Q(name__icontains=p["search"]) | Q(phone__icontains=p["search"]) | Q(code__icontains=p["search"]))
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response([_serialize(e, request) for e in page])

    @transaction.atomic
    def post(self, request):
        org = _org(request)
        serializer = EmployeeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        location = serializer.validated_data["location"]
        if not is_manager_or_owner(request, location):
            raise PermissionDenied("Only the owner or a branch manager can add employees.")
        emp = serializer.save(organization_id=org, code=services.next_code(location.organization))
        return Response(_serialize(emp, request), status=status.HTTP_201_CREATED)


class EmployeeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        emp = _employee(request, pk)
        from apps.staff import attendance as att
        from apps.staff.views_attendance import record_dict, schedule_dict
        at = att.now(); day = att.local_date(at)
        sched = att.schedule_of(emp)
        rec = emp.attendance.filter(date=day).first()
        return Response({**_serialize(emp, request), "stats": services.employee_stats(emp), "schedule": schedule_dict(sched),
                         "today": {"state": att.day_state(emp, sched, rec, day, at), "record": record_dict(rec)}})

    def patch(self, request, pk):
        emp = _employee(request, pk)
        if not is_manager_or_owner(request, emp.location):
            raise PermissionDenied("Only the owner or a branch manager can edit employees.")
        serializer = EmployeeSerializer(emp, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        new_loc = serializer.validated_data.get("location")
        if new_loc is not None and not is_manager_or_owner(request, new_loc):
            raise PermissionDenied("You cannot move an employee to a branch you do not manage.")
        if serializer.validated_data.get("is_active") is False and emp.is_active:
            self._can_deactivate(emp)
        serializer.save()
        return Response(_serialize(emp, request))

    def delete(self, request, pk):
        emp = _employee(request, pk)
        if not is_manager_or_owner(request, emp.location):
            raise PermissionDenied("Only the owner or a branch manager can remove employees.")
        self._can_deactivate(emp)
        emp.delete()                      # soft delete: old orders keep the name
        return Response(status=status.HTTP_204_NO_CONTENT)

    @staticmethod
    def _can_deactivate(emp):
        open_orders = Order.objects.filter(Q(waiter=emp) | Q(rider=emp)).exclude(status__in=["COMPLETED", "CANCELLED"]).count()
        if open_orders:
            raise ValidationError({"detail": f"{emp.name} is on {open_orders} open order(s). Finish or reassign them first."})
        if emp.role == Role.RIDER and services.unsettled_orders(emp):
            raise ValidationError({"detail": f"{emp.name} still owes cash from deliveries. Settle it first."})


class LinkUserView(APIView):
    """Owner links an employee to an existing login of the same restaurant (or unlinks with user_id = null)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        org = _org(request)
        emp = _employee(request, pk)
        if get_accessible_location_ids(request, org) is not None:
            raise PermissionDenied("Only the owner can link a login.")
        user_id = request.data.get("user_id")
        if user_id in (None, ""):
            emp.user = None
        else:
            member = OrganizationMembership.objects.filter(organization_id=org, user_id=user_id, is_active=True).select_related("user").first()
            if member is None:
                raise ValidationError({"user_id": "No such user in your restaurant."})
            if Employee.objects.filter(user_id=user_id).exclude(pk=emp.pk).exists():
                raise ValidationError({"user_id": "This login is already linked to another employee."})
            emp.user = member.user
        emp.save(update_fields=["user", "updated_at"])
        return Response(_serialize(emp, request))


# ───────────────────────── riders ─────────────────────────
def _rider(request, pk):
    emp = _employee(request, pk)
    if emp.role != Role.RIDER:
        raise ValidationError({"detail": "This employee is not a rider."})
    return emp


class RiderListView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def get(self, request):
        org = _org(request)
        qs = Employee.objects.filter(role=Role.RIDER, is_active=True, **location_scope(request, org)).select_related("location")
        if request.query_params.get("location"):
            try:
                qs = qs.filter(location_id=int(request.query_params["location"]))
            except ValueError:
                raise ValidationError({"location": "Invalid location id."})
        return Response([{**_serialize(r, request), "summary": services.rider_summary(r)} for r in qs])


class RiderLedgerView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def get(self, request, pk):
        rider = _rider(request, pk)
        pending = services.unsettled_orders(rider)
        history = rider.settlements.select_related("received_by")[:20]
        return Response({
            "rider": _serialize(rider, request), "summary": services.rider_summary(rider),
            "orders": [{"id": o.id, "order_number": o.order_number, "customer_name": o.customer_name, "address": o.delivery_address,
                        "total": o.total_amount, "due": due, "delivered_at": o.delivered_at} for o, due in pending],
            "settlements": [{"id": s.id, "expected": s.expected, "handed": s.handed, "shortage": s.shortage, "orders": len(s.order_ids),
                             "received_by": s.received_by.username, "note": s.note, "created_at": s.created_at} for s in history],
        })


class RiderSettleView(APIView):
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def post(self, request, pk):
        rider = _rider(request, pk)
        if request.data.get("handed") in (None, ""):
            raise ValidationError({"handed": "Enter the cash received."})
        s = services.settle(rider, request.user, request.data["handed"], request.data.get("order_ids"), request.data.get("note", ""))
        return Response({"id": s.id, "expected": s.expected, "handed": s.handed, "shortage": s.shortage,
                         "summary": services.rider_summary(rider)}, status=status.HTTP_201_CREATED)


class AssignRiderView(APIView):
    """POST /staff/orders/<id>/assign-rider/ {rider: id | null}"""
    permission_classes = [IsAuthenticated, CanOperatePOS]

    def post(self, request, pk):
        org = _org(request)
        order = get_object_or_404(Order.objects.select_related("location"), pk=pk, **location_scope(request, org))
        if order.order_type != "DELIVERY":
            raise ValidationError({"detail": "Only delivery orders have a rider."})
        if order.status in ("COMPLETED", "CANCELLED"):
            raise ValidationError({"detail": f"A {order.status.lower()} order cannot be changed."})
        if order.status == "OUT_FOR_DELIVERY" and not is_manager_or_owner(request, order.location):
            raise PermissionDenied("The order already left. Only a manager or the owner can change its rider.")
        rider_id = request.data.get("rider")
        if rider_id in (None, ""):
            if order.status == "OUT_FOR_DELIVERY":
                raise ValidationError({"detail": "The order is already out for delivery."})
            order.rider = None
        else:
            rider = Employee.objects.filter(pk=rider_id, organization_id=org, role=Role.RIDER, is_active=True, location_id=order.location_id).first()
            if rider is None:
                raise ValidationError({"rider": "Choose an active rider of this branch."})
            if order.rider_id and order.rider_id != rider.id and order.status == "OUT_FOR_DELIVERY":
                cash.audit(request.user, order.location, "rider_reassigned", order, order_number=order.order_number,
                           old=order.rider.name, new=rider.name)
            order.rider = rider
        order.save(update_fields=["rider", "updated_at"])
        return Response({"id": order.id, "rider": order.rider_id, "rider_name": order.rider.name if order.rider else None})
