from django.contrib.auth import get_user_model
from django.db import transaction

from apps.organizations.models import Organization, OrganizationMembership, Location

User = get_user_model()


@transaction.atomic
def create_restaurant(organization_data, owner_data, location_data):
    """Create owner user + organization + owner membership + first location. Returns (owner, organization, location)."""
    owner = User(
        username=owner_data["username"], email=owner_data["email"],
        first_name=owner_data["first_name"], last_name=owner_data["last_name"],
        role=User.Role.OWNER, is_active=True,
    )
    owner.set_password(owner_data["password"])
    owner.save()

    organization = Organization.objects.create(
        name=organization_data["name"], currency=organization_data["currency"],
        timezone=organization_data["timezone"], is_active=True,
    )
    OrganizationMembership.objects.create(
        user=owner, organization=organization, role=OrganizationMembership.Role.OWNER, is_active=True,
    )
    location = Location.objects.create(
        organization=organization, name=location_data["name"], address=location_data["address"],
        phone=location_data.get("phone", ""), is_primary=location_data.get("is_primary", True), is_active=True,
    )
    return owner, organization, location
