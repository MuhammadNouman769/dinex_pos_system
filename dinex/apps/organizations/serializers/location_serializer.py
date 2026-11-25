from django.db import transaction
from rest_framework import serializers

from apps.organizations.models import Location


class OrganizationLocationListSerializer(
    serializers.ModelSerializer
):
    class Meta:
        model = Location

        fields = [
            "id",
            "name",
            "address",
            "phone",
            "is_active",
            "is_primary",
            "tax_rate",
            "service_charge_rate",
            "inventory_policy",
            "created_at",
            "updated_at",
        ]

        read_only_fields = fields


""" ======================= Location Serializer ======================= """
class LocationSerializer(serializers.ModelSerializer):
    """
    Serializer for Location CRUD.

    `organization` is always injected server-side by the view
    (from the caller's own membership) — never trusted from input.
    """

    class Meta:
        model = Location

        fields = [
            "id",
            "organization",
            "name",
            "address",
            "phone",
            "is_active",
            "is_primary",
            "tax_rate",
            "service_charge_rate",
            "inventory_policy",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "organization",
            "created_at",
            "updated_at",
        ]

    def _validate_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Must be between 0 and 100.")
        return value

    def validate_tax_rate(self, value):
        return self._validate_percent(value)

    def validate_service_charge_rate(self, value):
        return self._validate_percent(value)

    def create(self, validated_data):
        organization = validated_data["organization"]

        with transaction.atomic():
            if validated_data.get("is_primary"):
                Location.objects.filter(
                    organization=organization,
                    is_primary=True,
                ).update(is_primary=False)

            return super().create(validated_data)

    def update(self, instance, validated_data):
        with transaction.atomic():
            if validated_data.get("is_primary"):
                Location.objects.filter(
                    organization=instance.organization,
                    is_primary=True,
                ).exclude(pk=instance.pk).update(is_primary=False)

            return super().update(instance, validated_data)