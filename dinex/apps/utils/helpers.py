""" ======================= Request Helpers ======================= """


def get_user_organization_id(request):
    """
    Resolve the organization_id for the current request's user.

    Caches the result on the user instance for the lifetime of the
    request so repeated calls within the same view don't hit the
    database again.
    """
    organization_id = getattr(request.user, "organization_id", None)

    if not organization_id:
        from apps.organizations.models import OrganizationMembership

        membership = (
            OrganizationMembership.objects
            .filter(user=request.user, is_active=True)
            .select_related("organization")
            .first()
        )

        if membership:
            organization_id = membership.organization_id
            request.user.organization_id = organization_id
            request.user.organization = membership.organization

    return organization_id


# ───────────── Location access (owner = all, staff = assigned only) ─────────────
def get_accessible_location_ids(request, organization_id):
    """
    None  -> unrestricted (organization OWNER): every location of the org.
    set() -> ids of the locations the user is actively assigned to
             (MANAGER / POS_OPERATOR). Empty set = no access.
    Cached on the request.
    """
    cache = getattr(request, "_accessible_location_ids", None)
    if cache is not None and cache[0] == organization_id:
        return cache[1]

    from apps.organizations.models import OrganizationMembership, LocationMembership

    user = request.user
    is_owner = OrganizationMembership.objects.filter(
        user=user,
        organization_id=organization_id,
        role=OrganizationMembership.Role.OWNER,
        is_active=True,
    ).exists()

    if is_owner:
        ids = None
    else:
        ids = set(
            LocationMembership.objects.filter(
                organization_membership__user=user,
                organization_membership__organization_id=organization_id,
                organization_membership__is_active=True,
                is_active=True,
            ).values_list("location_id", flat=True)
        )

    request._accessible_location_ids = (organization_id, ids)
    return ids


def location_scope(request, organization_id, prefix="location"):
    """
    ORM filter kwargs limiting a queryset to what the caller may touch:
    always their organization, plus their assigned locations for non-owners.
        Order.objects.filter(**location_scope(request, org_id))
        OrderItem.objects.filter(**location_scope(request, org_id, "order__location"))
    """
    scope = {f"{prefix}__organization_id": organization_id}
    ids = get_accessible_location_ids(request, organization_id)
    if ids is not None:
        scope[f"{prefix}_id__in"] = ids
    return scope


def location_model_scope(request, organization_id):
    """Same idea, for querying the Location model itself."""
    scope = {"organization_id": organization_id}
    ids = get_accessible_location_ids(request, organization_id)
    if ids is not None:
        scope["id__in"] = ids
    return scope


def is_manager_or_owner(request, location):
    """True for the organization OWNER, or an active MANAGER at `location`."""
    from apps.organizations.models import LocationMembership

    ids = get_accessible_location_ids(request, location.organization_id)
    if ids is None:                                   # owner of this location's organization
        return True
    return LocationMembership.objects.filter(
        organization_membership__user=request.user,
        organization_membership__organization_id=location.organization_id,
        organization_membership__is_active=True,
        location=location, is_active=True, role=LocationMembership.Role.MANAGER,
    ).exists()
