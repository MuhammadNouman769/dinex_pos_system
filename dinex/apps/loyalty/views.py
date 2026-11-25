from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.utils import get_user_organization_id
from apps.customers.models.customer import Customer
from apps.loyalty import services
from apps.orders.models import Order
from apps.organizations.models import Location, Organization
from apps.utils.helpers import location_model_scope, location_scope
from apps.operations.views import OwnerOrManager


class SettingsSerializer(serializers.Serializer):
    enabled = serializers.BooleanField()
    spend_per_point = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("1"))
    point_value = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))
    min_redeem = serializers.IntegerField(min_value=1, max_value=100000)
    email_customers = serializers.BooleanField()
    reminders = serializers.BooleanField()


def _org(request):
    org = get_user_organization_id(request)
    if not org:
        raise PermissionDenied("User has no organization assigned.")
    return org


def settings_dict(s):
    return {f: getattr(s, f) for f in SettingsSerializer().fields}


class LoyaltySettingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        s = services.get_settings(_org(request), create=True)
        return Response(settings_dict(s))

    def patch(self, request):
        if not request.user.is_authenticated or not _is_owner(request):
            raise PermissionDenied("Only the owner can change loyalty rules.")
        s = services.get_settings(_org(request), create=True)
        ser = SettingsSerializer(data={**settings_dict(s), **request.data})
        ser.is_valid(raise_exception=True)
        for k, v in ser.validated_data.items():
            setattr(s, k, v)
        s.save()
        return Response(settings_dict(s))


def _is_owner(request):
    from apps.organizations.models import OrganizationMembership
    return OrganizationMembership.objects.filter(user=request.user, organization_id=_org(request),
                                                 role=OrganizationMembership.Role.OWNER, is_active=True).exists()


class LookupView(APIView):
    """Cashier types a phone number: who is this and how many points do they have?"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        org = _org(request)
        try:
            loc = Location.objects.get(pk=int(request.query_params.get("location")), **location_model_scope(request, org))
        except (TypeError, ValueError, Location.DoesNotExist):
            raise ValidationError({"location": "Choose a branch."})
        phone = (request.query_params.get("phone") or "").strip()
        s = services.get_settings(org)
        c = Customer.objects.filter(location=loc, phone=phone).first() if phone else None
        if not c:
            return Response({"found": False})
        return Response({"found": True, "id": c.id, "name": c.full_name, "email": c.email or "", "balance": c.points_balance,
                         "can_redeem": bool(s and s.enabled and c.points_balance >= s.min_redeem)})


class RedeemView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk, **location_scope(request, _org(request)))
        order = services.redeem(order, request.data.get("points"), request.user)
        from apps.orders.serializers.order_serializer import OrderSerializer
        return Response(OrderSerializer(order, context={"request": request}).data)


class SendRemindersView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not _is_owner(request):
            raise PermissionDenied("Only the owner can send reminders.")
        return Response(services.send_reminders(Organization.objects.get(pk=_org(request)), min_gap_days=int(request.data.get("min_gap_days", 3))))
