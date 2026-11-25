from rest_framework import serializers

from apps.organizations.models import Organization

from .location_serializer import (
    OrganizationLocationListSerializer,
)


class OrganizationListSerializer(
    serializers.ModelSerializer
):
    locations = OrganizationLocationListSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Organization

        fields = [
            "id",
            "name",
            "currency",
            "timezone",
            "is_active",
            "locations",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


""" ======================= Organization Detail Serializer ======================= """
class OrganizationDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving/updating a single organization.

    `is_active` is intentionally excluded — deactivating an organization
    is a platform-only action performed through a dedicated endpoint.
    """

    locations = OrganizationLocationListSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = Organization

        fields = [
            "id",
            "name",
            "currency",
            "timezone",
            "is_active",
            "locations",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "is_active",
            "locations",
            "created_at",
            "updated_at",
        ]