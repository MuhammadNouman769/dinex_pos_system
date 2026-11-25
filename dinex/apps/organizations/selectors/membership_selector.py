from apps.organizations.models import OrganizationMembership


class MembershipSelector:
    """
    Selector for OrganizationMembership queries.
    """

    @staticmethod
    def get_all_members(organization_id):
        return (
            OrganizationMembership.objects
            .filter(organization_id=organization_id)
            .select_related("user")
            .order_by("-joined_at")
        )

    @staticmethod
    def get_member(organization_id, pk):
        return (
            OrganizationMembership.objects
            .select_related("user")
            .get(organization_id=organization_id, pk=pk)
        )

    @staticmethod
    def count_active_owners(organization_id):
        return OrganizationMembership.objects.filter(
            organization_id=organization_id,
            role=OrganizationMembership.Role.OWNER,
            is_active=True,
        ).count()
