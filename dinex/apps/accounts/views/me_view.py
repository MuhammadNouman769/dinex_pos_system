from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.utils import get_user_organization_id
from apps.utils.helpers import get_accessible_location_ids
from apps.organizations.models import (
    Organization, Location, OrganizationMembership, LocationMembership,
)


from apps.organizations.branding import branding_dict
from apps.loyalty.services import public_rules as loyalty_rules


class MeAPIView(APIView):
    """
    Who am I? Everything the frontend needs after login: the user, their
    restaurant, what they may do, and the locations they can work at.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,                       # PLATFORM (XverLabs staff) or OWNER
            "organization": None,
            "membership_role": None,
            "is_owner": False,
            "can_manage_menu": False,
            "can_manage_inventory": False,
            "can_operate_pos": False,
            "can_view_reports": False,
            "locations": [],
            "subscription": None,
        }

        org_id = get_user_organization_id(request)
        if not org_id:
            return Response(data)

        org = Organization.objects.get(pk=org_id)
        from apps.billing.services import status_info
        data["subscription"] = status_info(org)
        membership = OrganizationMembership.objects.filter(
            user=user, organization=org, is_active=True).first()
        data["organization"] = {
            "id": org.id, "name": org.name, "currency": org.currency,
            "timezone": org.timezone, "is_active": org.is_active,
            "branding": branding_dict(org, request),
            "loyalty": loyalty_rules(org.id),
        }
        data["membership_role"] = membership.role if membership else None

        location_ids = get_accessible_location_ids(request, org_id)   # None = owner (all)
        is_owner = location_ids is None
        locations = Location.objects.filter(organization=org, is_active=True)
        if not is_owner:
            locations = locations.filter(pk__in=location_ids)

        roles = {}
        if not is_owner:
            roles = dict(LocationMembership.objects.filter(
                organization_membership=membership, is_active=True,
            ).values_list("location_id", "role"))

        data["locations"] = [{
            "id": l.id, "name": l.name, "address": l.address, "is_primary": l.is_primary,
            "tax_rate": l.tax_rate, "service_charge_rate": l.service_charge_rate,
            "inventory_policy": l.inventory_policy,
            "role": "OWNER" if is_owner else roles.get(l.id),
        } for l in locations]

        is_manager = any(r == LocationMembership.Role.MANAGER for r in roles.values())
        data["is_owner"] = is_owner
        data["can_manage_menu"] = is_owner
        data["can_manage_inventory"] = is_owner or is_manager
        data["can_operate_pos"] = is_owner or bool(roles)
        data["can_view_reports"] = is_owner or is_manager
        return Response(data)
