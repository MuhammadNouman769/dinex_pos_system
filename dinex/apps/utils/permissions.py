from rest_framework.permissions import BasePermission, SAFE_METHODS


def _resolve_organization_id(obj):
    """
    Resolve the organization_id an object belongs to, regardless of
    whether the object IS an Organization, has a direct `organization`
    FK, or is nested under an `organization_membership`.
    """
    from apps.organizations.models import Organization

    if isinstance(obj, Organization):
        return obj.pk

    organization_id = getattr(obj, "organization_id", None)
    if organization_id:
        return organization_id

    organization_membership = getattr(obj, "organization_membership", None)
    if organization_membership is not None:
        return organization_membership.organization_id

    return None


class IsPlatformUser(BasePermission):
    """
    Allows access only to platform users.
    """
    message = "Only platform users can access this endpoint."
    
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.role == user.Role.PLATFORM


class IsOrganizationOwner(BasePermission):
    """
    Allows access only to organization owners.
    """
    message = "Only organization owners can perform this action."
    
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        
        # Platform user can do everything
        if user.role == user.Role.PLATFORM:
            return True
        
        # Check if user is owner
        if user.role == user.Role.OWNER:
            from apps.organizations.models import OrganizationMembership
            return OrganizationMembership.objects.filter(
                user=user,
                role=OrganizationMembership.Role.OWNER,
                is_active=True
            ).exists()
        
        return False
    
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.role == user.Role.PLATFORM:
            return True

        organization_id = _resolve_organization_id(obj)
        if organization_id is None:
            return False

        from apps.organizations.models import OrganizationMembership
        return OrganizationMembership.objects.filter(
            user=user,
            organization_id=organization_id,
            role=OrganizationMembership.Role.OWNER,
            is_active=True
        ).exists()


class IsOrganizationOwnerOrReadOnly(BasePermission):
    """
    Read-only for all authenticated users.
    Write access only for organization owners and platform users.
    """
    
    def has_permission(self, request, view):
        # Read-only for authenticated users
        if request.method in SAFE_METHODS:
            return request.user and request.user.is_authenticated
        
        # Write operations: owner or platform
        return IsOrganizationOwner().has_permission(request, view)
    
    def has_object_permission(self, request, view, obj):
        # Read-only allowed
        if request.method in SAFE_METHODS:
            return True
        
        # Write operations: owner or platform
        return IsOrganizationOwner().has_object_permission(request, view, obj)


class IsAuthenticatedOrReadOnly(BasePermission):
    """
    Read-only for everyone. Write only for authenticated users.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


""" ======================= Location Role Helpers ======================= """
def get_active_location_role(user, location_id):
    """
    Returns the LocationMembership.Role the user currently holds at
    `location_id`, or None if they have no active assignment there.
    """
    if not location_id or not user or not user.is_authenticated:
        return None

    from apps.organizations.models import LocationMembership

    return (
        LocationMembership.objects
        .filter(
            organization_membership__user=user,
            organization_membership__is_active=True,
            location_id=location_id,
            is_active=True,
        )
        .values_list("role", flat=True)
        .first()
    )


def is_location_manager(user, location_id):
    from apps.organizations.models import LocationMembership
    return get_active_location_role(user, location_id) == LocationMembership.Role.MANAGER


def is_location_staff(user, location_id):
    """True for MANAGER or POS_OPERATOR — any active assignment at the location."""
    return get_active_location_role(user, location_id) is not None


def user_can_manage_location_catalog(user, organization_id, location_id):
    """
    True for platform users, the organization's owner, or an active
    MANAGER at that specific location. Used to gate per-location catalog
    assignments (e.g. ProductLocation availability/pricing) — the one
    piece of catalog data a location manager is allowed to change
    without going through the organization owner.
    """
    if not user or not user.is_authenticated:
        return False

    if user.role == user.Role.PLATFORM:
        return True

    from apps.organizations.models import OrganizationMembership

    is_owner = OrganizationMembership.objects.filter(
        user=user,
        organization_id=organization_id,
        role=OrganizationMembership.Role.OWNER,
        is_active=True,
    ).exists()
    if is_owner:
        return True

    return is_location_manager(user, location_id)


class IsLocationManagerOrOrgOwner(BasePermission):
    """
    Allows platform users, the organization's owner, or an active
    location MANAGER. Requires the view to resolve `organization_id`
    and expose the target location id per-request via
    `view.get_location_id(request)` for list/create, and relies on
    `has_object_permission` (object's `location_id`) for detail routes.
    """
    message = "Only the organization owner or this location's manager can perform this action."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        get_location_id = getattr(view, "get_location_id", None)
        if get_location_id is None:
            return True

        organization_id = getattr(view, "get_organization_id", lambda r: None)(request)
        location_id = get_location_id(request)

        return user_can_manage_location_catalog(user, organization_id, location_id)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        organization_id = _resolve_organization_id(obj)
        location_id = getattr(obj, "location_id", None)

        return user_can_manage_location_catalog(user, organization_id, location_id)

class CanOperatePOS(BasePermission):
    """
    Day-to-day POS work (orders, items, customers, table occupy/free).

    - Read: any authenticated user (data is still scoped by organization/location).
    - Write: the organization OWNER, or a user with an active MANAGER /
      POS_OPERATOR assignment at some location. Which locations they may
      touch is enforced by `location_scope()` in the views and by
      OrganizationScopedMixin in the serializers.
    """
    message = "You are not assigned to a location, so you cannot do this."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True

        from apps.organizations.models import OrganizationMembership, LocationMembership

        if OrganizationMembership.objects.filter(
            user=user, role=OrganizationMembership.Role.OWNER, is_active=True
        ).exists():
            return True

        return LocationMembership.objects.filter(
            organization_membership__user=user,
            organization_membership__is_active=True,
            is_active=True,
        ).exists()


class CanManageInventory(BasePermission):
    """
    Stock movements (purchases, wastage, counts): the organization OWNER or an
    active location MANAGER. Cashiers (POS_OPERATOR) can only read stock.
    Which locations a manager may touch is enforced in the serializer.
    """
    message = "Only the owner or a location manager can change stock."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True

        from apps.organizations.models import OrganizationMembership, LocationMembership

        if OrganizationMembership.objects.filter(
            user=user, role=OrganizationMembership.Role.OWNER, is_active=True
        ).exists():
            return True
        return LocationMembership.objects.filter(
            organization_membership__user=user,
            organization_membership__is_active=True,
            is_active=True,
            role=LocationMembership.Role.MANAGER,
        ).exists()


class IsPlatformUser(BasePermission):
    """XverLabs staff only (the DineX Admin panel)."""
    message = "Only XverLabs platform staff can do this."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, "role", None) == "PLATFORM")
