from apps.organizations.models import Organization


def get_platform_organizations():
    """
    Return organizations with their locations.

    Uses prefetch_related to avoid N+1 queries.
    """

    return (
        Organization.objects
        .prefetch_related("locations")
        .order_by("name")
    )