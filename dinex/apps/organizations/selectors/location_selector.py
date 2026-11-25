from apps.organizations.models import Location


class LocationSelector:
    """
    Selector for Location queries.
    """

    @staticmethod
    def get_all_locations(organization_id, only_active=False):
        queryset = Location.objects.filter(organization_id=organization_id)

        if only_active:
            queryset = queryset.filter(is_active=True)

        return queryset

    @staticmethod
    def get_location(organization_id, pk):
        return Location.objects.get(
            organization_id=organization_id,
            pk=pk,
        )
