from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.organizations.models import OrganizationMembership
from apps.organizations.serializers.mixins import UserResolutionSerializer

User = get_user_model()


""" ======================= Membership User Serializer ======================= """
class MembershipUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name"]
        read_only_fields = fields


""" ======================= Membership Serializer (Output) ======================= """
class MembershipSerializer(serializers.ModelSerializer):
    user = MembershipUserSerializer(read_only=True)

    class Meta:
        model = OrganizationMembership
        fields = ["id", "user", "role", "is_active", "joined_at"]
        read_only_fields = fields


""" ======================= Membership Invite Serializer (Input) ======================= """
class MembershipInviteSerializer(UserResolutionSerializer):
    """
    Adds a member to an organization.

    Either `user_id` (attach an existing user) or the new-user fields
    (`username`, `email`, `password`, `first_name`, `last_name`) must
    be provided — never both.
    """

    role = serializers.ChoiceField(
        choices=OrganizationMembership.Role.choices,
        default=OrganizationMembership.Role.STAFF,
    )

    def create(self, validated_data):
        organization = self.context["organization"]
        role = validated_data["role"]

        with transaction.atomic():
            user = self.resolve_user(validated_data)

            existing = OrganizationMembership.all_objects.filter(
                user=user, organization=organization,
            ).first()

            if existing is None or existing.is_deleted or not existing.is_active:
                from apps.billing.services import check_limit
                check_limit(organization, "users")   # plan allows N staff accounts

            if existing is None:
                return OrganizationMembership.objects.create(
                    user=user,
                    organization=organization,
                    role=role,
                    is_active=True,
                )

            if not existing.is_deleted and existing.is_active:
                raise serializers.ValidationError(
                    "This user is already a member of the organization."
                )

            # Previously removed/deactivated member: bring them back
            existing.is_deleted = False
            existing.is_active = True
            existing.role = role
            existing.save()
            return existing


""" ======================= Membership Update Serializer (Input) ======================= """
class MembershipUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationMembership
        fields = ["role", "is_active"]
