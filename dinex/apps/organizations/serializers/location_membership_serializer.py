from django.db import transaction
from rest_framework import serializers

from apps.organizations.models import (
    Location,
    LocationMembership,
    OrganizationMembership,
)
from apps.organizations.serializers.mixins import UserResolutionSerializer


""" ======================= Location Membership Serializer (Output) ======================= """
class LocationMembershipSerializer(serializers.ModelSerializer):
    location = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()

    class Meta:
        model = LocationMembership
        fields = ["id", "location", "user", "role", "is_active", "joined_at"]
        read_only_fields = fields

    def get_location(self, obj):
        return {"id": obj.location_id, "name": obj.location.name}

    def get_user(self, obj):
        user = obj.organization_membership.user
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }


""" ======================= Location Staff Assign Serializer (Input) ======================= """
class LocationMembershipAssignSerializer(UserResolutionSerializer):
    """
    Assigns a user to a location with a role.

    Either `user_id` (an existing user — already an organization member
    or not) or new-user fields must be provided. If the resolved user
    is not yet a member of the organization, an OrganizationMembership
    with role STAFF is created for them automatically.

    Re-assigning a previously removed user to the same location
    reactivates their existing LocationMembership instead of erroring.
    """

    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(),
    )

    role = serializers.ChoiceField(choices=LocationMembership.Role.choices)

    def validate_location_id(self, location):
        organization = self.context["organization"]
        if location.organization_id != organization.id:
            raise serializers.ValidationError(
                "Location does not belong to your organization."
            )
        return location

    def create(self, validated_data):
        organization = self.context["organization"]
        location = validated_data["location_id"]
        role = validated_data["role"]

        with transaction.atomic():
            user = self.resolve_user(validated_data)

            if not OrganizationMembership.objects.filter(user=user, organization=organization, is_active=True).exists():
                from apps.billing.services import check_limit
                check_limit(organization, "users")   # plan allows N staff accounts

            organization_membership, created = OrganizationMembership.all_objects.get_or_create(
                user=user,
                organization=organization,
                defaults={
                    "role": OrganizationMembership.Role.STAFF,
                    "is_active": True,
                },
            )
            if not created and (organization_membership.is_deleted or not organization_membership.is_active):
                # Reactivate a removed member (keeps their existing org role)
                organization_membership.is_deleted = False
                organization_membership.is_active = True
                organization_membership.save()

            location_membership, _ = LocationMembership.all_objects.update_or_create(
                organization_membership=organization_membership,
                location=location,
                defaults={
                    "role": role,
                    "is_active": True,
                    "is_deleted": False,
                },
            )

            return location_membership


""" ======================= Location Staff Update Serializer (Input) ======================= """
class LocationMembershipUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationMembership
        fields = ["role", "is_active"]
