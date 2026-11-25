from apps.organizations.models import LocationMembership


class LocationMembershipSelector:
    """
    Selector for LocationMembership queries.
    """

    @staticmethod
    def get_all(organization_id, location_id=None):
        queryset = (
            LocationMembership.objects
            .filter(organization_membership__organization_id=organization_id)
            .select_related("organization_membership__user", "location")
        )

        if location_id:
            queryset = queryset.filter(location_id=location_id)

        return queryset

    @staticmethod
    def get(organization_id, pk):
        return (
            LocationMembership.objects
            .select_related("organization_membership__user", "location")
            .get(
                organization_membership__organization_id=organization_id,
                pk=pk,
            )
        )
