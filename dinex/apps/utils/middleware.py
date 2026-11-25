from django.utils.deprecation import MiddlewareMixin


class OrganizationMiddleware(MiddlewareMixin):
    """
    Middleware to attach organization_id to request user.
    """
    
    def process_request(self, request):
        if request.user and request.user.is_authenticated:
            # Get user's organization membership
            from apps.organizations.models import OrganizationMembership
            
            membership = OrganizationMembership.objects.filter(
                user=request.user,
                is_active=True
            ).select_related('organization').first()
            
            if membership:
                request.user.organization_id = membership.organization_id
                request.user.organization = membership.organization
            else:
                request.user.organization_id = None
                request.user.organization = None