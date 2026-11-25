from apps.organizations.models import OrganizationMembership


def get_user_organization_id(request):
    """
    Helper to get organization_id from user.
    If not set, fetch from membership and set it.
    """
    organization_id = getattr(request.user, 'organization_id', None)
    
    if not organization_id:
        membership = OrganizationMembership.objects.filter(
            user=request.user,
            is_active=True,
            organization__is_active=True,
        ).select_related('organization').first()
        
        if membership:
            organization_id = membership.organization_id
            request.user.organization_id = organization_id
            request.user.organization = membership.organization
    return organization_id