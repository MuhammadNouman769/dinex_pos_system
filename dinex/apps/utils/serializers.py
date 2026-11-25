class OrganizationScopedMixin:
    """
    Restricts related-object fields of a serializer to the caller's organization.

    Without this, a PrimaryKeyRelatedField accepts the id of ANY row in the
    database, so one restaurant could attach (or read) another restaurant's
    locations, customers, tables, categories, etc.

    Usage:
        class CustomerSerializer(OrganizationScopedMixin, serializers.ModelSerializer):
            org_scoped_fields = {"location": "organization_id"}

    The value is the ORM path from the related model to its organization id.
    Works for PrimaryKeyRelatedField and many=True fields.
    """

    org_scoped_fields = {}
    # Extra restriction for non-owners (MANAGER / POS_OPERATOR): the related
    # object must sit at one of their assigned locations.
    # field -> ORM path to the location id, e.g. {"table": "location_id"}
    location_scoped_fields = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request") if hasattr(self, "context") else None
        if request is None or not self.org_scoped_fields:
            return

        from apps.catalog.utils import get_user_organization_id

        org_id = get_user_organization_id(request)
        for name, path in self.org_scoped_fields.items():
            field = self.fields.get(name)
            if field is None:
                continue
            relation = getattr(field, "child_relation", field)
            queryset = getattr(relation, "queryset", None)
            if queryset is None:
                continue
            relation.queryset = (
                queryset.filter(**{path: org_id}) if org_id else queryset.none()
            )

        if not org_id:
            return
        from apps.utils.helpers import get_accessible_location_ids

        location_ids = get_accessible_location_ids(request, org_id)
        if location_ids is None:  # organization owner: no extra restriction
            return
        for name, path in self.location_scoped_fields.items():
            field = self.fields.get(name)
            relation = getattr(field, "child_relation", field) if field else None
            queryset = getattr(relation, "queryset", None)
            if queryset is not None:
                relation.queryset = queryset.filter(**{f"{path}__in": location_ids})
